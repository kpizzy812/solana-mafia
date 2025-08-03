"""
System monitoring service for admin dashboard.
"""

import asyncio
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.config import settings
from app.websocket.connection_manager import connection_manager
from app.models.event import Event
from app.models.player import Player
from app.models.business import Business

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics."""
    cpu_percent: float
    memory_percent: float
    memory_available_gb: float
    disk_usage_percent: float
    disk_free_gb: float
    uptime_seconds: int
    load_average: List[float]
    timestamp: datetime


@dataclass
class DatabaseMetrics:
    """Database performance metrics."""
    total_connections: int
    active_connections: int
    idle_connections: int
    total_queries: int
    slow_queries: int
    database_size_mb: float
    largest_table: str
    largest_table_size_mb: float
    avg_query_time_ms: float
    timestamp: datetime


@dataclass
class ApplicationMetrics:
    """Application-specific metrics."""
    total_players: int
    active_players_24h: int
    total_businesses: int
    businesses_created_24h: int
    total_events_processed: int
    events_processed_24h: int
    total_nfts: int
    websocket_connections: int
    indexer_status: str
    scheduler_status: str
    timestamp: datetime


class MonitoringService:
    """Service for collecting and managing system metrics."""
    
    def __init__(self):
        self.start_time = datetime.utcnow()
        self._metrics_cache: Dict[str, Any] = {}
        self._cache_ttl = 30  # seconds
    
    async def get_system_metrics(self) -> SystemMetrics:
        """Get current system performance metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_usage_percent = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024**3)
            
            # System uptime
            uptime_seconds = int((datetime.utcnow() - self.start_time).total_seconds())
            
            # Load average (Unix-like systems)
            try:
                load_average = list(psutil.getloadavg())
            except AttributeError:
                # Windows doesn't have load average
                load_average = [0.0, 0.0, 0.0]
            
            return SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory_percent,
                memory_available_gb=memory_available_gb,
                disk_usage_percent=disk_usage_percent,
                disk_free_gb=disk_free_gb,
                uptime_seconds=uptime_seconds,
                load_average=load_average,
                timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error("Error collecting system metrics", error=str(e))
            raise
    
    async def get_database_metrics(self) -> DatabaseMetrics:
        """Get current database performance metrics."""
        try:
            async with get_db_session() as db:
                # Connection stats (simplified - actual implementation depends on DB)
                result = await db.execute(text("SELECT 1"))
                total_connections = 1  # Placeholder
                active_connections = 1
                idle_connections = 0
                
                # Query stats (simplified)
                total_queries = 0
                slow_queries = 0
                avg_query_time_ms = 0.0
                
                # Database size
                try:
                    # PostgreSQL specific query
                    if 'postgresql' in str(db.bind.url):
                        size_result = await db.execute(text(
                            "SELECT pg_size_pretty(pg_database_size(current_database()))"
                        ))
                        database_size_mb = 0.0  # Would parse the result
                    else:
                        database_size_mb = 0.0
                except Exception:
                    database_size_mb = 0.0
                
                # Largest table (simplified)
                largest_table = "events"
                largest_table_size_mb = 0.0
                
                return DatabaseMetrics(
                    total_connections=total_connections,
                    active_connections=active_connections,
                    idle_connections=idle_connections,
                    total_queries=total_queries,
                    slow_queries=slow_queries,
                    database_size_mb=database_size_mb,
                    largest_table=largest_table,
                    largest_table_size_mb=largest_table_size_mb,
                    avg_query_time_ms=avg_query_time_ms,
                    timestamp=datetime.utcnow()
                )
        
        except Exception as e:
            logger.error("Error collecting database metrics", error=str(e))
            raise
    
    async def get_application_metrics(self) -> ApplicationMetrics:
        """Get current application-specific metrics."""
        try:
            async with get_db_session() as db:
                # Total players
                result = await db.execute(text("SELECT COUNT(*) FROM players"))
                total_players = result.scalar() or 0
                
                # Active players (24h) - simplified
                yesterday = datetime.utcnow() - timedelta(days=1)
                result = await db.execute(text(
                    "SELECT COUNT(DISTINCT player_wallet) FROM events WHERE created_at > :yesterday"
                ), {"yesterday": yesterday})
                active_players_24h = result.scalar() or 0
                
                # Total businesses
                result = await db.execute(text("SELECT COUNT(*) FROM businesses"))
                total_businesses = result.scalar() or 0
                
                # Businesses created (24h)
                result = await db.execute(text(
                    "SELECT COUNT(*) FROM businesses WHERE created_at > :yesterday"
                ), {"yesterday": yesterday})
                businesses_created_24h = result.scalar() or 0
                
                # Total events processed
                result = await db.execute(text("SELECT COUNT(*) FROM events"))
                total_events_processed = result.scalar() or 0
                
                # Events processed (24h)
                result = await db.execute(text(
                    "SELECT COUNT(*) FROM events WHERE created_at > :yesterday"
                ), {"yesterday": yesterday})
                events_processed_24h = result.scalar() or 0
                
                # Total NFTs
                result = await db.execute(text("SELECT COUNT(*) FROM business_nfts"))
                total_nfts = result.scalar() or 0
                
                # WebSocket connections
                websocket_connections = len(connection_manager.connections)
                
                # Service statuses (simplified)
                indexer_status = "running"  # Would check actual service status
                scheduler_status = "running"
                
                return ApplicationMetrics(
                    total_players=total_players,
                    active_players_24h=active_players_24h,
                    total_businesses=total_businesses,
                    businesses_created_24h=businesses_created_24h,
                    total_events_processed=total_events_processed,
                    events_processed_24h=events_processed_24h,
                    total_nfts=total_nfts,
                    websocket_connections=websocket_connections,
                    indexer_status=indexer_status,
                    scheduler_status=scheduler_status,
                    timestamp=datetime.utcnow()
                )
        
        except Exception as e:
            logger.error("Error collecting application metrics", error=str(e))
            raise
    
    async def get_websocket_metrics(self) -> Dict[str, Any]:
        """Get WebSocket connection metrics."""
        try:
            stats = connection_manager.get_connection_stats()
            
            # Add additional metrics
            connections_by_duration = {}
            current_time = datetime.utcnow()
            
            for connection in connection_manager.connections.values():
                duration = (current_time - connection.connected_at).total_seconds()
                if duration < 60:
                    connections_by_duration["< 1 min"] = connections_by_duration.get("< 1 min", 0) + 1
                elif duration < 300:
                    connections_by_duration["1-5 min"] = connections_by_duration.get("1-5 min", 0) + 1
                elif duration < 1800:
                    connections_by_duration["5-30 min"] = connections_by_duration.get("5-30 min", 0) + 1
                else:
                    connections_by_duration["> 30 min"] = connections_by_duration.get("> 30 min", 0) + 1
            
            return {
                **stats,
                "connections_by_duration": connections_by_duration,
                "timestamp": current_time.isoformat()
            }
        
        except Exception as e:
            logger.error("Error collecting WebSocket metrics", error=str(e))
            raise
    
    async def get_indexer_metrics(self) -> Dict[str, Any]:
        """Get event indexer metrics."""
        try:
            async with get_db_session() as db:
                # Events by type (last 24h)
                yesterday = datetime.utcnow() - timedelta(days=1)
                result = await db.execute(text("""
                    SELECT event_type, COUNT(*) as count
                    FROM events 
                    WHERE created_at > :yesterday
                    GROUP BY event_type
                    ORDER BY count DESC
                """), {"yesterday": yesterday})
                
                events_by_type = {row[0]: row[1] for row in result.fetchall()}
                
                # Events processing rate (events per hour for last 24h)
                result = await db.execute(text("""
                    SELECT 
                        DATE_TRUNC('hour', created_at) as hour,
                        COUNT(*) as count
                    FROM events 
                    WHERE created_at > :yesterday
                    GROUP BY hour
                    ORDER BY hour DESC
                    LIMIT 24
                """), {"yesterday": yesterday})
                
                events_per_hour = [{"hour": row[0].isoformat(), "count": row[1]} for row in result.fetchall()]
                
                # Latest processed event
                result = await db.execute(text("""
                    SELECT signature, event_type, created_at
                    FROM events
                    ORDER BY created_at DESC
                    LIMIT 1
                """))
                
                latest_event = result.fetchone()
                latest_event_info = None
                if latest_event:
                    latest_event_info = {
                        "signature": latest_event[0],
                        "event_type": latest_event[1],
                        "timestamp": latest_event[2].isoformat()
                    }
                
                return {
                    "events_by_type_24h": events_by_type,
                    "events_per_hour": events_per_hour,
                    "latest_event": latest_event_info,
                    "total_events": sum(events_by_type.values()),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        except Exception as e:
            logger.error("Error collecting indexer metrics", error=str(e))
            raise
    
    async def get_scheduler_metrics(self) -> Dict[str, Any]:
        """Get earnings scheduler metrics."""
        try:
            async with get_db_session() as db:
                # Players with pending earnings
                result = await db.execute(text("""
                    SELECT COUNT(*) 
                    FROM players 
                    WHERE earnings_balance > 0
                """))
                
                pending_earnings_count = result.scalar() or 0
                
                # Total pending earnings amount
                result = await db.execute(text("""
                    SELECT COALESCE(SUM(earnings_balance), 0) 
                    FROM players
                """))
                
                total_pending_earnings = result.scalar() or 0
                
                # Earnings updates (last 24h)
                yesterday = datetime.utcnow() - timedelta(days=1)
                result = await db.execute(text("""
                    SELECT COUNT(*)
                    FROM events
                    WHERE event_type = 'EarningsUpdated' 
                    AND created_at > :yesterday
                """), {"yesterday": yesterday})
                
                earnings_updates_24h = result.scalar() or 0
                
                # Earnings claims (last 24h)
                result = await db.execute(text("""
                    SELECT COUNT(*)
                    FROM events
                    WHERE event_type = 'EarningsClaimed' 
                    AND created_at > :yesterday
                """), {"yesterday": yesterday})
                
                earnings_claims_24h = result.scalar() or 0
                
                return {
                    "players_with_pending_earnings": pending_earnings_count,
                    "total_pending_earnings": total_pending_earnings,
                    "earnings_updates_24h": earnings_updates_24h,
                    "earnings_claims_24h": earnings_claims_24h,
                    "scheduler_status": "running",  # Would check actual status
                    "last_update": datetime.utcnow().isoformat(),
                    "timestamp": datetime.utcnow().isoformat()
                }
        
        except Exception as e:
            logger.error("Error collecting scheduler metrics", error=str(e))
            raise
    
    async def get_comprehensive_status(self) -> Dict[str, Any]:
        """Get comprehensive system status for dashboard."""
        try:
            # Run all metric collection in parallel
            system_task = asyncio.create_task(self.get_system_metrics())
            db_task = asyncio.create_task(self.get_database_metrics())
            app_task = asyncio.create_task(self.get_application_metrics())
            ws_task = asyncio.create_task(self.get_websocket_metrics())
            indexer_task = asyncio.create_task(self.get_indexer_metrics())
            scheduler_task = asyncio.create_task(self.get_scheduler_metrics())
            
            # Wait for all tasks to complete
            system_metrics, db_metrics, app_metrics, ws_metrics, indexer_metrics, scheduler_metrics = await asyncio.gather(
                system_task, db_task, app_task, ws_task, indexer_task, scheduler_task
            )
            
            # Overall health status
            health_status = "healthy"
            health_issues = []
            
            # Check for health issues
            if system_metrics.cpu_percent > 80:
                health_issues.append("High CPU usage")
            if system_metrics.memory_percent > 85:
                health_issues.append("High memory usage")
            if system_metrics.disk_usage_percent > 90:
                health_issues.append("Low disk space")
            
            if health_issues:
                health_status = "warning" if len(health_issues) < 3 else "critical"
            
            return {
                "overall_status": health_status,
                "health_issues": health_issues,
                "system": {
                    "cpu_percent": system_metrics.cpu_percent,
                    "memory_percent": system_metrics.memory_percent,
                    "memory_available_gb": round(system_metrics.memory_available_gb, 2),
                    "disk_usage_percent": round(system_metrics.disk_usage_percent, 2),
                    "disk_free_gb": round(system_metrics.disk_free_gb, 2),
                    "uptime_seconds": system_metrics.uptime_seconds,
                    "load_average": system_metrics.load_average
                },
                "database": {
                    "connections": {
                        "total": db_metrics.total_connections,
                        "active": db_metrics.active_connections,
                        "idle": db_metrics.idle_connections
                    },
                    "size_mb": db_metrics.database_size_mb,
                    "largest_table": {
                        "name": db_metrics.largest_table,
                        "size_mb": db_metrics.largest_table_size_mb
                    }
                },
                "application": {
                    "players": {
                        "total": app_metrics.total_players,
                        "active_24h": app_metrics.active_players_24h
                    },
                    "businesses": {
                        "total": app_metrics.total_businesses,
                        "created_24h": app_metrics.businesses_created_24h
                    },
                    "events": {
                        "total": app_metrics.total_events_processed,
                        "processed_24h": app_metrics.events_processed_24h
                    },
                    "nfts": {
                        "total": app_metrics.total_nfts
                    },
                    "services": {
                        "indexer": app_metrics.indexer_status,
                        "scheduler": app_metrics.scheduler_status
                    }
                },
                "websocket": ws_metrics,
                "indexer": indexer_metrics,
                "scheduler": scheduler_metrics,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error("Error collecting comprehensive status", error=str(e))
            raise


# Global monitoring service instance
monitoring_service = MonitoringService()


def get_monitoring_service() -> MonitoringService:
    """Get the global monitoring service instance."""
    return monitoring_service
"""
Admin dashboard API routes for system monitoring and management.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.api.schemas.common import SuccessResponse, create_success_response
from .admin_auth import require_admin_auth, optional_admin_auth
from .monitoring import get_monitoring_service, MonitoringService
from app.websocket.connection_manager import connection_manager

import structlog

logger = structlog.get_logger(__name__)

# Create admin router
admin_router = APIRouter()


@admin_router.get(
    "/status",
    response_model=SuccessResponse,
    summary="System Status Overview",
    description="Get comprehensive system status and health metrics"
)
async def get_system_status(
    auth: dict = Depends(require_admin_auth),
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Get comprehensive system status overview."""
    try:
        status_data = await monitoring.get_comprehensive_status()
        
        logger.info(
            "Admin accessed system status",
            admin_type=auth["auth_type"],
            admin_wallet=auth.get("wallet")
        )
        
        return create_success_response(
            data=status_data,
            message="System status retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error getting system status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system status"
        )


@admin_router.get(
    "/metrics/system",
    response_model=SuccessResponse,
    summary="System Performance Metrics",
    description="Get detailed system performance metrics (CPU, memory, disk)"
)
async def get_system_metrics(
    auth: dict = Depends(require_admin_auth),
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Get system performance metrics."""
    try:
        metrics = await monitoring.get_system_metrics()
        
        return create_success_response(
            data={
                "cpu_percent": metrics.cpu_percent,
                "memory": {
                    "percent": metrics.memory_percent,
                    "available_gb": round(metrics.memory_available_gb, 2)
                },
                "disk": {
                    "usage_percent": round(metrics.disk_usage_percent, 2),
                    "free_gb": round(metrics.disk_free_gb, 2)
                },
                "uptime_seconds": metrics.uptime_seconds,
                "load_average": metrics.load_average,
                "timestamp": metrics.timestamp.isoformat()
            },
            message="System metrics retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error getting system metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system metrics"
        )


@admin_router.get(
    "/metrics/database",
    response_model=SuccessResponse,
    summary="Database Performance Metrics",
    description="Get database performance and connection metrics"
)
async def get_database_metrics(
    auth: dict = Depends(require_admin_auth),
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Get database performance metrics."""
    try:
        metrics = await monitoring.get_database_metrics()
        
        return create_success_response(
            data={
                "connections": {
                    "total": metrics.total_connections,
                    "active": metrics.active_connections,
                    "idle": metrics.idle_connections
                },
                "performance": {
                    "total_queries": metrics.total_queries,
                    "slow_queries": metrics.slow_queries,
                    "avg_query_time_ms": metrics.avg_query_time_ms
                },
                "storage": {
                    "database_size_mb": metrics.database_size_mb,
                    "largest_table": {
                        "name": metrics.largest_table,
                        "size_mb": metrics.largest_table_size_mb
                    }
                },
                "timestamp": metrics.timestamp.isoformat()
            },
            message="Database metrics retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error getting database metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve database metrics"
        )


@admin_router.get(
    "/metrics/application",
    response_model=SuccessResponse,
    summary="Application Metrics",
    description="Get application-specific metrics (players, businesses, events)"
)
async def get_application_metrics(
    auth: dict = Depends(require_admin_auth),
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Get application-specific metrics."""
    try:
        metrics = await monitoring.get_application_metrics()
        
        return create_success_response(
            data={
                "players": {
                    "total": metrics.total_players,
                    "active_24h": metrics.active_players_24h
                },
                "businesses": {
                    "total": metrics.total_businesses,
                    "created_24h": metrics.businesses_created_24h
                },
                "events": {
                    "total_processed": metrics.total_events_processed,
                    "processed_24h": metrics.events_processed_24h
                },
                "nfts": {
                    "total": metrics.total_nfts
                },
                "services": {
                    "indexer_status": metrics.indexer_status,
                    "scheduler_status": metrics.scheduler_status,
                    "websocket_connections": metrics.websocket_connections
                },
                "timestamp": metrics.timestamp.isoformat()
            },
            message="Application metrics retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error getting application metrics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve application metrics"
        )


@admin_router.get(
    "/websocket/stats",
    response_model=SuccessResponse,
    summary="WebSocket Connection Statistics",
    description="Get detailed WebSocket connection statistics and metrics"
)
async def get_websocket_stats(
    auth: dict = Depends(require_admin_auth),
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Get WebSocket connection statistics."""
    try:
        stats = await monitoring.get_websocket_metrics()
        
        return create_success_response(
            data=stats,
            message="WebSocket statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error getting WebSocket stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve WebSocket statistics"
        )


@admin_router.get(
    "/websocket/connections",
    response_model=SuccessResponse,
    summary="Active WebSocket Connections",
    description="Get list of currently active WebSocket connections"
)
async def get_active_websocket_connections(
    auth: dict = Depends(require_admin_auth),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of connections to return")
):
    """Get list of active WebSocket connections."""
    try:
        connections_data = []
        
        for client_id, connection in list(connection_manager.connections.items())[:limit]:
            connection_info = {
                "client_id": client_id,
                "wallet": connection.wallet,
                "connected_at": connection.connected_at.isoformat(),
                "last_ping": connection.last_ping.isoformat(),
                "subscriptions": [sub.value for sub in connection.subscriptions],
                "duration_seconds": int((datetime.utcnow() - connection.connected_at).total_seconds())
            }
            connections_data.append(connection_info)
        
        return create_success_response(
            data={
                "connections": connections_data,
                "total_connections": len(connection_manager.connections),
                "showing": len(connections_data),
                "timestamp": datetime.utcnow().isoformat()
            },
            message=f"Retrieved {len(connections_data)} active connections"
        )
        
    except Exception as e:
        logger.error("Error getting active WebSocket connections", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve WebSocket connections"
        )


@admin_router.get(
    "/indexer/stats",
    response_model=SuccessResponse,
    summary="Event Indexer Statistics",
    description="Get event indexer performance and processing statistics"
)
async def get_indexer_stats(
    auth: dict = Depends(require_admin_auth),
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Get event indexer statistics."""
    try:
        stats = await monitoring.get_indexer_metrics()
        
        return create_success_response(
            data=stats,
            message="Indexer statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error getting indexer stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve indexer statistics"
        )


@admin_router.get(
    "/scheduler/stats",
    response_model=SuccessResponse,
    summary="Earnings Scheduler Statistics",
    description="Get earnings scheduler performance and processing statistics"
)
async def get_scheduler_stats(
    auth: dict = Depends(require_admin_auth),
    monitoring: MonitoringService = Depends(get_monitoring_service)
):
    """Get earnings scheduler statistics."""
    try:
        stats = await monitoring.get_scheduler_metrics()
        
        return create_success_response(
            data=stats,
            message="Scheduler statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error getting scheduler stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve scheduler statistics"
        )


@admin_router.get(
    "/players/top",
    response_model=SuccessResponse,
    summary="Top Players Statistics",
    description="Get top players by various metrics"
)
async def get_top_players(
    auth: dict = Depends(require_admin_auth),
    metric: str = Query("earnings", description="Metric to sort by: earnings, businesses, activity"),
    limit: int = Query(10, ge=1, le=100, description="Number of top players to return"),
    db: AsyncSession = Depends(get_db_session)
):
    """Get top players by specified metric."""
    try:
        if metric == "earnings":
            query = text("""
                SELECT wallet, total_earnings, earnings_balance, business_count
                FROM players
                ORDER BY total_earnings DESC
                LIMIT :limit
            """)
        elif metric == "businesses":
            query = text("""
                SELECT wallet, total_earnings, earnings_balance, business_count
                FROM players
                ORDER BY business_count DESC
                LIMIT :limit
            """)
        elif metric == "activity":
            # Count recent events for each player
            query = text("""
                SELECT p.wallet, p.total_earnings, p.earnings_balance, p.business_count,
                       COUNT(e.id) as recent_events
                FROM players p
                LEFT JOIN events e ON e.player_wallet = p.wallet 
                    AND e.created_at > NOW() - INTERVAL '7 days'
                GROUP BY p.wallet, p.total_earnings, p.earnings_balance, p.business_count
                ORDER BY recent_events DESC
                LIMIT :limit
            """)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid metric. Use: earnings, businesses, or activity"
            )
        
        result = await db.execute(query, {"limit": limit})
        rows = result.fetchall()
        
        players_data = []
        for row in rows:
            player_info = {
                "wallet": row[0],
                "total_earnings": row[1],
                "earnings_balance": row[2],
                "business_count": row[3]
            }
            if metric == "activity":
                player_info["recent_events"] = row[4]
            
            players_data.append(player_info)
        
        return create_success_response(
            data={
                "metric": metric,
                "players": players_data,
                "count": len(players_data),
                "timestamp": datetime.utcnow().isoformat()
            },
            message=f"Retrieved top {len(players_data)} players by {metric}"
        )
        
    except Exception as e:
        logger.error("Error getting top players", metric=metric, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve top players"
        )


@admin_router.get(
    "/events/recent",
    response_model=SuccessResponse,
    summary="Recent Events",
    description="Get recent blockchain events processed by the system"
)
async def get_recent_events(
    auth: dict = Depends(require_admin_auth),
    limit: int = Query(50, ge=1, le=500, description="Number of recent events to return"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    db: AsyncSession = Depends(get_db_session)
):
    """Get recent blockchain events."""
    try:
        if event_type:
            query = text("""
                SELECT signature, event_type, player_wallet, data, created_at
                FROM events
                WHERE event_type = :event_type
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            result = await db.execute(query, {"event_type": event_type, "limit": limit})
        else:
            query = text("""
                SELECT signature, event_type, player_wallet, data, created_at
                FROM events
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            result = await db.execute(query, {"limit": limit})
        
        rows = result.fetchall()
        
        events_data = []
        for row in rows:
            event_info = {
                "signature": row[0],
                "event_type": row[1],
                "player_wallet": row[2],
                "data": row[3],
                "timestamp": row[4].isoformat()
            }
            events_data.append(event_info)
        
        return create_success_response(
            data={
                "events": events_data,
                "count": len(events_data),
                "filter": {"event_type": event_type} if event_type else None,
                "timestamp": datetime.utcnow().isoformat()
            },
            message=f"Retrieved {len(events_data)} recent events"
        )
        
    except Exception as e:
        logger.error("Error getting recent events", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve recent events"
        )


@admin_router.post(
    "/websocket/broadcast",
    response_model=SuccessResponse,
    summary="Broadcast WebSocket Message",
    description="Broadcast a message to WebSocket connections"
)
async def broadcast_websocket_message(
    message_data: Dict[str, Any],
    auth: dict = Depends(require_admin_auth),
    target_wallet: Optional[str] = Query(None, description="Target specific wallet (optional)")
):
    """Broadcast a message to WebSocket connections."""
    try:
        from app.websocket.schemas import WebSocketMessage, MessageType
        
        # Create admin message
        admin_message = WebSocketMessage(
            type=MessageType.CONNECTION_STATUS,
            data={
                "admin_broadcast": True,
                "message": message_data.get("message", "Admin broadcast"),
                "data": message_data.get("data", {}),
                "sender": auth.get("wallet", "admin")
            }
        )
        
        if target_wallet:
            # Send to specific wallet
            sent_count = await connection_manager.send_to_wallet(target_wallet, admin_message)
            message = f"Message sent to {sent_count} connections for wallet {target_wallet}"
        else:
            # Broadcast to all connections
            sent_count = await connection_manager.broadcast_to_all(admin_message)
            message = f"Message broadcast to {sent_count} connections"
        
        logger.info(
            "Admin broadcast WebSocket message",
            admin_type=auth["auth_type"],
            admin_wallet=auth.get("wallet"),
            target_wallet=target_wallet,
            sent_count=sent_count
        )
        
        return create_success_response(
            data={
                "sent_count": sent_count,
                "target_wallet": target_wallet,
                "message_data": message_data,
                "timestamp": datetime.utcnow().isoformat()
            },
            message=message
        )
        
    except Exception as e:
        logger.error("Error broadcasting WebSocket message", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to broadcast WebSocket message"
        )


@admin_router.get(
    "/config",
    response_model=SuccessResponse,
    summary="System Configuration",
    description="Get current system configuration (non-sensitive values only)"
)
async def get_system_config(
    auth: dict = Depends(require_admin_auth)
):
    """Get system configuration."""
    try:
        from app.core.config import settings
        
        # Return non-sensitive configuration
        config_data = {
            "environment": settings.environment,
            "debug": settings.debug,
            "app_version": settings.app_version,
            "database_url": "***" if settings.database_url else None,
            "solana_rpc_url": settings.solana_rpc_url,
            "program_id": settings.solana_program_id,
            "api_v1_prefix": settings.api_v1_prefix,
            "host": settings.host,
            "port": settings.port,
            "log_level": settings.log_level,
            "cors_origins": settings.cors_origins,
            "admin_wallets_count": len(getattr(settings, 'admin_wallets', '').split(',')) if getattr(settings, 'admin_wallets', '') else 0,
            "admin_api_key_set": bool(getattr(settings, 'admin_api_key', None))
        }
        
        return create_success_response(
            data=config_data,
            message="System configuration retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error getting system config", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve system configuration"
        )


@admin_router.get(
    "/health",
    summary="Admin Health Check",
    description="Check admin API health and authentication"
)
async def admin_health_check(
    auth: dict = Depends(optional_admin_auth)
):
    """Admin health check endpoint."""
    health_data = {
        "status": "healthy",
        "admin_authenticated": auth.get("authenticated", False),
        "auth_type": auth.get("auth_type"),
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if auth.get("authenticated"):
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": health_data,
                "message": "Admin API is healthy and authenticated"
            }
        )
    else:
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": health_data,
                "message": "Admin API is healthy (authentication required for admin features)"
            }
        )


# ===== DYNAMIC PRICING MANAGEMENT =====

@admin_router.get(
    "/pricing/status",
    response_model=SuccessResponse,
    summary="Dynamic Pricing Status",
    description="Get current entry fee and pricing status"
)
async def get_pricing_status(
    auth: dict = Depends(require_admin_auth),
    db: AsyncSession = Depends(get_db_session)
):
    """Get current pricing status and SOL rate."""
    try:
        from app.services.coingecko_service import coingecko_service
        from app.services.dynamic_pricing_service import dynamic_pricing_service
        
        # Get SOL price
        sol_price = await coingecko_service.get_sol_price_usd()
        
        # Get total players
        total_players = await dynamic_pricing_service.get_total_players()
        
        # Calculate what dynamic fee should be
        dynamic_fee_usd = dynamic_pricing_service.calculate_entry_fee_usd(total_players)
        dynamic_fee_lamports = None
        if sol_price:
            dynamic_fee_lamports = dynamic_pricing_service.calculate_entry_fee_lamports(total_players, sol_price)
        
        return create_success_response(
            data={
                "sol_price_usd": sol_price,
                "total_players": total_players,
                "dynamic_fee_usd": dynamic_fee_usd,
                "dynamic_fee_lamports": dynamic_fee_lamports,
                "dynamic_fee_sol": dynamic_fee_lamports / 1_000_000_000 if dynamic_fee_lamports else None,
                "current_fee_lamports": dynamic_pricing_service.last_entry_fee,
                "pricing_enabled": settings.dynamic_pricing_enabled,
                "admin_wallet_configured": bool(dynamic_pricing_service.admin_keypair),
                "update_interval": settings.price_update_interval
            },
            message="Pricing status retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error getting pricing status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pricing status"
        )


@admin_router.post(
    "/pricing/update",
    response_model=SuccessResponse,
    summary="Manual Entry Fee Update",
    description="Manually update entry fee (for promotions and campaigns)"
)
async def manual_update_entry_fee(
    fee_data: Dict[str, Any],
    auth: dict = Depends(require_admin_auth)
):
    """Manually update entry fee."""
    try:
        from app.services.dynamic_pricing_service import dynamic_pricing_service
        
        # Validate input
        if "fee_lamports" not in fee_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fee_lamports is required"
            )
        
        fee_lamports = int(fee_data["fee_lamports"])
        if fee_lamports <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="fee_lamports must be positive"
            )
        
        # Send transaction
        success = await dynamic_pricing_service._send_update_transaction(fee_lamports)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send update transaction"
            )
        
        # Update cache
        dynamic_pricing_service.last_entry_fee = fee_lamports
        
        logger.info(
            "Admin manually updated entry fee",
            admin_wallet=auth.get("wallet"),
            new_fee_lamports=fee_lamports,
            new_fee_sol=fee_lamports / 1_000_000_000
        )
        
        return create_success_response(
            data={
                "new_fee_lamports": fee_lamports,
                "new_fee_sol": fee_lamports / 1_000_000_000,
                "updated_by": auth.get("wallet", "admin"),
                "timestamp": datetime.utcnow().isoformat()
            },
            message=f"Entry fee updated to {fee_lamports} lamports"
        )
        
    except Exception as e:
        logger.error("Error updating entry fee", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update entry fee"
        )


@admin_router.post(
    "/pricing/sync",
    response_model=SuccessResponse,
    summary="Sync Entry Fee to Dynamic Price",
    description="Force sync entry fee to current dynamic price calculation"
)
async def sync_dynamic_price(
    auth: dict = Depends(require_admin_auth)
):
    """Force sync entry fee to dynamic calculation."""
    try:
        from app.services.dynamic_pricing_service import dynamic_pricing_service
        
        # Force update
        success = await dynamic_pricing_service.update_entry_fee_if_needed()
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to sync dynamic price"
            )
        
        logger.info(
            "Admin synced entry fee to dynamic price",
            admin_wallet=auth.get("wallet")
        )
        
        return create_success_response(
            data={
                "new_fee_lamports": dynamic_pricing_service.last_entry_fee,
                "new_fee_sol": dynamic_pricing_service.last_entry_fee / 1_000_000_000 if dynamic_pricing_service.last_entry_fee else None,
                "synced_by": auth.get("wallet", "admin"),
                "timestamp": datetime.utcnow().isoformat()
            },
            message="Entry fee synced to dynamic price"
        )
        
    except Exception as e:
        logger.error("Error syncing dynamic price", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to sync dynamic price"
        )
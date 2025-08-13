"""
New Blockchain-First Earnings Scheduler.

This service provides:
- Daily earnings processing at configurable UTC hour
- Fault-tolerant architecture using ResilientEarningsProcessor
- Blockchain-as-source-of-truth synchronization
- Permissionless earnings updates (no admin scam risk)
- Comprehensive monitoring and health checks
"""

import asyncio
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

from app.core.config import settings
from app.services.resilient_earnings_processor import (
    get_resilient_earnings_processor,
    ProcessorStats
)


logger = structlog.get_logger(__name__)


class SchedulerStatus(Enum):
    """Status of the earnings scheduler."""
    STOPPED = "stopped"
    WAITING = "waiting"
    PROCESSING = "processing"
    ERROR = "error"


@dataclass
class SchedulerStats:
    """Statistics for scheduler operations."""
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    last_processing_stats: Optional[ProcessorStats] = None
    uptime_start: Optional[datetime] = None


class BlockchainEarningsScheduler:
    """
    Simplified earnings scheduler that runs daily and uses blockchain as source of truth.
    
    Key differences from old scheduler:
    - Runs once daily at configured UTC hour (not continuously)  
    - Uses ResilientEarningsProcessor for all logic
    - No database state management (blockchain is source of truth)
    - Permissionless transactions (no admin privileges)
    - Simple monitoring and health checks
    """
    
    def __init__(self):
        """Initialize the blockchain earnings scheduler."""
        self.logger = logger.bind(service="blockchain_earnings_scheduler")
        
        # Configuration from environment
        self.enabled = os.getenv('SCHEDULER_ENABLED', 'true').lower() == 'true'
        self.utc_hour = int(os.getenv('EARNINGS_SCHEDULE_UTC_HOUR', '0'))  # 00:00 UTC by default
        self.health_check_interval = int(os.getenv('SCHEDULER_INTERVAL', '60'))  # Still used for health checks
        
        # State
        self.status = SchedulerStatus.STOPPED
        self.stats = SchedulerStats(uptime_start=datetime.utcnow())
        self._should_stop = False
        self._scheduler_task: Optional[asyncio.Task] = None
        
        self.logger.info(
            "Blockchain earnings scheduler initialized",
            enabled=self.enabled,
            utc_hour=self.utc_hour,
            health_check_interval=self.health_check_interval
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()
    
    def _calculate_next_run_time(self) -> datetime:
        """Calculate the next time earnings should be processed."""
        now = datetime.now(timezone.utc)
        
        # Calculate next occurrence of target hour
        next_run = now.replace(
            hour=self.utc_hour,
            minute=0,
            second=0,
            microsecond=0
        )
        
        # If the time has already passed today, schedule for tomorrow
        if next_run <= now:
            next_run += timedelta(days=1)
        
        return next_run
    
    def _should_run_earnings(self) -> bool:
        """Check if it's time to run earnings processing."""
        now = datetime.now(timezone.utc)
        
        # Check if we're within the target hour
        if now.hour == self.utc_hour and now.minute < 30:  # 30-minute window
            # Check if we haven't run today yet
            if self.stats.last_run:
                last_run_date = self.stats.last_run.date()
                today = now.date()
                return last_run_date < today
            else:
                return True  # First run
                
        return False
    
    async def start(self):
        """Start the earnings scheduler."""
        if not self.enabled:
            self.logger.info("Earnings scheduler is disabled")
            return
        
        if self.status != SchedulerStatus.STOPPED:
            self.logger.warning(
                "Scheduler already running",
                current_status=self.status.value
            )
            return
        
        try:
            self.logger.info("Starting blockchain earnings scheduler")
            
            self._should_stop = False
            self.status = SchedulerStatus.WAITING
            
            # Calculate next run time
            self.stats.next_run = self._calculate_next_run_time()
            
            # Start scheduler task
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            
            self.logger.info(
                "Blockchain earnings scheduler started",
                next_run=self.stats.next_run.isoformat()
            )
            
        except Exception as e:
            self.status = SchedulerStatus.ERROR
            self.logger.error("Failed to start earnings scheduler", error=str(e))
            raise
    
    async def stop(self):
        """Stop the earnings scheduler."""
        if self.status == SchedulerStatus.STOPPED:
            return
        
        self.logger.info("Stopping blockchain earnings scheduler")
        
        self._should_stop = True
        
        # Cancel scheduler task
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        self.status = SchedulerStatus.STOPPED
        self.logger.info("Blockchain earnings scheduler stopped")
    
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        self.logger.info("Scheduler loop started")
        
        while not self._should_stop:
            try:
                # Check if it's time to run earnings
                if self._should_run_earnings():
                    await self._run_daily_earnings()
                
                # Update next run time
                self.stats.next_run = self._calculate_next_run_time()
                
                # Health check interval wait
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                self.logger.info("Scheduler loop cancelled")
                break
                
            except Exception as e:
                self.logger.error("Error in scheduler loop", error=str(e))
                self.status = SchedulerStatus.ERROR
                
                # Brief pause before retrying
                await asyncio.sleep(60)
                self.status = SchedulerStatus.WAITING
        
        self.logger.info("Scheduler loop stopped")
    
    async def _run_daily_earnings(self):
        """Run the daily earnings processing."""
        self.logger.info("Starting daily earnings processing")
        
        self.status = SchedulerStatus.PROCESSING
        self.stats.total_runs += 1
        
        try:
            # Get resilient earnings processor
            processor = await get_resilient_earnings_processor()
            
            # Run the daily earnings process
            processing_stats = await processor.run_daily_earnings_process()
            
            # Update scheduler stats
            self.stats.last_run = datetime.utcnow()
            self.stats.last_processing_stats = processing_stats
            self.stats.successful_runs += 1
            self.status = SchedulerStatus.WAITING
            
            self.logger.info(
                "Daily earnings processing completed successfully",
                total_players=processing_stats.total_players_found,
                players_updated=processing_stats.successful_updates,
                processing_time=f"{processing_stats.total_processing_time:.2f}s",
                success_rate=f"{processing_stats.success_rate * 100:.1f}%"
            )
            
        except Exception as e:
            self.stats.failed_runs += 1
            self.status = SchedulerStatus.ERROR
            
            self.logger.error(
                "Daily earnings processing failed",
                error=str(e),
                total_runs=self.stats.total_runs,
                failed_runs=self.stats.failed_runs
            )
            
            # Reset to waiting after error
            await asyncio.sleep(300)  # 5 minute pause after error
            self.status = SchedulerStatus.WAITING
    
    async def trigger_manual_run(self) -> ProcessorStats:
        """
        Manually trigger earnings processing (for testing/admin).
        
        Returns:
            ProcessorStats from the processing run
        """
        if self.status == SchedulerStatus.PROCESSING:
            raise Exception("Earnings processing already in progress")
        
        self.logger.info("Manual earnings processing triggered")
        
        old_status = self.status
        self.status = SchedulerStatus.PROCESSING
        
        try:
            processor = await get_resilient_earnings_processor()
            processing_stats = await processor.run_daily_earnings_process()
            
            # Update stats
            self.stats.last_run = datetime.utcnow()
            self.stats.last_processing_stats = processing_stats
            self.stats.total_runs += 1
            self.stats.successful_runs += 1
            
            self.logger.info(
                "Manual earnings processing completed",
                processing_time=f"{processing_stats.total_processing_time:.2f}s"
            )
            
            return processing_stats
            
        except Exception as e:
            self.stats.failed_runs += 1
            self.logger.error("Manual earnings processing failed", error=str(e))
            raise
        finally:
            self.status = old_status
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health check."""
        try:
            # Get processor health
            processor = await get_resilient_earnings_processor()
            processor_status = processor.get_status()
            
            # Calculate uptime
            uptime_seconds = (datetime.utcnow() - self.stats.uptime_start).total_seconds()
            
            return {
                "status": self.status.value,
                "enabled": self.enabled,
                "uptime_seconds": uptime_seconds,
                "scheduler_stats": asdict(self.stats),
                "processor_status": processor_status,
                "configuration": {
                    "utc_hour": self.utc_hour,
                    "health_check_interval": self.health_check_interval
                },
                "next_run_in_seconds": (
                    (self.stats.next_run - datetime.now(timezone.utc)).total_seconds()
                    if self.stats.next_run else None
                )
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "scheduler_stats": asdict(self.stats)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status."""
        return {
            "status": self.status.value,
            "enabled": self.enabled,
            "stats": asdict(self.stats),
            "next_run": self.stats.next_run.isoformat() if self.stats.next_run else None
        }


# Global scheduler instance
_blockchain_earnings_scheduler: Optional[BlockchainEarningsScheduler] = None


async def get_blockchain_earnings_scheduler() -> BlockchainEarningsScheduler:
    """Get or create global BlockchainEarningsScheduler instance."""
    global _blockchain_earnings_scheduler
    if _blockchain_earnings_scheduler is None:
        _blockchain_earnings_scheduler = BlockchainEarningsScheduler()
    return _blockchain_earnings_scheduler


async def start_blockchain_earnings_scheduler():
    """Start the global blockchain earnings scheduler."""
    scheduler = await get_blockchain_earnings_scheduler()
    await scheduler.start()


async def stop_blockchain_earnings_scheduler():
    """Stop the global blockchain earnings scheduler."""
    global _blockchain_earnings_scheduler
    if _blockchain_earnings_scheduler:
        await _blockchain_earnings_scheduler.stop()


async def trigger_manual_earnings() -> ProcessorStats:
    """Trigger manual earnings processing."""
    scheduler = await get_blockchain_earnings_scheduler()
    return await scheduler.trigger_manual_run()


# Legacy compatibility (for existing code that imports the old scheduler)
async def get_earnings_scheduler():
    """Legacy compatibility function."""
    return await get_blockchain_earnings_scheduler()


async def shutdown_earnings_scheduler():
    """Legacy compatibility function.""" 
    await stop_blockchain_earnings_scheduler()
"""
Prestige scheduler service for automated prestige point recalculation.
Monitors player activities and ensures prestige points are accurate.
"""

import asyncio
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func
import structlog

from app.core.database import get_async_session
from app.core.config import settings
from app.core.exceptions import SchedulerError
from app.services.prestige_service import get_prestige_service
from app.models.player import Player
from app.models.business import Business
from app.utils.validation import validate_wallet_address


logger = structlog.get_logger(__name__)


class PrestigeSchedulerStatus(Enum):
    """Status of the prestige scheduler."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class PrestigeSchedulerStats:
    """Statistics for prestige scheduler operations."""
    recalculations_processed: int = 0
    successful_recalculations: int = 0
    failed_recalculations: int = 0
    players_processed: int = 0
    total_points_recalculated: int = 0
    level_ups_triggered: int = 0
    start_time: Optional[datetime] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


@dataclass
class PrestigeRecalculationTask:
    """Task for recalculating a player's prestige."""
    wallet: str
    priority: int = 0
    retry_count: int = 0
    last_error: Optional[str] = None


class PrestigeScheduler:
    """
    Automated prestige scheduler for Solana Mafia players.
    
    Features:
    - Periodic recalculation of prestige points for all players
    - Distributed processing to prevent overload
    - Automatic retry logic for failed recalculations
    - Priority-based processing for new players
    - Comprehensive monitoring and statistics
    """
    
    def __init__(self):
        """Initialize the prestige scheduler."""
        self.logger = logger.bind(service="prestige_scheduler")
        self.status = PrestigeSchedulerStatus.STOPPED
        self.stats = PrestigeSchedulerStats()
        
        # Control flags
        self._running = False
        self._should_stop = False
        self._scheduler_task: Optional[asyncio.Task] = None
        
        # Task management
        self._pending_tasks: List[PrestigeRecalculationTask] = []
        self._processing_tasks: Set[str] = set()  # Wallets currently being processed
        
        # Configuration
        self.batch_size = getattr(settings, 'prestige_scheduler_batch_size', 50)
        self.max_workers = getattr(settings, 'prestige_scheduler_max_workers', 5)
        self.update_interval = getattr(settings, 'prestige_scheduler_interval', 3600)  # 1 hour
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
        
    async def initialize(self):
        """Initialize the scheduler."""
        try:
            self.status = PrestigeSchedulerStatus.STARTING
            self.logger.info("Initializing prestige scheduler")
            
            self.stats.start_time = datetime.utcnow()
            self.status = PrestigeSchedulerStatus.STOPPED
            
            self.logger.info("Prestige scheduler initialized successfully")
            
        except Exception as e:
            self.status = PrestigeSchedulerStatus.ERROR
            self.logger.error("Failed to initialize prestige scheduler", error=str(e))
            raise SchedulerError(f"Failed to initialize prestige scheduler: {e}")
            
    async def start(self):
        """Start the prestige scheduler."""
        if self.status == PrestigeSchedulerStatus.RUNNING:
            self.logger.warning("Prestige scheduler already running")
            return
            
        prestige_scheduler_enabled = getattr(settings, 'prestige_scheduler_enabled', True)
        if not prestige_scheduler_enabled:
            self.logger.info("Prestige scheduler disabled in configuration")
            return
            
        try:
            self.status = PrestigeSchedulerStatus.STARTING
            self._should_stop = False
            self._running = True
            
            self.logger.info("Starting prestige scheduler")
            
            # Start scheduler task
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            
            self.status = PrestigeSchedulerStatus.RUNNING
            self.logger.info("Prestige scheduler started successfully")
            
        except Exception as e:
            self.status = PrestigeSchedulerStatus.ERROR
            self._running = False
            self.logger.error("Failed to start prestige scheduler", error=str(e))
            raise SchedulerError(f"Failed to start prestige scheduler: {e}")
            
    async def stop(self):
        """Stop the prestige scheduler."""
        if self.status == PrestigeSchedulerStatus.STOPPED:
            return
            
        try:
            self.status = PrestigeSchedulerStatus.STOPPING
            self.logger.info("Stopping prestige scheduler")
            
            self._should_stop = True
            self._running = False
            
            # Cancel scheduler task
            if self._scheduler_task and not self._scheduler_task.done():
                self._scheduler_task.cancel()
                try:
                    await self._scheduler_task
                except asyncio.CancelledError:
                    pass
                    
            self.status = PrestigeSchedulerStatus.STOPPED
            self.logger.info("Prestige scheduler stopped")
            
        except Exception as e:
            self.status = PrestigeSchedulerStatus.ERROR
            self.logger.error("Error stopping prestige scheduler", error=str(e))
            
    async def shutdown(self):
        """Shutdown the scheduler completely."""
        await self.stop()
        self.logger.info("Prestige scheduler shutdown complete")
        
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        self.logger.info("Starting prestige scheduler loop")
        
        while not self._should_stop:
            try:
                self.stats.last_run = datetime.utcnow()
                
                # Load players that need prestige recalculation
                await self._load_pending_recalculations()
                
                # Process recalculations in batches
                await self._process_recalculation_batches()
                
                # Update next run time
                self.stats.next_run = datetime.utcnow() + timedelta(seconds=self.update_interval)
                
                # Wait for next cycle
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                self.logger.info("Prestige scheduler loop cancelled")
                break
                
            except Exception as e:
                self.logger.error("Error in prestige scheduler loop", error=str(e))
                self.stats.failed_recalculations += 1
                
                # Brief pause before retrying
                await asyncio.sleep(30)
                
        self.logger.info("Prestige scheduler loop stopped")
        
    async def _load_pending_recalculations(self):
        """Load players that need prestige recalculation."""
        try:
            current_time = datetime.utcnow()
            
            async with get_async_session() as db:
                # Get players that haven't had prestige updated recently
                # or players with no prestige update at all
                result = await db.execute(
                    select(Player.wallet)
                    .where(
                        and_(
                            Player.is_active == True,
                            or_(
                                Player.last_prestige_update.is_(None),
                                Player.last_prestige_update < current_time - timedelta(hours=24)
                            )
                        )
                    )
                    .order_by(Player.last_prestige_update.asc().nulls_first())
                    .limit(self.batch_size * 2)  # Load extra for better distribution
                )
                
                wallets = result.scalars().all()
                
                # Convert to recalculation tasks
                new_tasks = []
                for wallet in wallets:
                    # Skip if already being processed
                    if wallet in self._processing_tasks:
                        continue
                        
                    # Higher priority for players who never had prestige calculated
                    # Get player to check last_prestige_update
                    player_result = await db.execute(
                        select(Player.last_prestige_update).where(Player.wallet == wallet)
                    )
                    last_update = player_result.scalar_one_or_none()
                    
                    priority = 100 if last_update is None else 10
                    
                    task = PrestigeRecalculationTask(
                        wallet=wallet,
                        priority=priority
                    )
                    new_tasks.append(task)
                    
                # Add new tasks and sort by priority
                self._pending_tasks.extend(new_tasks)
                self._pending_tasks.sort(key=lambda t: t.priority, reverse=True)
                
                self.logger.debug(
                    "Loaded pending prestige recalculations",
                    players_found=len(wallets),
                    new_tasks=len(new_tasks),
                    total_pending=len(self._pending_tasks)
                )
                
        except Exception as e:
            self.logger.error("Failed to load pending recalculations", error=str(e))
            raise
            
    async def _process_recalculation_batches(self):
        """Process prestige recalculations in concurrent batches."""
        if not self._pending_tasks:
            return
            
        try:
            # Create worker tasks
            workers = []
            for i in range(min(self.max_workers, len(self._pending_tasks))):
                worker = asyncio.create_task(self._recalculation_worker(f"prestige-worker-{i}"))
                workers.append(worker)
                
            # Wait for all workers to complete
            await asyncio.gather(*workers, return_exceptions=True)
            
            self.logger.debug(
                "Prestige batch processing completed",
                workers=len(workers),
                remaining_tasks=len(self._pending_tasks)
            )
            
        except Exception as e:
            self.logger.error("Error in prestige batch processing", error=str(e))
            
    async def _recalculation_worker(self, worker_id: str):
        """Worker coroutine for processing prestige recalculations."""
        worker_logger = self.logger.bind(worker=worker_id)
        worker_logger.debug("Prestige worker started")
        
        try:
            while self._pending_tasks and not self._should_stop:
                # Get next task
                task = self._pending_tasks.pop(0)
                
                # Mark as processing
                self._processing_tasks.add(task.wallet)
                
                try:
                    await self._process_prestige_recalculation(task)
                    self.stats.successful_recalculations += 1
                    
                except Exception as e:
                    self.stats.failed_recalculations += 1
                    task.retry_count += 1
                    task.last_error = str(e)
                    
                    worker_logger.error(
                        "Prestige recalculation failed",
                        wallet=task.wallet,
                        retry_count=task.retry_count,
                        error=str(e)
                    )
                    
                    # Retry logic
                    if task.retry_count < 3:
                        # Re-queue for retry (with lower priority)
                        task.priority = max(0, task.priority - 10)
                        self._pending_tasks.append(task)
                    
                finally:
                    # Remove from processing set
                    self._processing_tasks.discard(task.wallet)
                    self.stats.recalculations_processed += 1
                    
                # Brief pause between updates
                await asyncio.sleep(0.2)
                
        except Exception as e:
            worker_logger.error("Prestige worker error", error=str(e))
            
        worker_logger.debug("Prestige worker finished")
        
    async def _process_prestige_recalculation(self, task: PrestigeRecalculationTask):
        """Process prestige recalculation for a single player."""
        try:
            wallet = task.wallet
            
            if not validate_wallet_address(wallet):
                raise SchedulerError(f"Invalid wallet address: {wallet}")
                
            self.logger.debug("Processing prestige recalculation", wallet=wallet)
            
            async with get_async_session() as db:
                # Get prestige service and recalculate
                prestige_service = await get_prestige_service(db)
                result = await prestige_service.recalculate_player_prestige(wallet)
                
                if result:
                    self.stats.players_processed += 1
                    self.stats.total_points_recalculated += result.get('total_points', 0)
                    
                    if result.get('level_changed', False):
                        self.stats.level_ups_triggered += 1
                    
                    self.logger.info(
                        "Prestige recalculated",
                        wallet=wallet,
                        total_points=result.get('total_points', 0),
                        level=result.get('level', 'unknown'),
                        level_changed=result.get('level_changed', False)
                    )
                else:
                    self.logger.warning("Player not found for prestige recalculation", wallet=wallet)
                
                await db.commit()
                
        except Exception as e:
            self.logger.error(
                "Failed to process prestige recalculation",
                wallet=task.wallet,
                error=str(e)
            )
            raise
            
    async def trigger_immediate_recalculation(self, wallet: str):
        """Trigger an immediate prestige recalculation for a player."""
        try:
            task = PrestigeRecalculationTask(
                wallet=wallet,
                priority=1000  # High priority
            )
            
            await self._process_prestige_recalculation(task)
            
            self.logger.info("Immediate prestige recalculation triggered", wallet=wallet)
            
        except Exception as e:
            self.logger.error(
                "Failed to trigger immediate prestige recalculation",
                wallet=wallet,
                error=str(e)
            )
            raise SchedulerError(f"Failed to trigger immediate recalculation: {e}")
            
    async def recalculate_all_players(self):
        """Trigger recalculation for all active players."""
        try:
            self.logger.info("Starting full prestige recalculation for all players")
            
            async with get_async_session() as db:
                # Get all active players
                result = await db.execute(
                    select(Player.wallet).where(Player.is_active == True)
                )
                wallets = result.scalars().all()
                
                # Add all to pending tasks with normal priority
                new_tasks = [
                    PrestigeRecalculationTask(wallet=wallet, priority=50)
                    for wallet in wallets
                    if wallet not in self._processing_tasks
                ]
                
                self._pending_tasks.extend(new_tasks)
                self._pending_tasks.sort(key=lambda t: t.priority, reverse=True)
                
                self.logger.info(
                    "Added all players for prestige recalculation",
                    total_players=len(wallets),
                    new_tasks=len(new_tasks),
                    total_pending=len(self._pending_tasks)
                )
                
        except Exception as e:
            self.logger.error("Failed to queue all players for recalculation", error=str(e))
            raise SchedulerError(f"Failed to queue all players for recalculation: {e}")
            
    async def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status and statistics."""
        async with get_async_session() as db:
            # Get player statistics
            total_players_result = await db.execute(
                select(func.count(Player.wallet)).where(Player.is_active == True)
            )
            total_players = total_players_result.scalar()
            
            players_with_prestige_result = await db.execute(
                select(func.count(Player.wallet)).where(
                    and_(
                        Player.is_active == True,
                        Player.prestige_points > 0
                    )
                )
            )
            players_with_prestige = players_with_prestige_result.scalar()
            
            # Get level distribution
            level_distribution_result = await db.execute(
                select(
                    Player.prestige_level,
                    func.count(Player.wallet).label("count")
                ).where(Player.is_active == True)
                .group_by(Player.prestige_level)
            )
            level_distribution = {level: count for level, count in level_distribution_result.all()}
            
        return {
            "status": self.status.value,
            "running": self._running,
            "stats": asdict(self.stats),
            "players": {
                "total_active": total_players,
                "with_prestige": players_with_prestige,
                "level_distribution": level_distribution
            },
            "tasks": {
                "pending": len(self._pending_tasks),
                "processing": len(self._processing_tasks)
            },
            "config": {
                "batch_size": self.batch_size,
                "max_workers": self.max_workers,
                "update_interval": self.update_interval
            }
        }


# Global scheduler instance
_prestige_scheduler: Optional[PrestigeScheduler] = None


async def get_prestige_scheduler() -> PrestigeScheduler:
    """Get or create a global prestige scheduler instance."""
    global _prestige_scheduler
    if _prestige_scheduler is None:
        _prestige_scheduler = PrestigeScheduler()
        await _prestige_scheduler.initialize()
    return _prestige_scheduler


async def shutdown_prestige_scheduler():
    """Shutdown the global prestige scheduler instance."""
    global _prestige_scheduler
    if _prestige_scheduler:
        await _prestige_scheduler.shutdown()
        _prestige_scheduler = None
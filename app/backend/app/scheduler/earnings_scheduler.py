"""
Earnings scheduler service for automated earnings updates.
Monitors player earnings schedules and triggers updates at appropriate times.
"""

import asyncio
from typing import Dict, List, Optional, Set, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import random

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func
import structlog

from app.core.database import get_async_session
from app.core.config import settings
from app.core.exceptions import SchedulerError, SolanaError
from app.services.solana_client import SolanaClient, get_solana_client
from app.services.referral_service import ReferralService
from app.models.player import Player
from app.models.business import Business
from app.models.earnings import EarningsSchedule
from app.models.user import User
from app.models.referral import ReferralRelation
from app.utils.validation import validate_wallet_address


logger = structlog.get_logger(__name__)


class SchedulerStatus(Enum):
    """Status of the earnings scheduler."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class SchedulerStats:
    """Statistics for scheduler operations."""
    updates_processed: int = 0
    successful_updates: int = 0
    failed_updates: int = 0
    players_processed: int = 0
    total_earnings_updated: int = 0
    start_time: Optional[datetime] = None
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


@dataclass
class EarningsUpdateTask:
    """Task for updating a player's earnings."""
    wallet: str
    scheduled_time: datetime
    priority: int = 0
    retry_count: int = 0
    last_error: Optional[str] = None


class EarningsScheduler:
    """
    Automated earnings scheduler for Solana Mafia players.
    
    Features:
    - Distributed scheduling to prevent RPC overload
    - Automatic retry logic for failed updates
    - Priority-based processing
    - Load balancing across time windows
    - Comprehensive monitoring and statistics
    """
    
    def __init__(self):
        """Initialize the earnings scheduler."""
        self.logger = logger.bind(service="earnings_scheduler")
        self.status = SchedulerStatus.STOPPED
        self.stats = SchedulerStats()
        
        # Services
        self.solana_client: Optional[SolanaClient] = None
        
        # Control flags
        self._running = False
        self._should_stop = False
        self._scheduler_task: Optional[asyncio.Task] = None
        
        # Task management
        self._pending_tasks: List[EarningsUpdateTask] = []
        self._processing_tasks: Set[str] = set()  # Wallets currently being processed
        
        # Configuration
        self.batch_size = settings.scheduler_batch_size
        self.max_workers = settings.scheduler_max_workers
        self.update_interval = settings.scheduler_interval
        
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
            self.status = SchedulerStatus.STARTING
            self.logger.info("Initializing earnings scheduler")
            
            # Initialize Solana client
            self.solana_client = await get_solana_client()
            
            self.stats.start_time = datetime.utcnow()
            self.status = SchedulerStatus.STOPPED
            
            self.logger.info("Earnings scheduler initialized successfully")
            
        except Exception as e:
            self.status = SchedulerStatus.ERROR
            self.logger.error("Failed to initialize earnings scheduler", error=str(e))
            raise SchedulerError(f"Failed to initialize earnings scheduler: {e}")
            
    async def start(self):
        """Start the earnings scheduler."""
        if self.status == SchedulerStatus.RUNNING:
            self.logger.warning("Earnings scheduler already running")
            return
            
        if not settings.scheduler_enabled:
            self.logger.info("Earnings scheduler disabled in configuration")
            return
            
        try:
            self.status = SchedulerStatus.STARTING
            self._should_stop = False
            self._running = True
            
            self.logger.info("Starting earnings scheduler")
            
            # Start scheduler task
            self._scheduler_task = asyncio.create_task(self._scheduler_loop())
            
            self.status = SchedulerStatus.RUNNING
            self.logger.info("Earnings scheduler started successfully")
            
        except Exception as e:
            self.status = SchedulerStatus.ERROR
            self._running = False
            self.logger.error("Failed to start earnings scheduler", error=str(e))
            raise SchedulerError(f"Failed to start earnings scheduler: {e}")
            
    async def stop(self):
        """Stop the earnings scheduler."""
        if self.status == SchedulerStatus.STOPPED:
            return
            
        try:
            self.status = SchedulerStatus.STOPPING
            self.logger.info("Stopping earnings scheduler")
            
            self._should_stop = True
            self._running = False
            
            # Cancel scheduler task
            if self._scheduler_task and not self._scheduler_task.done():
                self._scheduler_task.cancel()
                try:
                    await self._scheduler_task
                except asyncio.CancelledError:
                    pass
                    
            self.status = SchedulerStatus.STOPPED
            self.logger.info("Earnings scheduler stopped")
            
        except Exception as e:
            self.status = SchedulerStatus.ERROR
            self.logger.error("Error stopping earnings scheduler", error=str(e))
            
    async def shutdown(self):
        """Shutdown the scheduler completely."""
        await self.stop()
        
        if self.solana_client:
            await self.solana_client.close()
            
        self.logger.info("Earnings scheduler shutdown complete")
        
    async def _scheduler_loop(self):
        """Main scheduler loop."""
        self.logger.info("Starting scheduler loop")
        
        while not self._should_stop:
            try:
                self.stats.last_run = datetime.utcnow()
                
                # Load pending earnings updates
                await self._load_pending_updates()
                
                # Process updates in batches
                await self._process_update_batches()
                
                # Update next run time
                self.stats.next_run = datetime.utcnow() + timedelta(seconds=self.update_interval)
                
                # Wait for next cycle
                await asyncio.sleep(self.update_interval)
                
            except asyncio.CancelledError:
                self.logger.info("Scheduler loop cancelled")
                break
                
            except Exception as e:
                self.logger.error("Error in scheduler loop", error=str(e))
                self.stats.failed_updates += 1
                
                # Brief pause before retrying
                await asyncio.sleep(10)
                
        self.logger.info("Scheduler loop stopped")
        
    async def _load_pending_updates(self):
        """Load pending earnings updates from the database."""
        try:
            current_time = datetime.utcnow()
            
            async with get_async_session() as db:
                # Get players whose earnings need updating
                result = await db.execute(
                    select(EarningsSchedule)
                    .where(
                        and_(
                            EarningsSchedule.is_active == True,
                            EarningsSchedule.next_update_time <= current_time
                        )
                    )
                    .order_by(EarningsSchedule.next_update_time)
                    .limit(self.batch_size * 2)  # Load extra for better distribution
                )
                
                schedules = result.scalars().all()
                
                # Convert to update tasks
                new_tasks = []
                for schedule in schedules:
                    # Skip if already being processed
                    if schedule.player_wallet in self._processing_tasks:
                        continue
                        
                    # Calculate priority (earlier updates have higher priority)
                    delay_minutes = (current_time - schedule.next_update_time).total_seconds() / 60
                    priority = max(0, int(delay_minutes))
                    
                    task = EarningsUpdateTask(
                        wallet=schedule.player_wallet,
                        scheduled_time=schedule.next_update_time,
                        priority=priority
                    )
                    new_tasks.append(task)
                    
                # Add new tasks and sort by priority
                self._pending_tasks.extend(new_tasks)
                self._pending_tasks.sort(key=lambda t: t.priority, reverse=True)
                
                self.logger.debug(
                    "Loaded pending updates",
                    schedules_found=len(schedules),
                    new_tasks=len(new_tasks),
                    total_pending=len(self._pending_tasks)
                )
                
        except Exception as e:
            self.logger.error("Failed to load pending updates", error=str(e))
            raise
            
    async def _process_update_batches(self):
        """Process earnings updates in concurrent batches."""
        if not self._pending_tasks:
            return
            
        try:
            # Create worker tasks
            workers = []
            for i in range(min(self.max_workers, len(self._pending_tasks))):
                worker = asyncio.create_task(self._update_worker(f"worker-{i}"))
                workers.append(worker)
                
            # Wait for all workers to complete
            await asyncio.gather(*workers, return_exceptions=True)
            
            self.logger.debug(
                "Batch processing completed",
                workers=len(workers),
                remaining_tasks=len(self._pending_tasks)
            )
            
        except Exception as e:
            self.logger.error("Error in batch processing", error=str(e))
            
    async def _update_worker(self, worker_id: str):
        """Worker coroutine for processing earnings updates."""
        worker_logger = self.logger.bind(worker=worker_id)
        worker_logger.debug("Worker started")
        
        try:
            while self._pending_tasks and not self._should_stop:
                # Get next task
                task = self._pending_tasks.pop(0)
                
                # Mark as processing
                self._processing_tasks.add(task.wallet)
                
                try:
                    await self._process_earnings_update(task)
                    self.stats.successful_updates += 1
                    
                except Exception as e:
                    self.stats.failed_updates += 1
                    task.retry_count += 1
                    task.last_error = str(e)
                    
                    worker_logger.error(
                        "Earnings update failed",
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
                    self.stats.updates_processed += 1
                    
                # Brief pause between updates to avoid overwhelming RPC
                await asyncio.sleep(0.1)
                
        except Exception as e:
            worker_logger.error("Worker error", error=str(e))
            
        worker_logger.debug("Worker finished")
        
    async def _process_earnings_update(self, task: EarningsUpdateTask):
        """Process earnings update for a single player."""
        try:
            wallet = task.wallet
            
            if not validate_wallet_address(wallet):
                raise SchedulerError(f"Invalid wallet address: {wallet}")
                
            self.logger.debug("Processing earnings update", wallet=wallet)
            
            async with get_async_session() as db:
                # Get player data
                player_result = await db.execute(
                    select(Player).where(Player.wallet == wallet)
                )
                player = player_result.scalar_one_or_none()
                
                if not player:
                    self.logger.warning("Player not found", wallet=wallet)
                    return
                    
                # Get active businesses
                businesses_result = await db.execute(
                    select(Business).where(
                        and_(
                            Business.owner == wallet,
                            Business.is_active == True
                        )
                    )
                )
                businesses = businesses_result.scalars().all()
                
                if not businesses:
                    self.logger.debug("No active businesses", wallet=wallet)
                    # Still update the schedule for next check
                    await self._update_earnings_schedule(db, wallet)
                    return
                    
                # Calculate earnings since last update
                time_since_update = datetime.utcnow() - player.last_earnings_update
                hours_elapsed = time_since_update.total_seconds() / 3600
                
                total_earnings = 0
                for business in businesses:
                    business_earnings = int(business.earnings_per_hour * hours_elapsed)
                    total_earnings += business_earnings
                    
                if total_earnings > 0:
                    # Update player earnings (this would typically trigger a blockchain transaction)
                    # For now, we'll just update the database
                    await db.execute(
                        update(Player)
                        .where(Player.wallet == wallet)
                        .values(
                            earnings_balance=Player.earnings_balance + total_earnings,
                            last_earnings_update=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                    )
                    
                    # Process referral commissions
                    await self._process_referral_commissions(
                        db, wallet, total_earnings
                    )
                    
                    self.stats.total_earnings_updated += total_earnings
                    self.stats.players_processed += 1
                    
                    self.logger.info(
                        "Earnings updated",
                        wallet=wallet,
                        earnings=total_earnings,
                        businesses_count=len(businesses)
                    )
                
                # Update schedule for next update
                await self._update_earnings_schedule(db, wallet)
                
                await db.commit()
                
        except Exception as e:
            self.logger.error(
                "Failed to process earnings update",
                wallet=task.wallet,
                error=str(e)
            )
            raise
            
    async def _update_earnings_schedule(self, db: AsyncSession, wallet: str):
        """Update the earnings schedule for the next update."""
        try:
            # Calculate next update time with some randomization to distribute load
            base_interval = 3600  # 1 hour base interval
            jitter = random.randint(-300, 300)  # ±5 minutes jitter
            next_update = datetime.utcnow() + timedelta(seconds=base_interval + jitter)
            
            await db.execute(
                update(EarningsSchedule)
                .where(EarningsSchedule.player_wallet == wallet)
                .values(
                    next_update_time=next_update,
                    last_update=datetime.utcnow(),
                    update_count=EarningsSchedule.update_count + 1
                )
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to update earnings schedule",
                wallet=wallet,
                error=str(e)
            )
            raise
    
    async def _process_referral_commissions(
        self, 
        db: AsyncSession, 
        player_wallet: str, 
        earnings_amount: int
    ):
        """Process referral commissions for a player's earnings."""
        try:
            # First check if this is a wallet user or find corresponding user
            user_id = player_wallet  # For wallet users, user_id is the wallet address
            
            # Try to find if this wallet is linked to a Telegram user
            result = await db.execute(
                select(User).where(User.wallet_address == player_wallet)
            )
            user = result.scalar_one_or_none()
            
            if user and user.user_type == "telegram":
                user_id = user.id  # Use the telegram user ID format
            
            # Process referral commissions
            referral_service = ReferralService(db)
            commissions = await referral_service.process_earning_commission(
                user_id=user_id,
                earning_amount=earnings_amount,
                earning_event_id=f"earnings_{player_wallet}_{int(datetime.utcnow().timestamp())}"
            )
            
            if commissions:
                self.logger.info(
                    "Referral commissions processed",
                    player_wallet=player_wallet,
                    user_id=user_id,
                    earnings_amount=earnings_amount,
                    commissions_count=len(commissions),
                    total_commission=sum(c.commission_amount for c in commissions)
                )
                
                # Update pending referral earnings for referrers
                for commission in commissions:
                    relation_result = await db.execute(
                        select(ReferralRelation).where(
                            ReferralRelation.id == commission.referral_relation_id
                        )
                    )
                    relation = relation_result.scalar_one()
                    
                    # Update referrer's pending earnings
                    referrer_id = relation.referrer_id
                    
                    # Check if referrer is a wallet or telegram user
                    if referrer_id.startswith('tg_'):
                        # Telegram user - find their User record
                        referrer_result = await db.execute(
                            select(User).where(User.id == referrer_id)
                        )
                        referrer_user = referrer_result.scalar_one_or_none()
                        
                        if referrer_user:
                            await db.execute(
                                update(User)
                                .where(User.id == referrer_id)
                                .values(
                                    pending_referral_earnings=User.pending_referral_earnings + commission.commission_amount
                                )
                            )
                    else:
                        # Wallet user - update Player record
                        await db.execute(
                            update(Player)
                            .where(Player.wallet == referrer_id)
                            .values(
                                pending_referral_earnings=Player.pending_referral_earnings + commission.commission_amount
                            )
                        )
                        
                        # Also update User record if it exists
                        await db.execute(
                            update(User)
                            .where(User.wallet_address == referrer_id)
                            .values(
                                pending_referral_earnings=User.pending_referral_earnings + commission.commission_amount
                            )
                        )
            
        except Exception as e:
            self.logger.error(
                "Failed to process referral commissions",
                player_wallet=player_wallet,
                earnings_amount=earnings_amount,
                error=str(e)
            )
            # Don't raise - referral commission failures shouldn't break earnings updates
            
    async def add_player_to_schedule(self, wallet: str, immediate: bool = False):
        """Add a player to the earnings schedule."""
        try:
            if not validate_wallet_address(wallet):
                raise SchedulerError(f"Invalid wallet address: {wallet}")
                
            async with get_async_session() as db:
                # Check if schedule already exists
                result = await db.execute(
                    select(EarningsSchedule).where(EarningsSchedule.player_wallet == wallet)
                )
                existing_schedule = result.scalar_one_or_none()
                
                if existing_schedule:
                    if immediate:
                        # Update to trigger immediate processing
                        await db.execute(
                            update(EarningsSchedule)
                            .where(EarningsSchedule.player_wallet == wallet)
                            .values(
                                next_update_time=datetime.utcnow(),
                                is_active=True
                            )
                        )
                    else:
                        # Just activate if inactive
                        await db.execute(
                            update(EarningsSchedule)
                            .where(EarningsSchedule.player_wallet == wallet)
                            .values(is_active=True)
                        )
                else:
                    # Create new schedule
                    next_update = (
                        datetime.utcnow() if immediate
                        else datetime.utcnow() + timedelta(hours=1)
                    )
                    
                    schedule = EarningsSchedule(
                        wallet=wallet,
                        next_update_time=next_update,
                        update_interval=3600,
                        is_active=True
                    )
                    
                    db.add(schedule)
                    
                await db.commit()
                
                self.logger.info(
                    "Player added to earnings schedule",
                    wallet=wallet,
                    immediate=immediate
                )
                
        except Exception as e:
            self.logger.error(
                "Failed to add player to schedule",
                wallet=wallet,
                error=str(e)
            )
            raise SchedulerError(f"Failed to add player to schedule: {e}")
            
    async def remove_player_from_schedule(self, wallet: str):
        """Remove a player from the earnings schedule."""
        try:
            async with get_async_session() as db:
                await db.execute(
                    update(EarningsSchedule)
                    .where(EarningsSchedule.player_wallet == wallet)
                    .values(is_active=False)
                )
                
                await db.commit()
                
                self.logger.info("Player removed from earnings schedule", wallet=wallet)
                
        except Exception as e:
            self.logger.error(
                "Failed to remove player from schedule",
                wallet=wallet,
                error=str(e)
            )
            raise SchedulerError(f"Failed to remove player from schedule: {e}")
            
    async def trigger_immediate_update(self, wallet: str):
        """Trigger an immediate earnings update for a player."""
        try:
            task = EarningsUpdateTask(
                wallet=wallet,
                scheduled_time=datetime.utcnow(),
                priority=1000  # High priority
            )
            
            await self._process_earnings_update(task)
            
            self.logger.info("Immediate earnings update triggered", wallet=wallet)
            
        except Exception as e:
            self.logger.error(
                "Failed to trigger immediate update",
                wallet=wallet,
                error=str(e)
            )
            raise SchedulerError(f"Failed to trigger immediate update: {e}")
            
    async def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status and statistics."""
        async with get_async_session() as db:
            # Get schedule statistics
            total_schedules_result = await db.execute(
                select(func.count(EarningsSchedule.player_wallet))
            )
            total_schedules = total_schedules_result.scalar()
            
            active_schedules_result = await db.execute(
                select(func.count(EarningsSchedule.player_wallet))
                .where(EarningsSchedule.is_active == True)
            )
            active_schedules = active_schedules_result.scalar()
            
            pending_updates_result = await db.execute(
                select(func.count(EarningsSchedule.player_wallet))
                .where(
                    and_(
                        EarningsSchedule.is_active == True,
                        EarningsSchedule.next_update_time <= datetime.utcnow()
                    )
                )
            )
            pending_updates = pending_updates_result.scalar()
            
        return {
            "status": self.status.value,
            "running": self._running,
            "stats": asdict(self.stats),
            "schedules": {
                "total": total_schedules,
                "active": active_schedules,
                "pending_updates": pending_updates
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
_earnings_scheduler: Optional[EarningsScheduler] = None


async def get_earnings_scheduler() -> EarningsScheduler:
    """Get or create a global earnings scheduler instance."""
    global _earnings_scheduler
    if _earnings_scheduler is None:
        _earnings_scheduler = EarningsScheduler()
        await _earnings_scheduler.initialize()
    return _earnings_scheduler


async def shutdown_earnings_scheduler():
    """Shutdown the global earnings scheduler instance."""
    global _earnings_scheduler
    if _earnings_scheduler:
        await _earnings_scheduler.shutdown()
        _earnings_scheduler = None
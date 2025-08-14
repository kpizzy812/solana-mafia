"""
Daily earnings tracking service for ensuring all players receive their earnings.
This service provides guaranteed tracking and recovery mechanisms for failed earnings.
"""

from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func, desc
from sqlalchemy.orm import selectinload

import structlog

from app.models.daily_earnings import (
    DailyEarningsRun, 
    PlayerDailyEarningsStatus,
    EarningsRunStatus,
    PlayerEarningsStatus
)
from app.models.player import Player
from app.models.business import Business
from app.core.database import get_async_session


logger = structlog.get_logger(__name__)


@dataclass
class EarningsRunSummary:
    """Summary of an earnings run for reporting."""
    run_id: int
    earnings_date: date
    status: str
    total_players: int
    successful: int
    failed: int
    success_rate: float
    started_at: datetime
    completed_at: Optional[datetime]
    duration_minutes: Optional[int]
    failed_players: List[str]


@dataclass
class PlayerEarningsInfo:
    """Information about a player's businesses and expected earnings."""
    wallet: str
    businesses_count: int
    total_levels: int
    expected_earnings: int


class DailyEarningsTracker:
    """
    Service for tracking daily earnings processing with full accountability.
    Ensures no player is missed and provides recovery mechanisms.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logger.bind(service="daily_earnings_tracker")
    
    async def start_daily_run(
        self, 
        earnings_date: date,
        triggered_by: str = "scheduler",
        admin_wallet: Optional[str] = None
    ) -> DailyEarningsRun:
        """
        Start a new daily earnings run with full tracking.
        
        Args:
            earnings_date: Date to process earnings for
            triggered_by: What triggered this run (scheduler/manual/retry)
            admin_wallet: Admin wallet if manually triggered
            
        Returns:
            DailyEarningsRun: The created earnings run record
        """
        self.logger.info(
            "Starting daily earnings run",
            earnings_date=earnings_date.isoformat(),
            triggered_by=triggered_by
        )
        
        # Check if run already exists for this date
        existing_run = await self._get_latest_run_for_date(earnings_date)
        if existing_run and existing_run.status == EarningsRunStatus.COMPLETED:
            self.logger.warning(
                "Earnings run already completed for date",
                earnings_date=earnings_date.isoformat(),
                existing_run_id=existing_run.id
            )
            raise ValueError(f"Earnings already processed for {earnings_date}")
        
        # Get all players with businesses
        players_info = await self._get_players_with_businesses()
        
        # Create new earnings run
        earnings_run = DailyEarningsRun(
            earnings_date=earnings_date,
            status=EarningsRunStatus.STARTED,
            total_players_found=len(players_info),
            triggered_by=triggered_by,
            processed_by_admin=admin_wallet
        )
        
        self.db.add(earnings_run)
        await self.db.flush()  # Get the ID
        
        # Create status records for all players
        player_statuses = []
        for player_info in players_info:
            status = PlayerDailyEarningsStatus(
                player_wallet=player_info.wallet,
                earnings_date=earnings_date,
                earnings_run_id=earnings_run.id,
                status=PlayerEarningsStatus.PENDING,
                businesses_count=player_info.businesses_count,
                total_business_levels=player_info.total_levels,
                expected_earnings_lamports=player_info.expected_earnings
            )
            player_statuses.append(status)
        
        self.db.add_all(player_statuses)
        
        # Update run status
        earnings_run.status = EarningsRunStatus.IN_PROGRESS
        earnings_run.total_batches = (len(players_info) + 499) // 500  # Calculate batches
        
        await self.db.commit()
        
        self.logger.info(
            "Daily earnings run started",
            run_id=earnings_run.id,
            total_players=len(players_info),
            expected_batches=earnings_run.total_batches
        )
        
        return earnings_run
    
    async def mark_player_processing(
        self, 
        run_id: int, 
        player_wallet: str
    ) -> None:
        """Mark a player as currently being processed."""
        await self.db.execute(
            update(PlayerDailyEarningsStatus)
            .where(
                and_(
                    PlayerDailyEarningsStatus.earnings_run_id == run_id,
                    PlayerDailyEarningsStatus.player_wallet == player_wallet
                )
            )
            .values(
                status=PlayerEarningsStatus.PROCESSING,
                first_attempt_at=datetime.utcnow(),
                last_attempt_at=datetime.utcnow(),
                processing_attempts=PlayerDailyEarningsStatus.processing_attempts + 1
            )
        )
    
    async def mark_player_success(
        self, 
        run_id: int, 
        player_wallet: str, 
        actual_earnings: int
    ) -> None:
        """Mark a player as successfully processed."""
        await self.db.execute(
            update(PlayerDailyEarningsStatus)
            .where(
                and_(
                    PlayerDailyEarningsStatus.earnings_run_id == run_id,
                    PlayerDailyEarningsStatus.player_wallet == player_wallet
                )
            )
            .values(
                status=PlayerEarningsStatus.SUCCESS,
                actual_earnings_applied=actual_earnings,
                success_at=datetime.utcnow(),
                last_attempt_at=datetime.utcnow()
            )
        )
        
        # Update run statistics
        await self.db.execute(
            update(DailyEarningsRun)
            .where(DailyEarningsRun.id == run_id)
            .values(players_processed=DailyEarningsRun.players_processed + 1)
        )
    
    async def mark_player_failed(
        self, 
        run_id: int, 
        player_wallet: str, 
        error_message: str,
        is_blockchain_error: bool = False,
        needs_manual_review: bool = False
    ) -> None:
        """Mark a player as failed processing."""
        await self.db.execute(
            update(PlayerDailyEarningsStatus)
            .where(
                and_(
                    PlayerDailyEarningsStatus.earnings_run_id == run_id,
                    PlayerDailyEarningsStatus.player_wallet == player_wallet
                )
            )
            .values(
                status=PlayerEarningsStatus.MANUAL_FIX_NEEDED if needs_manual_review else PlayerEarningsStatus.FAILED,
                error_message=error_message,
                blockchain_error=is_blockchain_error,
                needs_manual_review=needs_manual_review,
                last_attempt_at=datetime.utcnow()
            )
        )
        
        # Update run statistics
        await self.db.execute(
            update(DailyEarningsRun)
            .where(DailyEarningsRun.id == run_id)
            .values(players_failed=DailyEarningsRun.players_failed + 1)
        )
    
    async def complete_daily_run(
        self, 
        run_id: int, 
        final_status: EarningsRunStatus = EarningsRunStatus.COMPLETED,
        error_message: Optional[str] = None
    ) -> EarningsRunSummary:
        """Complete a daily earnings run and return summary."""
        
        # Get run details
        result = await self.db.execute(
            select(DailyEarningsRun)
            .where(DailyEarningsRun.id == run_id)
        )
        earnings_run = result.scalar_one()
        
        # Calculate duration
        duration_seconds = None
        if earnings_run.started_at:
            duration_seconds = int((datetime.utcnow() - earnings_run.started_at).total_seconds())
        
        # Update run
        await self.db.execute(
            update(DailyEarningsRun)
            .where(DailyEarningsRun.id == run_id)
            .values(
                status=final_status,
                completed_at=datetime.utcnow(),
                processing_duration_seconds=duration_seconds,
                error_message=error_message
            )
        )
        
        await self.db.commit()
        
        # Get final summary
        summary = await self.get_run_summary(run_id)
        
        self.logger.info(
            "Daily earnings run completed",
            run_id=run_id,
            status=final_status.value,
            success_rate=summary.success_rate,
            failed_players_count=len(summary.failed_players)
        )
        
        return summary
    
    async def get_run_summary(self, run_id: int) -> EarningsRunSummary:
        """Get detailed summary of an earnings run."""
        
        # Get run details
        result = await self.db.execute(
            select(DailyEarningsRun)
            .where(DailyEarningsRun.id == run_id)
        )
        earnings_run = result.scalar_one()
        
        # Get failed players
        failed_result = await self.db.execute(
            select(PlayerDailyEarningsStatus.player_wallet)
            .where(
                and_(
                    PlayerDailyEarningsStatus.earnings_run_id == run_id,
                    PlayerDailyEarningsStatus.status.in_([
                        PlayerEarningsStatus.FAILED,
                        PlayerEarningsStatus.MANUAL_FIX_NEEDED
                    ])
                )
            )
        )
        failed_players = [row[0] for row in failed_result.fetchall()]
        
        # Calculate duration
        duration_minutes = None
        if earnings_run.started_at and earnings_run.completed_at:
            duration_minutes = int((earnings_run.completed_at - earnings_run.started_at).total_seconds() / 60)
        
        return EarningsRunSummary(
            run_id=run_id,
            earnings_date=earnings_run.earnings_date,
            status=earnings_run.status,
            total_players=earnings_run.total_players_found,
            successful=earnings_run.players_processed,
            failed=earnings_run.players_failed,
            success_rate=earnings_run.success_rate,
            started_at=earnings_run.started_at,
            completed_at=earnings_run.completed_at,
            duration_minutes=duration_minutes,
            failed_players=failed_players
        )
    
    async def get_failed_players_for_date(self, earnings_date: date) -> List[Dict[str, Any]]:
        """Get all players who failed processing for a specific date."""
        
        result = await self.db.execute(
            select(PlayerDailyEarningsStatus)
            .where(
                and_(
                    PlayerDailyEarningsStatus.earnings_date == earnings_date,
                    PlayerDailyEarningsStatus.status.in_([
                        PlayerEarningsStatus.FAILED,
                        PlayerEarningsStatus.MANUAL_FIX_NEEDED
                    ])
                )
            )
            .order_by(PlayerDailyEarningsStatus.last_attempt_at.desc())
        )
        
        failed_players = []
        for status in result.scalars().all():
            failed_players.append({
                "player_wallet": status.player_wallet,
                "status": status.status,
                "businesses_count": status.businesses_count,
                "expected_earnings": status.expected_earnings_lamports,
                "error_message": status.error_message,
                "blockchain_error": status.blockchain_error,
                "attempts": status.processing_attempts,
                "last_attempt": status.last_attempt_at,
                "needs_manual_review": status.needs_manual_review
            })
        
        return failed_players
    
    async def retry_failed_player(
        self, 
        player_wallet: str, 
        earnings_date: date,
        admin_wallet: str
    ) -> bool:
        """
        Retry processing for a specific failed player.
        
        Returns:
            bool: True if player was marked for retry, False if not found or already successful
        """
        
        result = await self.db.execute(
            select(PlayerDailyEarningsStatus)
            .where(
                and_(
                    PlayerDailyEarningsStatus.player_wallet == player_wallet,
                    PlayerDailyEarningsStatus.earnings_date == earnings_date,
                    PlayerDailyEarningsStatus.status.in_([
                        PlayerEarningsStatus.FAILED,
                        PlayerEarningsStatus.MANUAL_FIX_NEEDED
                    ])
                )
            )
        )
        
        status = result.scalar_one_or_none()
        if not status:
            return False
        
        # Reset status for retry
        await self.db.execute(
            update(PlayerDailyEarningsStatus)
            .where(PlayerDailyEarningsStatus.id == status.id)
            .values(
                status=PlayerEarningsStatus.PENDING,
                error_message=None,
                needs_manual_review=False,
                manually_resolved=False
            )
        )
        
        await self.db.commit()
        
        self.logger.info(
            "Player marked for retry",
            player_wallet=player_wallet,
            earnings_date=earnings_date.isoformat(),
            admin_wallet=admin_wallet
        )
        
        return True
    
    async def manually_resolve_player(
        self,
        player_wallet: str,
        earnings_date: date,
        admin_wallet: str,
        resolution_note: str,
        applied_earnings: Optional[int] = None
    ) -> bool:
        """
        Manually mark a player as resolved by admin.
        
        Args:
            player_wallet: Player to resolve
            earnings_date: Date to resolve for
            admin_wallet: Admin performing resolution
            resolution_note: Note about the resolution
            applied_earnings: Earnings amount if manually applied
            
        Returns:
            bool: True if resolved, False if not found
        """
        
        result = await self.db.execute(
            update(PlayerDailyEarningsStatus)
            .where(
                and_(
                    PlayerDailyEarningsStatus.player_wallet == player_wallet,
                    PlayerDailyEarningsStatus.earnings_date == earnings_date
                )
            )
            .values(
                status=PlayerEarningsStatus.SUCCESS,
                manually_resolved=True,
                resolved_by_admin=admin_wallet,
                resolution_note=resolution_note,
                actual_earnings_applied=applied_earnings,
                success_at=datetime.utcnow()
            )
        )
        
        rows_affected = result.rowcount
        await self.db.commit()
        
        if rows_affected > 0:
            self.logger.info(
                "Player manually resolved",
                player_wallet=player_wallet,
                earnings_date=earnings_date.isoformat(),
                admin_wallet=admin_wallet,
                applied_earnings=applied_earnings
            )
        
        return rows_affected > 0
    
    async def _get_latest_run_for_date(self, earnings_date: date) -> Optional[DailyEarningsRun]:
        """Get the latest earnings run for a specific date."""
        result = await self.db.execute(
            select(DailyEarningsRun)
            .where(DailyEarningsRun.earnings_date == earnings_date)
            .order_by(desc(DailyEarningsRun.started_at))
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def _get_players_with_businesses(self) -> List[PlayerEarningsInfo]:
        """Get all players who have businesses and should receive earnings."""
        
        # Query players with their businesses
        result = await self.db.execute(
            select(Player.wallet, func.count(Business.id), func.sum(Business.level))
            .select_from(Player)
            .join(Business, Player.wallet == Business.owner)
            .where(Business.is_active == True)
            .group_by(Player.wallet)
            .having(func.count(Business.id) > 0)
        )
        
        players_info = []
        for wallet, business_count, total_levels in result.fetchall():
            # Calculate expected earnings (simplified - would use actual business logic)
            expected_earnings = total_levels * 1000000  # 1 SOL per level per day (example)
            
            players_info.append(PlayerEarningsInfo(
                wallet=wallet,
                businesses_count=business_count,
                total_levels=total_levels or 0,
                expected_earnings=expected_earnings
            ))
        
        return players_info


# Service factory
async def get_daily_earnings_tracker(db: Optional[AsyncSession] = None) -> DailyEarningsTracker:
    """Get daily earnings tracker service."""
    if db is None:
        async with get_async_session() as session:
            return DailyEarningsTracker(session)
    return DailyEarningsTracker(db)
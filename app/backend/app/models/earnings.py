"""
Earnings-related models for scheduling and history tracking.
"""

from datetime import datetime, timedelta
from typing import Optional
from enum import Enum

from sqlalchemy import (
    String, Integer, BigInteger, Boolean, ForeignKey, Index, 
    Enum as SQLEnum, Text
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, TimestampMixin


class EarningsStatus(Enum):
    """Status of earnings processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class EarningsSchedule(BaseModel, TimestampMixin):
    """Schedule for automatic earnings updates."""
    
    __tablename__ = "earnings_schedule"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Player reference
    player_wallet: Mapped[str] = mapped_column(
        String(44),
        ForeignKey("players.wallet", ondelete="CASCADE"),
        comment="Player wallet address",
        index=True
    )
    
    # Scheduling
    next_update_time: Mapped[datetime] = mapped_column(
        comment="Next scheduled update time",
        index=True
    )
    
    update_interval: Mapped[int] = mapped_column(
        Integer,
        default=86400,  # 24 hours in seconds
        comment="Update interval in seconds"
    )
    
    # Status tracking
    status: Mapped[EarningsStatus] = mapped_column(
        SQLEnum(EarningsStatus),
        default=EarningsStatus.PENDING,
        comment="Current processing status"
    )
    
    last_update_attempt: Mapped[Optional[datetime]] = mapped_column(
        comment="Last update attempt timestamp"
    )
    
    last_successful_update: Mapped[Optional[datetime]] = mapped_column(
        comment="Last successful update timestamp"
    )
    
    # Error tracking
    consecutive_failures: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of consecutive failures"
    )
    
    last_error: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Last error message"
    )
    
    # Configuration
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether this schedule is active"
    )
    
    priority: Mapped[int] = mapped_column(
        Integer,
        default=5,
        comment="Processing priority (1=highest, 10=lowest)"
    )
    
    # Performance tracking
    average_processing_time: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Average processing time in milliseconds"
    )
    
    total_updates: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Total number of successful updates"
    )
    
    # Relationships
    player: Mapped["Player"] = relationship("Player")
    
    # Indexes
    __table_args__ = (
        Index("idx_earnings_schedule_next_update", "next_update_time", "is_active"),
        Index("idx_earnings_schedule_status", "status", "next_update_time"),
        Index("idx_earnings_schedule_failures", "consecutive_failures", "is_active"),
        Index("idx_earnings_schedule_priority", "priority", "next_update_time"),
    )
    
    def __repr__(self) -> str:
        return f"<EarningsSchedule(player={self.player_wallet}, next={self.next_update_time})>"
    
    @property
    def is_due(self) -> bool:
        """Check if earnings update is due."""
        return (
            self.is_active and 
            self.status != EarningsStatus.PROCESSING and
            datetime.utcnow() >= self.next_update_time
        )
    
    @property
    def is_overdue(self) -> bool:
        """Check if earnings update is overdue by more than 1 hour."""
        if not self.is_due:
            return False
        
        overdue_threshold = self.next_update_time + timedelta(hours=1)
        return datetime.utcnow() > overdue_threshold
    
    def schedule_next_update(self) -> None:
        """Schedule the next update based on interval."""
        self.next_update_time = datetime.utcnow() + timedelta(seconds=self.update_interval)
        self.status = EarningsStatus.PENDING
    
    def mark_processing(self) -> None:
        """Mark as currently being processed."""
        self.status = EarningsStatus.PROCESSING
        self.last_update_attempt = datetime.utcnow()
    
    def mark_completed(self, processing_time_ms: int) -> None:
        """Mark as successfully completed."""
        now = datetime.utcnow()
        self.status = EarningsStatus.COMPLETED
        self.last_successful_update = now
        self.consecutive_failures = 0
        self.last_error = None
        self.total_updates += 1
        
        # Update average processing time
        if self.average_processing_time is None:
            self.average_processing_time = processing_time_ms
        else:
            # Simple moving average
            self.average_processing_time = (
                self.average_processing_time + processing_time_ms
            ) // 2
        
        self.schedule_next_update()
    
    def mark_failed(self, error_message: str) -> None:
        """Mark as failed with error."""
        self.status = EarningsStatus.FAILED
        self.consecutive_failures += 1
        self.last_error = error_message
        
        # Exponential backoff for retries
        backoff_minutes = min(2 ** self.consecutive_failures, 60)
        self.next_update_time = datetime.utcnow() + timedelta(minutes=backoff_minutes)
    
    def reset_failures(self) -> None:
        """Reset failure counter."""
        self.consecutive_failures = 0
        self.last_error = None
        self.status = EarningsStatus.PENDING


class EarningsHistory(BaseModel, TimestampMixin):
    """Historical record of earnings updates and claims."""
    
    __tablename__ = "earnings_history"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Player reference
    player_wallet: Mapped[str] = mapped_column(
        String(44),
        ForeignKey("players.wallet", ondelete="CASCADE"),
        comment="Player wallet address",
        index=True
    )
    
    # Event type
    event_type: Mapped[str] = mapped_column(
        String(20),
        comment="Type of earnings event (update, claim)"
    )
    
    # Amounts
    amount: Mapped[int] = mapped_column(
        BigInteger,
        comment="Amount in lamports"
    )
    
    previous_balance: Mapped[int] = mapped_column(
        BigInteger,
        comment="Previous pending earnings balance"
    )
    
    new_balance: Mapped[int] = mapped_column(
        BigInteger,
        comment="New pending earnings balance"
    )
    
    # Source breakdown
    base_earnings: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Base business earnings"
    )
    
    slot_bonus_earnings: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Bonus earnings from premium slots"
    )
    
    referral_earnings: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Referral bonus earnings"
    )
    
    # Metadata
    business_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of active businesses at time of update"
    )
    
    transaction_signature: Mapped[Optional[str]] = mapped_column(
        String(88),
        comment="Related blockchain transaction"
    )
    
    # Processing info
    processing_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Processing time in milliseconds"
    )
    
    indexer_version: Mapped[str] = mapped_column(
        String(20),
        default="1.0",
        comment="Version of system that processed this"
    )
    
    # Relationships
    player: Mapped["Player"] = relationship(
        "Player",
        back_populates="earnings_history"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_earnings_history_player_time", "player_wallet", "created_at"),
        Index("idx_earnings_history_event_type", "event_type", "created_at"),
        Index("idx_earnings_history_amount", "amount"),
        Index("idx_earnings_history_signature", "transaction_signature"),
    )
    
    def __repr__(self) -> str:
        return f"<EarningsHistory(player={self.player_wallet}, type={self.event_type}, amount={self.amount})>"
    
    @property
    def amount_in_sol(self) -> float:
        """Get amount in SOL (assuming 1 SOL = 1e9 lamports)."""
        return self.amount / 1e9
    
    @classmethod
    def create_update_record(
        cls,
        player_wallet: str,
        amount: int,
        previous_balance: int,
        new_balance: int,
        business_count: int,
        base_earnings: int = 0,
        slot_bonus_earnings: int = 0,
        processing_time_ms: Optional[int] = None
    ) -> "EarningsHistory":
        """Create an earnings update record."""
        return cls(
            player_wallet=player_wallet,
            event_type="update",
            amount=amount,
            previous_balance=previous_balance,
            new_balance=new_balance,
            business_count=business_count,
            base_earnings=base_earnings,
            slot_bonus_earnings=slot_bonus_earnings,
            processing_time_ms=processing_time_ms
        )
    
    @classmethod
    def create_claim_record(
        cls,
        player_wallet: str,
        amount: int,
        previous_balance: int,
        transaction_signature: str,
        referral_earnings: int = 0
    ) -> "EarningsHistory":
        """Create an earnings claim record."""
        return cls(
            player_wallet=player_wallet,
            event_type="claim",
            amount=amount,
            previous_balance=previous_balance,
            new_balance=0,  # Balance is cleared after claim
            referral_earnings=referral_earnings,
            transaction_signature=transaction_signature
        )
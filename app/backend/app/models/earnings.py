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



class EarningsHistory(BaseModel, TimestampMixin):
    """Historical record of earnings updates and claims."""
    
    __tablename__ = "earnings_history"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Player reference
    player_wallet: Mapped[str] = mapped_column(
        String(44),
        ForeignKey("players.wallet", ondelete="CASCADE"),
        comment="Player wallet address"
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
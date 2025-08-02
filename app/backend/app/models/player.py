"""
Player model - mirrors the on-chain Player state with additional indexing.
"""

from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from sqlalchemy import (
    String, Integer, BigInteger, Boolean, DECIMAL, Text, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, TimestampMixin


class Player(BaseModel, TimestampMixin):
    """Player model mirroring on-chain Player account."""
    
    __tablename__ = "players"
    
    # Primary identifier
    wallet: Mapped[str] = mapped_column(
        String(44), 
        primary_key=True,
        comment="Player's wallet public key"
    )
    
    # Account state (mirrors on-chain data)
    total_invested: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Total amount invested in lamports"
    )
    
    total_upgrade_spent: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Total spent on upgrades in lamports"
    )
    
    total_slot_spent: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Total spent on slots in lamports"
    )
    
    total_earned: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Total earnings claimed in lamports"
    )
    
    pending_earnings: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Pending earnings in lamports"
    )
    
    pending_referral_earnings: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Pending referral earnings in lamports"
    )
    
    # Slot information
    unlocked_slots_count: Mapped[int] = mapped_column(
        Integer,
        default=3,
        comment="Number of unlocked regular slots"
    )
    
    premium_slots_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of premium slots owned"
    )
    
    # Status flags
    has_paid_entry: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether player has paid entry fee"
    )
    
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether player account is active"
    )
    
    # Timing information
    first_business_time: Mapped[Optional[datetime]] = mapped_column(
        comment="When player created their first business"
    )
    
    next_earnings_time: Mapped[Optional[datetime]] = mapped_column(
        comment="Next scheduled earnings update",
        index=True
    )
    
    last_earnings_update: Mapped[Optional[datetime]] = mapped_column(
        comment="Last earnings update timestamp"
    )
    
    earnings_interval: Mapped[int] = mapped_column(
        Integer,
        default=86400,  # 24 hours
        comment="Earnings update interval in seconds"
    )
    
    # Referral information
    referrer_wallet: Mapped[Optional[str]] = mapped_column(
        String(44),
        comment="Wallet of referring player"
    )
    
    referral_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of players referred"
    )
    
    # Additional tracking fields (not on-chain)
    transaction_signature: Mapped[Optional[str]] = mapped_column(
        String(88),
        comment="Transaction signature when player was created"
    )
    
    on_chain_created_at: Mapped[Optional[datetime]] = mapped_column(
        comment="Creation timestamp from on-chain data"
    )
    
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        comment="Last synchronization with on-chain data",
        index=True
    )
    
    sync_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Version for sync conflict resolution"
    )
    
    # Computed fields (updated by background processes)
    roi_percentage: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(10, 4),
        comment="Return on investment percentage"
    )
    
    daily_earnings_estimate: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Estimated daily earnings in lamports"
    )
    
    # Relationships
    businesses: Mapped[List["Business"]] = relationship(
        "Business",
        back_populates="player",
        cascade="all, delete-orphan"
    )
    
    nfts: Mapped[List["BusinessNFT"]] = relationship(
        "BusinessNFT",
        back_populates="player",
        cascade="all, delete-orphan"
    )
    
    earnings_history: Mapped[List["EarningsHistory"]] = relationship(
        "EarningsHistory",
        back_populates="player",
        cascade="all, delete-orphan"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_player_next_earnings", "next_earnings_time"),
        Index("idx_player_active_earnings", "is_active", "next_earnings_time"),
        Index("idx_player_created_at", "created_at"),
        Index("idx_player_referrer", "referrer_wallet"),
        Index("idx_player_sync", "last_sync_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Player(wallet={self.wallet}, businesses={len(self.businesses)})>"
    
    @property
    def total_slots(self) -> int:
        """Total number of slots (regular + premium)."""
        return self.unlocked_slots_count + self.premium_slots_count
    
    @property
    def net_profit(self) -> int:
        """Net profit (earnings - investments)."""
        total_investment = self.total_invested + self.total_upgrade_spent + self.total_slot_spent
        return self.total_earned - total_investment
    
    @property
    def is_earnings_due(self) -> bool:
        """Check if earnings update is due."""
        if not self.next_earnings_time:
            return False
        return datetime.utcnow() >= self.next_earnings_time
    
    def get_claimable_amount(self) -> int:
        """Get total claimable earnings."""
        return self.pending_earnings + self.pending_referral_earnings
    
    def update_roi(self) -> None:
        """Update ROI percentage."""
        total_investment = self.total_invested + self.total_upgrade_spent + self.total_slot_spent
        if total_investment > 0:
            self.roi_percentage = Decimal(self.total_earned) / Decimal(total_investment) * 100
        else:
            self.roi_percentage = Decimal(0)
"""
Player model - mirrors the on-chain Player state with additional indexing.
"""

from datetime import datetime
from typing import List, Optional
from decimal import Decimal

from sqlalchemy import (
    String, Integer, BigInteger, Boolean, DECIMAL, Text, Index, DateTime
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
        comment="Next scheduled earnings update"
    )
    
    last_earnings_update: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
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
        comment="Last synchronization with on-chain data"
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
    
    # Prestige system fields
    prestige_points: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Current prestige points"
    )
    
    prestige_level: Mapped[str] = mapped_column(
        String(20),
        default="wannabe",
        comment="Current prestige level (wannabe, associate, soldier, capo, underboss, boss)"
    )
    
    total_prestige_earned: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Total prestige points earned throughout gameplay"
    )
    
    prestige_level_up_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of times player leveled up in prestige"
    )
    
    last_prestige_update: Mapped[Optional[datetime]] = mapped_column(
        comment="Last time prestige was updated"
    )
    
    # Relationships
    businesses: Mapped[List["Business"]] = relationship(
        "Business",
        back_populates="player",
        cascade="all, delete-orphan",
        foreign_keys="Business.player_wallet"
    )
    
    # Убрано nfts relationship - NFT больше не используются
    
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
        Index("idx_player_prestige_level_main", "prestige_level"),
        Index("idx_player_prestige_points", "prestige_points"),
    )
    
    def __repr__(self) -> str:
        return f"<Player(wallet={self.wallet}, businesses={len(self.businesses)})>"
    
    @property
    def total_slots(self) -> int:
        """Total number of slots (regular + premium)."""
        return self.unlocked_slots_count + self.premium_slots_count
    
    def calculate_business_liquidation_value(self) -> int:
        """Calculate total liquidation value of all player's businesses."""
        try:
            # Safe access to businesses relationship
            businesses = getattr(self, '_businesses', None) or getattr(self, 'businesses', [])
            if not businesses:
                return 0
        except Exception:
            # If relationship access fails, return 0 (no liquidation value)
            return 0
        
        total_liquidation_value = 0
        current_time = datetime.utcnow()
        
        # Early sell fee schedule from smart contract (constants.rs)
        # Days 0-6: 25%, Days 7-13: 20%, Days 14-20: 15%, Days 21-27: 10%, Days 28-30: 5%, After: 2%
        early_sell_fees = [
            25, 25, 25, 25, 25, 25, 25,  # Days 0-6: 25%
            20, 20, 20, 20, 20, 20, 20,  # Days 7-13: 20%
            15, 15, 15, 15, 15, 15, 15,  # Days 14-20: 15%
            10, 10, 10, 10, 10, 10, 10,  # Days 21-27: 10%
            5,  5,  5,  2               # Days 28-30: 5%, final: 2%
        ]
        final_sell_fee_percent = 2
        
        for business in businesses:
            if not business.is_active:
                continue
                
            # Calculate days held
            if business.on_chain_created_at:
                days_held = (current_time - business.on_chain_created_at).days
            else:
                # Fallback to created_at if on_chain_created_at is not available
                days_held = (current_time - business.created_at).days if business.created_at else 0
            
            # Get base fee percentage based on days held
            if days_held < len(early_sell_fees):
                base_fee_percent = early_sell_fees[days_held]
            else:
                base_fee_percent = final_sell_fee_percent
            
            # TODO: Account for slot discounts (Premium/VIP/Legendary slots reduce fees)
            # For now, use base fee without slot discounts
            final_fee_percent = base_fee_percent
            
            # Calculate return amount (total invested - sell fee)
            total_invested = business.total_invested_amount
            sell_fee = (total_invested * final_fee_percent) // 100
            return_amount = total_invested - sell_fee
            
            total_liquidation_value += return_amount
        
        return total_liquidation_value

    @property
    def net_profit(self) -> int:
        """Net profit including current liquidation value of businesses."""
        total_investment = self.total_invested + self.total_upgrade_spent + self.total_slot_spent
        
        # Include ONLY claimed earnings + liquidation value of businesses
        # Pending earnings are NOT included to avoid double counting when they get claimed
        total_assets = (
            self.total_earned +  # Already claimed earnings
            self.calculate_business_liquidation_value()  # Current sale value of businesses
        )
        
        return total_assets - total_investment
    
    @property
    def is_earnings_due(self) -> bool:
        """Check if earnings update is due."""
        if not self.next_earnings_time:
            return False
        return datetime.utcnow() >= self.next_earnings_time
    
    def get_claimable_amount(self) -> int:
        """Get total claimable earnings."""
        return self.pending_earnings + self.pending_referral_earnings
    
    def add_prestige_points(self, points: int, source: str = "general") -> bool:
        """Add prestige points and return True if leveled up."""
        if points <= 0:
            return False
        
        old_level = self.prestige_level
        self.prestige_points += points
        self.total_prestige_earned += points
        self.last_prestige_update = datetime.utcnow()
        
        # Update level based on points (simplified calculation)
        new_level = self._calculate_prestige_level()
        if new_level != old_level:
            self.prestige_level = new_level
            self.prestige_level_up_count += 1
            return True
        
        return False
    
    def _calculate_prestige_level(self) -> str:
        """Calculate prestige level based on current points."""
        points = self.prestige_points
        
        if points >= 10000:
            return "boss"
        elif points >= 3000:
            return "underboss"
        elif points >= 800:
            return "capo"
        elif points >= 200:
            return "soldier"
        elif points >= 50:
            return "associate"
        else:
            return "wannabe"
    
    @property
    def prestige_progress_to_next(self) -> tuple[int, int]:
        """Get points needed for next level and progress percentage."""
        current_points = self.prestige_points
        
        level_thresholds = {
            "wannabe": 50,
            "associate": 200,
            "soldier": 800,
            "capo": 3000,
            "underboss": 10000,
            "boss": None  # No next level
        }
        
        next_threshold = level_thresholds.get(self.prestige_level)
        if next_threshold is None:
            return (0, 100)  # Boss level - already at max
        
        points_needed = next_threshold - current_points
        
        # Calculate progress within current level
        if self.prestige_level == "wannabe":
            progress = min(100, (current_points / 50) * 100)
        elif self.prestige_level == "associate":
            progress = min(100, ((current_points - 50) / 150) * 100)
        elif self.prestige_level == "soldier":
            progress = min(100, ((current_points - 200) / 600) * 100)
        elif self.prestige_level == "capo":
            progress = min(100, ((current_points - 800) / 2200) * 100)
        elif self.prestige_level == "underboss":
            progress = min(100, ((current_points - 3000) / 7000) * 100)
        else:
            progress = 100
        
        return (max(0, points_needed), int(progress))

    def update_roi(self) -> None:
        """Update ROI percentage."""
        total_investment = self.total_invested + self.total_upgrade_spent + self.total_slot_spent
        if total_investment > 0:
            self.roi_percentage = Decimal(self.total_earned) / Decimal(total_investment) * 100
        else:
            self.roi_percentage = Decimal(0)
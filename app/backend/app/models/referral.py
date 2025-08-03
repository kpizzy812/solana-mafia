"""
Referral system models for tracking multi-level referrals.
Supports 3-level referral system with 5%, 2%, 1% commission rates.
"""

import secrets
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal

from sqlalchemy import (
    String, Integer, BigInteger, Boolean, DECIMAL, Text, Index, 
    ForeignKey, DateTime, Float, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, TimestampMixin


class ReferralCode(BaseModel, TimestampMixin):
    """Referral codes for tracking referrals."""
    
    __tablename__ = "referral_codes"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Unique referral code
    code: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        comment="Unique referral code"
    )
    
    # Owner of the referral code
    owner_id: Mapped[str] = mapped_column(
        String(50),
        index=True,
        comment="Owner identifier (wallet address or tg_user_id)"
    )
    
    # Owner type (wallet or telegram)
    owner_type: Mapped[str] = mapped_column(
        String(20),
        comment="Type of owner: 'wallet' or 'telegram'"
    )
    
    # Usage tracking
    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of times this code was used"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether the code is active"
    )
    
    # Expiration (optional)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="Code expiration date (optional)"
    )
    
    # Relationships
    referrals: Mapped[List["ReferralRelation"]] = relationship(
        "ReferralRelation",
        back_populates="referral_code",
        foreign_keys="ReferralRelation.referral_code_id"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_referral_code_owner", "owner_id", "owner_type"),
        Index("idx_referral_code_active", "is_active", "expires_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ReferralCode(code={self.code}, owner={self.owner_id})>"
    
    @classmethod
    def generate_code(cls, length: int = 8) -> str:
        """Generate a unique referral code."""
        # Use URL-safe base64 encoding for readability
        return secrets.token_urlsafe(length)[:length].upper()
    
    @property
    def is_expired(self) -> bool:
        """Check if the code is expired."""
        if not self.expires_at:
            return False
        return datetime.utcnow() > self.expires_at


class ReferralRelation(BaseModel, TimestampMixin):
    """Referral relationships between users."""
    
    __tablename__ = "referral_relations"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Referrer (who referred)
    referrer_id: Mapped[str] = mapped_column(
        String(50),
        index=True,
        comment="Referrer identifier"
    )
    
    referrer_type: Mapped[str] = mapped_column(
        String(20),
        comment="Type of referrer: 'wallet' or 'telegram'"
    )
    
    # Referee (who was referred)
    referee_id: Mapped[str] = mapped_column(
        String(50),
        index=True,
        comment="Referee identifier"
    )
    
    referee_type: Mapped[str] = mapped_column(
        String(20),
        comment="Type of referee: 'wallet' or 'telegram'"
    )
    
    # Referral code used
    referral_code_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("referral_codes.id"),
        comment="Referral code that was used"
    )
    
    # Referral level (1, 2, or 3)
    level: Mapped[int] = mapped_column(
        Integer,
        comment="Referral level (1=direct, 2=second-level, 3=third-level)"
    )
    
    # Commission rate used (stored for historical accuracy)
    commission_rate: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4),
        comment="Commission rate at time of referral (e.g., 0.0500 for 5%)"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether this referral relation is active"
    )
    
    # Tracking
    first_earning_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="When referee first earned (triggering commissions)"
    )
    
    total_earnings_referred: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Total earnings from referee that triggered commissions"
    )
    
    total_commission_earned: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Total commission earned from this referral"
    )
    
    # Relationships
    referral_code: Mapped["ReferralCode"] = relationship(
        "ReferralCode",
        back_populates="referrals"
    )
    
    commission_history: Mapped[List["ReferralCommission"]] = relationship(
        "ReferralCommission",
        back_populates="referral_relation",
        cascade="all, delete-orphan"
    )
    
    # Constraints and indexes
    __table_args__ = (
        # Ensure no duplicate referral relations
        UniqueConstraint("referrer_id", "referee_id", name="unique_referral_relation"),
        # Indexes for performance
        Index("idx_referral_referrer", "referrer_id", "referrer_type"),
        Index("idx_referral_referee", "referee_id", "referee_type"),
        Index("idx_referral_level", "level"),
        Index("idx_referral_active", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<ReferralRelation(referrer={self.referrer_id}, referee={self.referee_id}, level={self.level})>"


class ReferralCommission(BaseModel, TimestampMixin):
    """Individual commission payments from referrals."""
    
    __tablename__ = "referral_commissions"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Referral relation this commission belongs to
    referral_relation_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("referral_relations.id"),
        comment="Referral relation that generated this commission"
    )
    
    # Commission details
    earning_event_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        comment="ID of the earning event that triggered this commission"
    )
    
    referee_earning_amount: Mapped[int] = mapped_column(
        BigInteger,
        comment="Amount the referee earned (that triggered commission)"
    )
    
    commission_amount: Mapped[int] = mapped_column(
        BigInteger,
        comment="Commission amount paid out"
    )
    
    commission_rate: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4),
        comment="Commission rate used for this payment"
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        comment="Status: pending, paid, failed"
    )
    
    # Blockchain transaction (if applicable)
    transaction_signature: Mapped[Optional[str]] = mapped_column(
        String(88),
        comment="Solana transaction signature for commission payment"
    )
    
    paid_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="When commission was paid"
    )
    
    # Relationships
    referral_relation: Mapped["ReferralRelation"] = relationship(
        "ReferralRelation",
        back_populates="commission_history"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_commission_relation", "referral_relation_id"),
        Index("idx_commission_status", "status"),
        Index("idx_commission_event", "earning_event_id"),
        Index("idx_commission_paid", "paid_at"),
    )
    
    def __repr__(self) -> str:
        return f"<ReferralCommission(amount={self.commission_amount}, status={self.status})>"


class ReferralStats(BaseModel, TimestampMixin):
    """Aggregated referral statistics for users."""
    
    __tablename__ = "referral_stats"
    
    # Primary key
    user_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        comment="User identifier"
    )
    
    user_type: Mapped[str] = mapped_column(
        String(20),
        comment="Type of user: 'wallet' or 'telegram'"
    )
    
    # Referral counts by level
    level_1_referrals: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Direct referrals count"
    )
    
    level_2_referrals: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Second-level referrals count"
    )
    
    level_3_referrals: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Third-level referrals count"
    )
    
    # Earnings by level
    level_1_earnings: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Total earnings from level 1 referrals"
    )
    
    level_2_earnings: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Total earnings from level 2 referrals"
    )
    
    level_3_earnings: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Total earnings from level 3 referrals"
    )
    
    # Overall stats
    total_referrals: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Total referrals across all levels"
    )
    
    total_referral_earnings: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Total referral earnings across all levels"
    )
    
    pending_commission: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        comment="Pending commission to be paid"
    )
    
    # Last update tracking
    last_updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        comment="Last time stats were updated"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_referral_stats_user", "user_id", "user_type"),
        Index("idx_referral_stats_total", "total_referrals"),
        Index("idx_referral_stats_earnings", "total_referral_earnings"),
    )
    
    def __repr__(self) -> str:
        return f"<ReferralStats(user={self.user_id}, total_referrals={self.total_referrals})>"
    
    @property
    def total_count(self) -> int:
        """Total referral count across all levels."""
        return self.level_1_referrals + self.level_2_referrals + self.level_3_referrals
    
    @property
    def total_earnings(self) -> int:
        """Total earnings across all levels."""
        return self.level_1_earnings + self.level_2_earnings + self.level_3_earnings
    
    def update_stats(self) -> None:
        """Update computed fields."""
        self.total_referrals = self.total_count
        self.total_referral_earnings = self.total_earnings
        self.last_updated_at = datetime.utcnow()


class ReferralConfig(BaseModel, TimestampMixin):
    """Configuration for the referral system."""
    
    __tablename__ = "referral_config"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Commission rates by level
    level_1_rate: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4),
        default=Decimal("0.0500"),  # 5%
        comment="Commission rate for level 1 referrals"
    )
    
    level_2_rate: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4),
        default=Decimal("0.0200"),  # 2%
        comment="Commission rate for level 2 referrals"
    )
    
    level_3_rate: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4),
        default=Decimal("0.0100"),  # 1%
        comment="Commission rate for level 3 referrals"
    )
    
    # System settings
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether referral system is enabled"
    )
    
    min_earning_threshold: Mapped[int] = mapped_column(
        BigInteger,
        default=1000000,  # 0.001 SOL in lamports
        comment="Minimum earning amount to trigger referral commission"
    )
    
    max_referral_levels: Mapped[int] = mapped_column(
        Integer,
        default=3,
        comment="Maximum referral levels"
    )
    
    # Active period (for versioning)
    active_from: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        comment="When this config becomes active"
    )
    
    active_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="When this config expires (null = indefinite)"
    )
    
    # Version for tracking changes
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Configuration version"
    )
    
    def __repr__(self) -> str:
        return f"<ReferralConfig(version={self.version}, rates={self.level_1_rate}/{self.level_2_rate}/{self.level_3_rate})>"
    
    @property
    def is_active(self) -> bool:
        """Check if this configuration is currently active."""
        now = datetime.utcnow()
        return (
            self.is_enabled and
            self.active_from <= now and
            (self.active_until is None or self.active_until > now)
        )
    
    def get_rate_for_level(self, level: int) -> Decimal:
        """Get commission rate for a specific level."""
        if level == 1:
            return self.level_1_rate
        elif level == 2:
            return self.level_2_rate
        elif level == 3:
            return self.level_3_rate
        else:
            return Decimal("0.0000")
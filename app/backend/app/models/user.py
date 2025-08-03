"""
Unified user model supporting both wallet and Telegram Mini Apps users.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    String, Integer, BigInteger, Boolean, DECIMAL, Text, Index, 
    JSON, DateTime, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, TimestampMixin


class UserType(str, Enum):
    """User authentication types."""
    WALLET = "wallet"
    TELEGRAM = "telegram"


class User(BaseModel, TimestampMixin):
    """Unified user model for both wallet and Telegram users."""
    
    __tablename__ = "users"
    
    # Primary identifier
    id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        comment="Unique user identifier (wallet address or tg_{telegram_user_id})"
    )
    
    # User type
    user_type: Mapped[str] = mapped_column(
        String(20),
        comment="User type: 'wallet' or 'telegram'"
    )
    
    # Wallet information (for wallet users or linked wallets)
    wallet_address: Mapped[Optional[str]] = mapped_column(
        String(44),
        unique=True,
        index=True,
        comment="Solana wallet address"
    )
    
    # Telegram information (for TMA users)
    telegram_user_id: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        unique=True,
        index=True,
        comment="Telegram user ID"
    )
    
    telegram_username: Mapped[Optional[str]] = mapped_column(
        String(32),
        comment="Telegram username"
    )
    
    first_name: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="User's first name"
    )
    
    last_name: Mapped[Optional[str]] = mapped_column(
        String(64),
        comment="User's last name"
    )
    
    language_code: Mapped[Optional[str]] = mapped_column(
        String(10),
        comment="User's language code"
    )
    
    is_telegram_premium: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        comment="Whether user has Telegram Premium"
    )
    
    telegram_photo_url: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Telegram profile photo URL"
    )
    
    # Account linking
    is_linked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether Telegram account is linked to a wallet"
    )
    
    linked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="When accounts were linked"
    )
    
    # Game data (mirrors player data)
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
    
    # Referral information
    referrer_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Referrer's user ID"
    )
    
    referral_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        unique=True,
        comment="User's unique referral code"
    )
    
    # Activity tracking
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="Last login timestamp"
    )
    
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="Last activity timestamp"
    )
    
    login_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Total login count"
    )
    
    # Status flags
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether user account is active"
    )
    
    is_banned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether user is banned"
    )
    
    # Metadata
    metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        comment="Additional user metadata"
    )
    
    # Relationships
    businesses: Mapped[List["Business"]] = relationship(
        "Business",
        back_populates="owner_user",
        cascade="all, delete-orphan",
        foreign_keys="Business.owner_id"
    )
    
    # Constraints and indexes
    __table_args__ = (
        # Ensure wallet users have wallet_address
        # CheckConstraint(
        #     "(user_type = 'wallet' AND wallet_address IS NOT NULL) OR "
        #     "(user_type = 'telegram' AND telegram_user_id IS NOT NULL)",
        #     name="check_user_type_fields"
        # ),
        # Indexes for performance
        Index("idx_user_type", "user_type"),
        Index("idx_user_wallet", "wallet_address"),
        Index("idx_user_telegram", "telegram_user_id"),
        Index("idx_user_referrer", "referrer_id"),
        Index("idx_user_active", "is_active"),
        Index("idx_user_last_activity", "last_activity_at"),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, type={self.user_type})>"
    
    @classmethod
    def create_wallet_user(cls, wallet_address: str) -> "User":
        """Create a new wallet user."""
        return cls(
            id=wallet_address,
            user_type=UserType.WALLET,
            wallet_address=wallet_address
        )
    
    @classmethod
    def create_telegram_user(
        cls, 
        telegram_user_id: int,
        first_name: str,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        language_code: Optional[str] = None,
        is_premium: Optional[bool] = None
    ) -> "User":
        """Create a new Telegram user."""
        user_id = f"tg_{telegram_user_id}"
        return cls(
            id=user_id,
            user_type=UserType.TELEGRAM,
            telegram_user_id=telegram_user_id,
            telegram_username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            is_telegram_premium=is_premium
        )
    
    @property
    def display_name(self) -> str:
        """Get display name for the user."""
        if self.user_type == UserType.TELEGRAM:
            if self.first_name:
                name = self.first_name
                if self.last_name:
                    name += f" {self.last_name}"
                return name
            elif self.telegram_username:
                return f"@{self.telegram_username}"
            else:
                return f"User {self.telegram_user_id}"
        else:
            return self.wallet_address or self.id
    
    @property
    def is_wallet_user(self) -> bool:
        """Check if this is a wallet user."""
        return self.user_type == UserType.WALLET
    
    @property
    def is_telegram_user(self) -> bool:
        """Check if this is a Telegram user."""
        return self.user_type == UserType.TELEGRAM
    
    @property
    def net_profit(self) -> int:
        """Net profit (earnings - investments)."""
        total_investment = self.total_invested + self.total_upgrade_spent + self.total_slot_spent
        return self.total_earned - total_investment
    
    def get_claimable_amount(self) -> int:
        """Get total claimable earnings."""
        return self.pending_earnings + self.pending_referral_earnings
    
    def link_wallet(self, wallet_address: str) -> None:
        """Link a wallet to this Telegram user."""
        if self.user_type != UserType.TELEGRAM:
            raise ValueError("Only Telegram users can link wallets")
        
        self.wallet_address = wallet_address
        self.is_linked = True
        self.linked_at = datetime.utcnow()
    
    def update_activity(self) -> None:
        """Update user activity timestamp."""
        self.last_activity_at = datetime.utcnow()
    
    def record_login(self) -> None:
        """Record a user login."""
        self.last_login_at = datetime.utcnow()
        self.last_activity_at = datetime.utcnow()
        self.login_count += 1
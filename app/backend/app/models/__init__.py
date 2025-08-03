"""
Database models for Solana Mafia backend.

Contains SQLAlchemy models that mirror the on-chain state
and provide additional indexing and caching capabilities.
"""

from .base import BaseModel, TimestampMixin
from .player import Player
from .business import Business, BusinessSlot
from .nft import BusinessNFT
from .event import Event
from .earnings import EarningsSchedule, EarningsHistory
from .user import User, UserType
from .referral import (
    ReferralCode, ReferralRelation, ReferralCommission,
    ReferralStats, ReferralConfig
)

__all__ = [
    "BaseModel",
    "TimestampMixin", 
    "Player",
    "Business",
    "BusinessSlot",
    "BusinessNFT",
    "Event",
    "EarningsSchedule",
    "EarningsHistory",
    "User",
    "UserType",
    "ReferralCode",
    "ReferralRelation",
    "ReferralCommission",
    "ReferralStats",
    "ReferralConfig",
]
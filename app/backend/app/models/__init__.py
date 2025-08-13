"""
Database models for Solana Mafia backend.

Contains SQLAlchemy models that mirror the on-chain state
and provide additional indexing and caching capabilities.
"""

from .base import BaseModel, TimestampMixin
from .player import Player
from .business import Business, BusinessSlot
from .event import Event
from .earnings import EarningsHistory
from .user import User, UserType
from .referral import (
    ReferralCode, ReferralRelation, ReferralCommission,
    ReferralStats, ReferralConfig, ReferralWithdrawal
)
from .prestige import (
    PrestigeLevel, PrestigeAction, PrestigeHistory, PlayerPrestigeStats,
    PrestigeConfig, PrestigeRank, ActionType
)
from .quest import (
    Quest, QuestCategory, PlayerQuestProgress, QuestTemplate, QuestReward,
    QuestType, QuestDifficulty
)

__all__ = [
    "BaseModel",
    "TimestampMixin", 
    "Player",
    "Business",
    "BusinessSlot",
    "Event",
    "EarningsHistory",
    "User",
    "UserType",
    "ReferralCode",
    "ReferralRelation",
    "ReferralCommission",
    "ReferralStats",
    "ReferralConfig",
    "ReferralWithdrawal",
    "PrestigeLevel",
    "PrestigeAction", 
    "PrestigeHistory",
    "PlayerPrestigeStats",
    "PrestigeConfig",
    "PrestigeRank",
    "ActionType",
    "Quest",
    "QuestCategory",
    "PlayerQuestProgress",
    "QuestTemplate",
    "QuestReward",
    "QuestType",
    "QuestDifficulty",
]
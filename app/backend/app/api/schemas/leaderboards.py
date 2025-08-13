"""
Leaderboard schemas for the Solana Mafia API.
Handles leaderboard data structures and responses.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum

from .common import APIResponse, SuccessResponse, WalletField, LamportsField


class LeaderboardType(str, Enum):
    """Types of leaderboards available."""
    EARNINGS = "earnings"
    REFERRALS = "referrals" 
    PRESTIGE = "prestige"
    COMBINED = "combined"


class LeaderboardPeriod(str, Enum):
    """Time periods for leaderboards."""
    ALL_TIME = "all"
    MONTHLY = "monthly"
    WEEKLY = "weekly"
    DAILY = "daily"


class BaseLeaderboardEntry(BaseModel):
    """Base leaderboard entry with common fields."""
    rank: int = Field(description="Player's rank in leaderboard")
    wallet: str = WalletField
    display_name: Optional[str] = Field(None, description="Player display name (if available)")
    
    # Prestige info for context
    prestige_level: str = Field(default="wannabe", description="Current prestige level")
    prestige_points: int = Field(default=0, description="Current prestige points")


class EarningsLeaderboardEntry(BaseLeaderboardEntry):
    """Earnings leaderboard entry."""
    total_earned: int = LamportsField
    total_invested: int = LamportsField
    roi_percentage: float = Field(description="Return on investment percentage")
    active_businesses: int = Field(description="Number of active businesses")
    
    # Recent earnings data
    last_claim_amount: Optional[int] = Field(None, description="Last claim amount in lamports")
    last_claim_at: Optional[datetime] = Field(None, description="Last claim timestamp")


class ReferralLeaderboardEntry(BaseLeaderboardEntry):
    """Referral leaderboard entry."""
    total_referrals: int = Field(description="Total number of referrals")
    total_referral_earnings: int = LamportsField
    
    # Level breakdown
    level_1_referrals: int = Field(description="Direct referrals")
    level_2_referrals: int = Field(description="Second-level referrals")
    level_3_referrals: int = Field(description="Third-level referrals")
    
    # Earnings breakdown
    level_1_earnings: int = Field(default=0, description="Earnings from level 1 referrals")
    level_2_earnings: int = Field(default=0, description="Earnings from level 2 referrals")
    level_3_earnings: int = Field(default=0, description="Earnings from level 3 referrals")


class PrestigeLeaderboardEntry(BaseLeaderboardEntry):
    """Prestige leaderboard entry."""
    current_points: int = Field(description="Current prestige points")
    total_points_earned: int = Field(description="Total points earned (including spent)")
    current_level: str = Field(description="Current prestige level")
    level_up_count: int = Field(description="Number of times leveled up")
    
    # Progress to next level
    points_to_next_level: Optional[int] = Field(None, description="Points needed for next level")
    progress_percentage: float = Field(description="Progress to next level as percentage")
    
    # Achievement info
    achievements_unlocked: int = Field(default=0, description="Number of achievements unlocked")


class CombinedLeaderboardEntry(BaseLeaderboardEntry):
    """Combined leaderboard entry with all stats."""
    # Score calculation
    combined_score: float = Field(description="Combined weighted score")
    
    # Individual metrics
    earnings_rank: Optional[int] = Field(None, description="Rank in earnings leaderboard")
    referrals_rank: Optional[int] = Field(None, description="Rank in referrals leaderboard")
    prestige_rank: Optional[int] = Field(None, description="Rank in prestige leaderboard")
    
    # Key stats
    total_earned: int = LamportsField
    total_referrals: int = Field(description="Total number of referrals")
    prestige_current_points: int = Field(description="Current prestige points")


class PlayerPosition(BaseModel):
    """Player's position across all leaderboards."""
    wallet: str = WalletField
    
    # Positions in each leaderboard
    earnings_rank: Optional[int] = Field(None, description="Position in earnings leaderboard")
    referrals_rank: Optional[int] = Field(None, description="Position in referrals leaderboard")
    prestige_rank: Optional[int] = Field(None, description="Position in prestige leaderboard")
    combined_rank: Optional[int] = Field(None, description="Position in combined leaderboard")
    
    # Total players in each leaderboard
    total_players_earnings: int = Field(description="Total players in earnings leaderboard")
    total_players_referrals: int = Field(description="Total players in referrals leaderboard")
    total_players_prestige: int = Field(description="Total players in prestige leaderboard")
    
    # Percentile rankings
    earnings_percentile: Optional[float] = Field(None, description="Percentile in earnings (0-100)")
    referrals_percentile: Optional[float] = Field(None, description="Percentile in referrals (0-100)")
    prestige_percentile: Optional[float] = Field(None, description="Percentile in prestige (0-100)")


class LeaderboardStats(BaseModel):
    """Overall leaderboard statistics."""
    total_players: int = Field(description="Total number of players")
    total_earnings: int = LamportsField
    total_referrals: int = Field(description="Total referrals across all players")
    average_prestige_points: float = Field(description="Average prestige points")
    
    # Top performers
    top_earner_wallet: Optional[str] = None
    top_earner_amount: Optional[int] = None
    top_referrer_wallet: Optional[str] = None
    top_referrer_count: Optional[int] = None
    top_prestige_wallet: Optional[str] = None
    top_prestige_points: Optional[int] = None


# Response schemas
class EarningsLeaderboardResponse(SuccessResponse):
    """Earnings leaderboard response."""
    data: Dict[str, Any] = Field(
        description="Leaderboard data",
        example={
            "leaderboard": [],
            "period": "all",
            "total_entries": 0,
            "stats": {},
            "last_updated": "2024-01-01T00:00:00Z"
        }
    )


class ReferralLeaderboardResponse(SuccessResponse):
    """Referral leaderboard response."""
    data: Dict[str, Any] = Field(
        description="Referral leaderboard data"
    )


class PrestigeLeaderboardResponse(SuccessResponse):
    """Prestige leaderboard response."""
    data: Dict[str, Any] = Field(
        description="Prestige leaderboard data"
    )


class CombinedLeaderboardResponse(SuccessResponse):
    """Combined leaderboard response."""
    data: Dict[str, Any] = Field(
        description="Combined leaderboard data"
    )


class PlayerPositionResponse(SuccessResponse):
    """Player position response."""
    data: PlayerPosition


class LeaderboardStatsResponse(SuccessResponse):
    """Leaderboard statistics response."""
    data: LeaderboardStats


# Request schemas
class LeaderboardRequest(BaseModel):
    """Base leaderboard request parameters."""
    limit: int = Field(default=100, ge=1, le=1000, description="Number of entries to return")
    offset: int = Field(default=0, ge=0, description="Number of entries to skip")
    period: LeaderboardPeriod = Field(default=LeaderboardPeriod.ALL_TIME, description="Time period")


class CombinedLeaderboardRequest(LeaderboardRequest):
    """Combined leaderboard request with weights."""
    earnings_weight: float = Field(default=0.4, ge=0, le=1, description="Weight for earnings score")
    referrals_weight: float = Field(default=0.3, ge=0, le=1, description="Weight for referrals score")
    prestige_weight: float = Field(default=0.3, ge=0, le=1, description="Weight for prestige score")
    
    def __init__(self, **data):
        super().__init__(**data)
        # Normalize weights to sum to 1.0
        total_weight = self.earnings_weight + self.referrals_weight + self.prestige_weight
        if total_weight > 0:
            self.earnings_weight /= total_weight
            self.referrals_weight /= total_weight
            self.prestige_weight /= total_weight
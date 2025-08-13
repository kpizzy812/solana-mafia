"""
Player-related Pydantic schemas for API.
Defines data structures for player endpoints.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator
from uuid import UUID

from .common import (
    APIResponse, 
    WalletField, 
    LamportsField,
    SuccessResponse,
    BusinessType
)

import structlog


logger = structlog.get_logger(__name__)


class PlayerBase(BaseModel):
    """Base player model."""
    wallet: str = WalletField
    referrer: Optional[str] = Field(default=None, description="Referrer wallet address")
    unlocked_slots_count: int = Field(ge=1, le=30, description="Number of unlocked business slots")


class PlayerCreate(PlayerBase):
    """Player creation request model."""
    pass


class PlayerResponse(BaseModel):
    """Player response model."""
    wallet: str
    total_invested: int = LamportsField
    total_earned: int = LamportsField
    pending_earnings: int = LamportsField
    is_active: bool = True
    next_earnings_time: Optional[datetime] = None
    last_earnings_update: Optional[datetime] = None
    earnings_interval: int = Field(default=86400, description="Earnings interval in seconds")
    unlocked_slots_count: int = Field(ge=1, le=50, description="Number of unlocked business slots")
    premium_slots_count: int = Field(ge=0, le=10, description="Number of premium slots")
    active_businesses_count: int = Field(ge=0, description="Number of active businesses")
    
    # Prestige fields
    prestige_points: int = Field(default=0, description="Current prestige points")
    prestige_level: str = Field(default="wannabe", description="Current prestige level")
    total_prestige_earned: int = Field(default=0, description="Total prestige points earned")
    points_to_next_level: int = Field(default=0, description="Points needed to reach next level")
    prestige_progress_percentage: int = Field(default=0, description="Progress to next level as percentage")
    
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class PlayerStatsResponse(BaseModel):
    """Player statistics response model."""
    wallet: str = WalletField
    total_businesses: int = Field(ge=0, description="Total number of businesses owned")
    active_businesses: int = Field(ge=0, description="Number of active businesses")
    total_earnings: int = LamportsField
    earnings_balance: int = LamportsField
    total_claimed: int = LamportsField
    business_types_owned: List[BusinessType] = Field(default_factory=list)
    slot_utilization: float = Field(ge=0.0, le=1.0, description="Slot utilization ratio")
    days_active: int = Field(ge=0, description="Number of days since account creation")
    last_activity: Optional[datetime] = None
    
    # Prestige statistics
    prestige_points: int = Field(default=0, description="Current prestige points")
    prestige_level: str = Field(default="wannabe", description="Current prestige level")
    total_prestige_earned: int = Field(default=0, description="Total prestige points earned")
    prestige_level_up_count: int = Field(default=0, description="Number of prestige level ups")
    points_to_next_level: int = Field(default=0, description="Points needed to reach next level")
    prestige_progress_percentage: int = Field(default=0, description="Progress to next level as percentage")


class PlayerBusinessSummary(BaseModel):
    """Player business summary."""
    business_id: str
    business_type: BusinessType
    name: str
    level: int = Field(ge=0, le=10, description="Business upgrade level (0-3, matches contract)")
    base_cost: int = LamportsField
    initial_cost: int = LamportsField  # Same as base_cost for compatibility
    total_invested: int = LamportsField
    earnings_per_hour: int = LamportsField
    slot_index: int = Field(ge=0, le=29)
    is_active: bool
    # Убрано nft_mint поле - NFT больше не используются
    created_at: datetime


class PlayerBusinessesResponse(BaseModel):
    """Player businesses response model."""
    wallet: str = WalletField
    businesses: List[PlayerBusinessSummary]
    total_businesses: int = Field(ge=0)
    active_businesses: int = Field(ge=0)
    total_hourly_earnings: int = LamportsField


class PlayerEarningsPeriod(BaseModel):
    """Player earnings for a specific period."""
    date: datetime
    earnings_amount: int = LamportsField
    cumulative_earnings: int = LamportsField


class PlayerEarningsHistory(BaseModel):
    """Player earnings history response."""
    wallet: str = WalletField
    period: str = Field(description="Period type: daily, weekly, monthly")
    earnings_data: List[PlayerEarningsPeriod]
    total_period_earnings: int = LamportsField
    average_daily_earnings: int = LamportsField


class PlayerLeaderboardEntry(BaseModel):
    """Player leaderboard entry."""
    rank: int = Field(ge=1)
    wallet: str = WalletField
    total_earnings: int = LamportsField
    total_businesses: int = Field(ge=0)
    days_active: int = Field(ge=0)


class PlayerLeaderboardResponse(BaseModel):
    """Player leaderboard response."""
    leaderboard_type: str = Field(description="Type: earnings, businesses, longevity")
    entries: List[PlayerLeaderboardEntry]
    user_rank: Optional[int] = Field(default=None, description="Current user's rank")
    total_players: int = Field(ge=0)


class PlayerActivityLog(BaseModel):
    """Player activity log entry."""
    timestamp: datetime
    activity_type: str = Field(description="Type of activity")
    description: str
    transaction_signature: Optional[str] = None
    metadata: Optional[dict] = None


class PlayerActivityResponse(BaseModel):
    """Player activity response."""
    wallet: str = WalletField
    activities: List[PlayerActivityLog]
    total_activities: int = Field(ge=0)


# Validation functions
@field_validator('wallet', 'referrer')
def validate_wallet_address(cls, v):
    """Validate Solana wallet address format."""
    if v is None:
        return v
    
    if not (32 <= len(v) <= 44):
        raise ValueError("Wallet address must be between 32 and 44 characters")
    
    if not v.isalnum():
        raise ValueError("Wallet address must contain only alphanumeric characters")
    
    return v


# Connect wallet schemas
class ConnectWalletRequest(BaseModel):
    """Request schema for wallet connection."""
    wallet: str = WalletField


class ConnectWalletResponse(BaseModel):
    """Response schema for wallet connection."""
    user_id: str = Field(description="User identifier")
    wallet: str = WalletField
    referral_code: str = Field(description="User's referral code")
    is_new_user: bool = Field(description="Whether this is a new user")
    

# Add validator to schemas
PlayerBase.model_validate = validate_wallet_address
PlayerResponse.model_validate = validate_wallet_address
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
    slots_unlocked: int = Field(ge=1, le=30, description="Number of unlocked business slots")


class PlayerCreate(PlayerBase):
    """Player creation request model."""
    pass


class PlayerResponse(PlayerBase):
    """Player response model."""
    total_earnings: int = LamportsField
    earnings_balance: int = LamportsField
    last_earnings_update: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool = True
    
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


class PlayerBusinessSummary(BaseModel):
    """Player business summary."""
    business_id: str
    business_type: BusinessType
    name: str
    level: int = Field(ge=1, le=10)
    earnings_per_hour: int = LamportsField
    slot_index: int = Field(ge=0, le=29)
    is_active: bool
    nft_mint: str = Field(description="NFT mint address")
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


# Add validator to schemas
PlayerBase.model_validate = validate_wallet_address
PlayerResponse.model_validate = validate_wallet_address
"""
Earnings-related Pydantic schemas for API.
Defines data structures for earnings endpoints.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

from .common import (
    APIResponse,
    WalletField,
    LamportsField,
    SuccessResponse
)

import structlog


logger = structlog.get_logger(__name__)


class EarningsBase(BaseModel):
    """Base earnings model."""
    wallet: str = WalletField
    earnings_amount: int = LamportsField
    total_earnings: int = LamportsField


class EarningsUpdate(EarningsBase):
    """Earnings update model."""
    last_update: datetime
    next_update_time: Optional[datetime] = None


class EarningsResponse(EarningsBase):
    """Earnings response model."""
    earnings_balance: int = LamportsField
    last_earnings_update: datetime
    next_scheduled_update: Optional[datetime] = None
    hourly_rate: int = LamportsField
    
    class Config:
        from_attributes = True


class EarningsClaim(BaseModel):
    """Earnings claim request model."""
    amount: Optional[int] = Field(default=None, description="Amount to claim (default: all available)")


class EarningsClaimResponse(BaseModel):
    """Earnings claim response model."""
    wallet: str = WalletField
    amount_claimed: int = LamportsField
    treasury_fee: int = LamportsField
    net_amount: int = LamportsField
    remaining_balance: int = LamportsField
    transaction_signature: Optional[str] = None


class EarningsHistory(BaseModel):
    """Earnings history entry."""
    timestamp: datetime
    event_type: str = Field(description="Type: update, claim")
    amount: int = LamportsField
    balance_before: int = LamportsField
    balance_after: int = LamportsField
    transaction_signature: Optional[str] = None
    business_count: int = Field(ge=0, description="Number of businesses at the time")


class EarningsHistoryResponse(BaseModel):
    """Earnings history response model."""
    wallet: str = WalletField
    history: List[EarningsHistory]
    total_events: int = Field(ge=0)
    period_start: datetime
    period_end: datetime
    total_earned: int = LamportsField
    total_claimed: int = LamportsField


class EarningsSchedule(BaseModel):
    """Earnings schedule information."""
    wallet: str = WalletField
    next_update_time: datetime
    update_interval: int = Field(ge=1, description="Update interval in seconds")
    is_active: bool
    last_update: Optional[datetime] = None
    update_count: int = Field(ge=0)


class EarningsScheduleResponse(BaseModel):
    """Earnings schedule response model."""
    schedules: List[EarningsSchedule]
    total_active_schedules: int = Field(ge=0)
    next_batch_update: Optional[datetime] = None


class EarningsProjection(BaseModel):
    """Earnings projection model."""
    period: str = Field(description="Period: 1h, 6h, 1d, 1w, 1m")
    projected_earnings: int = LamportsField
    confidence: float = Field(ge=0.0, le=1.0, description="Projection confidence")


class EarningsProjectionResponse(BaseModel):
    """Earnings projection response model."""
    wallet: str = WalletField
    current_hourly_rate: int = LamportsField
    projections: List[EarningsProjection]
    based_on_businesses: int = Field(ge=0)
    last_calculated: datetime


class EarningsComparison(BaseModel):
    """Earnings comparison with other players."""
    wallet: str = WalletField
    player_earnings: int = LamportsField
    average_earnings: int = LamportsField
    median_earnings: int = LamportsField
    percentile: float = Field(ge=0.0, le=100.0)
    rank: int = Field(ge=1)
    total_players: int = Field(ge=1)


class EarningsLeaderboard(BaseModel):
    """Earnings leaderboard entry."""
    rank: int = Field(ge=1)
    wallet: str = WalletField
    total_earnings: int = LamportsField
    hourly_rate: int = LamportsField
    business_count: int = Field(ge=0)
    days_active: int = Field(ge=0)


class EarningsLeaderboardResponse(BaseModel):
    """Earnings leaderboard response model."""
    period: str = Field(description="Period: daily, weekly, monthly, all_time")
    entries: List[EarningsLeaderboard]
    user_entry: Optional[EarningsLeaderboard] = None
    total_players: int = Field(ge=1)
    last_updated: datetime


class EarningsStatistics(BaseModel):
    """Global earnings statistics."""
    total_earnings_distributed: int = LamportsField
    total_earnings_claimed: int = LamportsField
    total_treasury_fees: int = LamportsField
    active_earners: int = Field(ge=0)
    average_hourly_rate: int = LamportsField
    median_hourly_rate: int = LamportsField
    top_earner_hourly_rate: int = LamportsField


class EarningsStatisticsResponse(BaseModel):
    """Earnings statistics response model."""
    statistics: EarningsStatistics
    last_24h: EarningsStatistics
    last_7d: EarningsStatistics
    last_30d: EarningsStatistics
    calculated_at: datetime


class TreasuryInfo(BaseModel):
    """Treasury information."""
    total_balance: int = LamportsField
    total_fees_collected: int = LamportsField
    fee_percentage: float = Field(ge=0.0, le=1.0)
    total_distributed: int = LamportsField
    pending_claims: int = LamportsField


class TreasuryInfoResponse(BaseModel):
    """Treasury information response model."""
    treasury: TreasuryInfo
    last_updated: datetime


# Response wrappers
class EarningsResponseWrapper(SuccessResponse):
    """Earnings response wrapper."""
    data: EarningsResponse


class EarningsClaimResponseWrapper(SuccessResponse):
    """Earnings claim response wrapper."""
    data: EarningsClaimResponse


class EarningsHistoryResponseWrapper(SuccessResponse):
    """Earnings history response wrapper."""
    data: EarningsHistoryResponse


class EarningsProjectionResponseWrapper(SuccessResponse):
    """Earnings projection response wrapper."""
    data: EarningsProjectionResponse
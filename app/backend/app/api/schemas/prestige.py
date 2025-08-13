"""
Pydantic schemas for prestige-related API endpoints.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict


class PrestigeLevelInfo(BaseModel):
    """Prestige level information."""
    model_config = ConfigDict(from_attributes=True)
    
    rank: str = Field(..., description="Level rank identifier")
    display_name_en: str = Field(..., description="Display name in English")
    display_name_ru: str = Field(..., description="Display name in Russian")
    description_en: str = Field(..., description="Description in English")
    description_ru: str = Field(..., description="Description in Russian")
    min_points: int = Field(..., description="Minimum points for this level")
    max_points: Optional[int] = Field(None, description="Maximum points for this level")
    order_rank: int = Field(..., description="Numeric order for sorting")
    icon: Optional[str] = Field(None, description="Icon identifier")
    color: Optional[str] = Field(None, description="Color theme")
    bonus_multiplier: Decimal = Field(Decimal("1.0000"), description="Bonus multiplier")
    referral_bonus: Decimal = Field(Decimal("0.0000"), description="Referral bonus percentage")


class PrestigeProgress(BaseModel):
    """Progress information for next prestige level."""
    
    points_to_next: int = Field(..., description="Points needed for next level")
    progress_percentage: int = Field(..., description="Progress percentage (0-100)")
    next_level_name: Optional[str] = Field(None, description="Name of next level")


class PrestigeStats(BaseModel):
    """Prestige statistics for a player."""
    
    total_earned: int = Field(..., description="Total prestige points earned")
    level_up_count: int = Field(..., description="Number of level ups")
    daily_points: int = Field(0, description="Points earned today")
    last_update: Optional[datetime] = Field(None, description="Last prestige update")
    
    # Breakdown by source
    points_from_business: int = Field(0, description="Points from business activities")
    points_from_referrals: int = Field(0, description="Points from referral system")
    points_from_activity: int = Field(0, description="Points from daily activity")


class PrestigeInfo(BaseModel):
    """Complete prestige information for a player."""
    
    wallet: str = Field(..., description="Player wallet address")
    current_points: int = Field(..., description="Current prestige points")
    current_level: str = Field(..., description="Current prestige level")
    level_info: PrestigeLevelInfo = Field(..., description="Current level details")
    progress: PrestigeProgress = Field(..., description="Progress to next level")
    stats: PrestigeStats = Field(..., description="Prestige statistics")


class PrestigeHistoryEntry(BaseModel):
    """Single prestige history entry."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="History entry ID")
    action_type: str = Field(..., description="Type of action")
    points_awarded: int = Field(..., description="Points awarded")
    points_before: int = Field(..., description="Points before action")
    points_after: int = Field(..., description="Points after action")
    level_before: Optional[str] = Field(None, description="Level before action")
    level_after: Optional[str] = Field(None, description="Level after action")
    level_up: bool = Field(False, description="Whether action caused level up")
    action_value: Optional[int] = Field(None, description="Value of the action")
    business_type: Optional[int] = Field(None, description="Business type involved")
    business_level: Optional[int] = Field(None, description="Business level involved")
    slot_index: Optional[int] = Field(None, description="Slot index involved")
    related_transaction: Optional[str] = Field(None, description="Related transaction")
    calculation_method: str = Field(..., description="Calculation method used")
    multiplier_applied: Decimal = Field(..., description="Multiplier applied")
    action_metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    created_at: datetime = Field(..., description="When points were awarded")


class PrestigeHistoryResponse(BaseModel):
    """Response for prestige history."""
    
    wallet: str = Field(..., description="Player wallet")
    total_entries: int = Field(..., description="Total history entries")
    entries: List[PrestigeHistoryEntry] = Field(..., description="History entries")


class PrestigeLeaderboardEntry(BaseModel):
    """Leaderboard entry for prestige rankings."""
    
    rank: int = Field(..., description="Leaderboard rank")
    wallet: str = Field(..., description="Player wallet")
    points: int = Field(..., description="Prestige points")
    level: str = Field(..., description="Prestige level")
    level_display: str = Field(..., description="Display name for level")


class PrestigeLeaderboardResponse(BaseModel):
    """Response for prestige leaderboard."""
    
    period: str = Field(..., description="Leaderboard period (all, weekly, monthly)")
    total_players: int = Field(..., description="Total players with prestige")
    entries: List[PrestigeLeaderboardEntry] = Field(..., description="Leaderboard entries")


class PrestigeActionResponse(BaseModel):
    """Response for prestige action award."""
    
    success: bool = Field(..., description="Whether action was successful")
    points_awarded: int = Field(0, description="Points awarded")
    level_up_occurred: bool = Field(False, description="Whether level up occurred")
    new_total_points: int = Field(..., description="New total points")
    new_level: str = Field(..., description="New prestige level")
    message: str = Field(..., description="Result message")


class PrestigeRecalculateResponse(BaseModel):
    """Response for prestige recalculation."""
    
    wallet: str = Field(..., description="Player wallet")
    total_points: int = Field(..., description="Total points after recalculation")
    level: str = Field(..., description="Level after recalculation")
    level_changed: bool = Field(..., description="Whether level changed")
    breakdown: Dict[str, int] = Field(..., description="Points breakdown by source")


class PrestigeLevelsResponse(BaseModel):
    """Response for all prestige levels."""
    
    levels: List[PrestigeLevelInfo] = Field(..., description="All prestige levels")


class PrestigeSystemStatus(BaseModel):
    """Overall prestige system status."""
    
    is_enabled: bool = Field(..., description="Whether prestige system is enabled")
    total_players_with_prestige: int = Field(..., description="Players with prestige points")
    average_points: float = Field(..., description="Average prestige points")
    level_distribution: Dict[str, int] = Field(..., description="Players per level")
    top_level_players: int = Field(..., description="Number of Boss level players")
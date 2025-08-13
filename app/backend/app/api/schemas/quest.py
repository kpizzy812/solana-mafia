"""
Pydantic schemas for quest-related API endpoints.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


class QuestTypeEnum(str, Enum):
    """Quest types enumeration for API."""
    SOCIAL_FOLLOW = "social_follow"
    BUSINESS_PURCHASE = "business_purchase"
    BUSINESS_UPGRADE = "business_upgrade"
    REFERRAL_INVITE = "referral_invite"
    DAILY_LOGIN = "daily_login"
    FIXED_TASK = "fixed_task"
    EARNINGS_CLAIM = "earnings_claim"
    PROFILE_COMPLETE = "profile_complete"


class QuestDifficultyEnum(str, Enum):
    """Quest difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    LEGENDARY = "legendary"


class QuestCategoryInfo(BaseModel):
    """Quest category information."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Category ID")
    name_en: str = Field(..., description="Category name in English")
    name_ru: str = Field(..., description="Category name in Russian")
    description_en: Optional[str] = Field(None, description="Description in English")
    description_ru: Optional[str] = Field(None, description="Description in Russian")
    icon: Optional[str] = Field(None, description="Icon identifier")
    color: Optional[str] = Field(None, description="Color theme")
    order_priority: int = Field(0, description="Display order priority")
    is_active: bool = Field(True, description="Whether category is active")


class QuestInfo(BaseModel):
    """Basic quest information."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Quest ID")
    category_id: Optional[int] = Field(None, description="Category ID")
    quest_type: QuestTypeEnum = Field(..., description="Quest type")
    difficulty: QuestDifficultyEnum = Field(QuestDifficultyEnum.EASY, description="Quest difficulty")
    title_en: str = Field(..., description="Quest title in English")
    title_ru: str = Field(..., description="Quest title in Russian")
    description_en: str = Field(..., description="Quest description in English")
    description_ru: str = Field(..., description="Quest description in Russian")
    target_value: int = Field(1, description="Target value to complete quest")
    current_target: Optional[int] = Field(None, description="Current target for progressive quests")
    max_target: Optional[int] = Field(None, description="Maximum target for progressive quests")
    prestige_reward: int = Field(0, description="Prestige points reward")
    bonus_reward: Optional[int] = Field(None, description="Bonus reward (SOL in lamports)")
    is_repeatable: bool = Field(False, description="Whether quest can be repeated")
    is_progressive: bool = Field(False, description="Whether quest progresses")
    is_daily: bool = Field(False, description="Whether quest resets daily")
    is_featured: bool = Field(False, description="Whether quest is featured")
    cooldown_hours: Optional[int] = Field(None, description="Cooldown between completions")
    expires_at: Optional[datetime] = Field(None, description="Quest expiration time")
    min_level: int = Field(1, description="Minimum player level required")
    required_quests: Optional[List[int]] = Field(None, description="Required quest IDs")
    social_links: Optional[Dict[str, str]] = Field(None, description="Social media links")
    order_priority: int = Field(0, description="Display order priority")
    is_active: bool = Field(True, description="Whether quest is active")


class PlayerQuestProgressInfo(BaseModel):
    """Player quest progress information."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Progress ID")
    player_wallet: str = Field(..., description="Player wallet address")
    quest_id: int = Field(..., description="Quest ID")
    current_progress: int = Field(0, description="Current progress value")
    target_value: int = Field(..., description="Target value")
    is_completed: bool = Field(False, description="Whether quest is completed")
    is_claimed: bool = Field(False, description="Whether reward has been claimed")
    started_at: datetime = Field(..., description="When quest was started")
    completed_at: Optional[datetime] = Field(None, description="When quest was completed")
    claimed_at: Optional[datetime] = Field(None, description="When reward was claimed")
    prestige_points_rewarded: int = Field(0, description="Prestige points rewarded")
    bonus_reward_given: Optional[int] = Field(None, description="Bonus reward given")
    progress_percentage: float = Field(..., description="Progress percentage (0-100)")
    is_ready_to_claim: bool = Field(..., description="Whether ready to claim")


class QuestWithProgress(BaseModel):
    """Quest information with player progress."""
    
    quest: QuestInfo = Field(..., description="Quest information")
    progress: Optional[PlayerQuestProgressInfo] = Field(None, description="Player progress (if started)")
    category: Optional[QuestCategoryInfo] = Field(None, description="Quest category")


class QuestListResponse(BaseModel):
    """Response for quest list."""
    
    quests: List[QuestWithProgress] = Field(..., description="List of quests with progress")
    categories: List[QuestCategoryInfo] = Field(..., description="Available categories")
    total_quests: int = Field(..., description="Total number of quests")
    completed_count: int = Field(0, description="Number of completed quests")
    claimed_count: int = Field(0, description="Number of claimed quests")
    available_to_claim: int = Field(0, description="Number of quests ready to claim")


class PlayerQuestStatsResponse(BaseModel):
    """Player quest statistics."""
    
    player_wallet: str = Field(..., description="Player wallet address")
    total_quests_started: int = Field(0, description="Total quests started")
    total_quests_completed: int = Field(0, description="Total quests completed")
    total_quests_claimed: int = Field(0, description="Total quests claimed")
    total_prestige_earned: int = Field(0, description="Total prestige points earned from quests")
    total_bonus_earned: int = Field(0, description="Total bonus rewards earned")
    quests_ready_to_claim: int = Field(0, description="Quests ready to claim")
    current_streak: int = Field(0, description="Current daily quest streak")
    last_quest_completed: Optional[datetime] = Field(None, description="Last quest completion time")


class QuestClaimRequest(BaseModel):
    """Request to claim quest reward."""
    
    player_wallet: str = Field(..., description="Player wallet address")


class QuestClaimResponse(BaseModel):
    """Response for quest claim."""
    
    success: bool = Field(..., description="Whether claim was successful")
    quest_id: int = Field(..., description="Quest ID")
    prestige_points_awarded: int = Field(0, description="Prestige points awarded")
    bonus_reward_awarded: Optional[int] = Field(None, description="Bonus reward awarded")
    new_total_prestige: int = Field(..., description="Player's new total prestige")
    message: str = Field(..., description="Result message")
    next_quest_unlocked: Optional[QuestInfo] = Field(None, description="Next quest unlocked")


class QuestProgressUpdateRequest(BaseModel):
    """Request to update quest progress."""
    
    player_wallet: str = Field(..., description="Player wallet address")
    quest_type: Optional[QuestTypeEnum] = Field(None, description="Quest type to update")
    progress_value: Optional[int] = Field(None, description="New progress value")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class QuestProgressUpdateResponse(BaseModel):
    """Response for quest progress update."""
    
    success: bool = Field(..., description="Whether update was successful")
    updated_quests: List[PlayerQuestProgressInfo] = Field(..., description="Updated quest progress")
    newly_completed: List[QuestInfo] = Field(..., description="Newly completed quests")
    message: str = Field(..., description="Result message")


class QuestStartRequest(BaseModel):
    """Request to start a quest."""
    
    player_wallet: str = Field(..., description="Player wallet address")
    quest_id: int = Field(..., description="Quest ID to start")


class QuestStartResponse(BaseModel):
    """Response for quest start."""
    
    success: bool = Field(..., description="Whether quest was started successfully")
    quest_progress: PlayerQuestProgressInfo = Field(..., description="Quest progress information")
    message: str = Field(..., description="Result message")


class QuestRewardInfo(BaseModel):
    """Quest reward information."""
    
    reward_type: str = Field(..., description="Type of reward")
    reward_value: int = Field(..., description="Reward value")
    reward_data: Optional[Dict[str, Any]] = Field(None, description="Additional reward data")
    condition_type: Optional[str] = Field(None, description="Condition type")
    condition_value: Optional[str] = Field(None, description="Condition value")


class QuestDetailedInfo(BaseModel):
    """Detailed quest information with all related data."""
    
    quest: QuestInfo = Field(..., description="Basic quest information")
    category: Optional[QuestCategoryInfo] = Field(None, description="Quest category")
    rewards: List[QuestRewardInfo] = Field(..., description="Additional rewards")
    required_quests_info: List[QuestInfo] = Field(..., description="Information about required quests")
    completion_stats: Dict[str, Any] = Field(..., description="Completion statistics")


class QuestSystemStatusResponse(BaseModel):
    """Overall quest system status."""
    
    total_active_quests: int = Field(..., description="Total active quests")
    total_categories: int = Field(..., description="Total categories")
    total_players_with_quests: int = Field(..., description="Players who started quests")
    most_popular_quest: Optional[QuestInfo] = Field(None, description="Most popular quest")
    completion_rates: Dict[str, float] = Field(..., description="Completion rates by quest type")
    average_completion_time: Dict[str, float] = Field(..., description="Average completion time by quest type")


class QuestLeaderboardEntry(BaseModel):
    """Leaderboard entry for quest completion."""
    
    rank: int = Field(..., description="Leaderboard rank")
    player_wallet: str = Field(..., description="Player wallet")
    total_completed: int = Field(..., description="Total quests completed")
    total_prestige_earned: int = Field(..., description="Total prestige earned from quests")
    completion_percentage: float = Field(..., description="Completion percentage")


class QuestLeaderboardResponse(BaseModel):
    """Response for quest leaderboard."""
    
    period: str = Field(..., description="Leaderboard period")
    total_players: int = Field(..., description="Total players on leaderboard")
    entries: List[QuestLeaderboardEntry] = Field(..., description="Leaderboard entries")


class QuestTemplateInfo(BaseModel):
    """Quest template information."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    quest_type: QuestTypeEnum = Field(..., description="Quest type")
    template_data: Dict[str, Any] = Field(..., description="Template configuration")
    is_active: bool = Field(True, description="Whether template is active")


class CreateQuestFromTemplateRequest(BaseModel):
    """Request to create quest from template."""
    
    template_id: int = Field(..., description="Template ID")
    overrides: Optional[Dict[str, Any]] = Field(None, description="Template data overrides")


class QuestBulkOperationRequest(BaseModel):
    """Request for bulk quest operations."""
    
    quest_ids: List[int] = Field(..., description="List of quest IDs")
    operation: str = Field(..., description="Operation type (activate, deactivate, delete)")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Operation parameters")


class QuestBulkOperationResponse(BaseModel):
    """Response for bulk quest operations."""
    
    success: bool = Field(..., description="Whether operation was successful")
    processed_count: int = Field(..., description="Number of quests processed")
    failed_count: int = Field(0, description="Number of failed operations")
    errors: List[str] = Field(..., description="List of errors")
    message: str = Field(..., description="Result message")


class QuestValidationResponse(BaseModel):
    """Response for quest validation."""
    
    is_valid: bool = Field(..., description="Whether quest configuration is valid")
    errors: List[str] = Field(..., description="Validation errors")
    warnings: List[str] = Field(..., description="Validation warnings")
    suggestions: List[str] = Field(..., description="Improvement suggestions")


class DailyQuestResponse(BaseModel):
    """Response for daily quests."""
    
    daily_quests: List[QuestWithProgress] = Field(..., description="Daily quests")
    streak_count: int = Field(0, description="Current daily streak")
    last_completion: Optional[datetime] = Field(None, description="Last daily quest completion")
    next_reset: datetime = Field(..., description="Next daily reset time")
    bonus_multiplier: float = Field(1.0, description="Streak bonus multiplier")
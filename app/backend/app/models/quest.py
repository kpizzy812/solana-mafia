"""
Quest system models for tracking player quests and rewards.
Implements quest mechanics with prestige point rewards for various game activities.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    String, Integer, BigInteger, Boolean, DECIMAL, Text, Index, 
    ForeignKey, DateTime, JSON, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, TimestampMixin


class QuestType(Enum):
    """Types of quests available in the game."""
    SOCIAL_FOLLOW = "social_follow"           # Subscribe to social media
    BUSINESS_PURCHASE = "business_purchase"   # Purchase a business
    BUSINESS_UPGRADE = "business_upgrade"     # Upgrade a business
    REFERRAL_INVITE = "referral_invite"       # Invite friends (progressive)
    DAILY_LOGIN = "daily_login"               # Daily login bonus
    FIXED_TASK = "fixed_task"                # Fixed task completion
    EARNINGS_CLAIM = "earnings_claim"         # Claim earnings
    PROFILE_COMPLETE = "profile_complete"     # Complete profile setup


class QuestDifficulty(Enum):
    """Quest difficulty levels."""
    EASY = "easy"
    MEDIUM = "medium" 
    HARD = "hard"
    LEGENDARY = "legendary"


class QuestCategory(BaseModel, TimestampMixin):
    """Categories for grouping quests."""
    
    __tablename__ = "quest_categories"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Category details
    name_en: Mapped[str] = mapped_column(
        String(100),
        comment="Category name in English"
    )
    
    name_ru: Mapped[str] = mapped_column(
        String(100),
        comment="Category name in Russian"
    )
    
    description_en: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Category description in English"
    )
    
    description_ru: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Category description in Russian"
    )
    
    # Visual elements
    icon: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Icon identifier for UI"
    )
    
    color: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Color theme for this category"
    )
    
    # Ordering
    order_priority: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Order priority for displaying categories"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether this category is active"
    )
    
    # Relationships
    quests: Mapped[List["Quest"]] = relationship(
        "Quest",
        back_populates="category"
    )
    
    def __repr__(self) -> str:
        return f"<QuestCategory(id={self.id}, name={self.name_en})>"


class Quest(BaseModel, TimestampMixin):
    """Quest definitions with requirements and rewards."""
    
    __tablename__ = "quests"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Category reference
    category_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("quest_categories.id", ondelete="SET NULL"),
        comment="Quest category ID"
    )
    
    # Quest details
    quest_type: Mapped[QuestType] = mapped_column(
        String(30),
        comment="Type of quest"
    )
    
    difficulty: Mapped[QuestDifficulty] = mapped_column(
        String(20),
        default="easy",
        comment="Quest difficulty level"
    )
    
    title_en: Mapped[str] = mapped_column(
        String(200),
        comment="Quest title in English"
    )
    
    title_ru: Mapped[str] = mapped_column(
        String(200),
        comment="Quest title in Russian"
    )
    
    description_en: Mapped[str] = mapped_column(
        Text,
        comment="Quest description in English"
    )
    
    description_ru: Mapped[str] = mapped_column(
        Text,
        comment="Quest description in Russian"
    )
    
    # Quest mechanics
    target_value: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Target value to complete quest (e.g., number of referrals)"
    )
    
    current_target: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Current target for progressive quests"
    )
    
    max_target: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Maximum target for progressive quests"
    )
    
    # Rewards
    prestige_reward: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Prestige points awarded upon completion"
    )
    
    bonus_reward: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Additional bonus reward (SOL in lamports)"
    )
    
    # Quest behavior
    is_repeatable: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether quest can be repeated"
    )
    
    is_progressive: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether quest progresses (like referral goals)"
    )
    
    is_daily: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether quest resets daily"
    )
    
    # Timing
    cooldown_hours: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Cooldown between completions (for repeatable quests)"
    )
    
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="Quest expiration time"
    )
    
    # Requirements
    min_level: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Minimum player level required"
    )
    
    required_quests: Mapped[Optional[List[int]]] = mapped_column(
        JSON,
        comment="List of quest IDs that must be completed first"
    )
    
    # Metadata
    quest_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        comment="Additional quest-specific metadata"
    )
    
    # Social media links for social quests
    social_links: Mapped[Optional[Dict[str, str]]] = mapped_column(
        JSON,
        comment="Social media links for verification"
    )
    
    # Ordering and visibility
    order_priority: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Order priority for displaying quests"
    )
    
    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether quest is featured"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether quest is active"
    )
    
    # Relationships
    category: Mapped[Optional["QuestCategory"]] = relationship(
        "QuestCategory",
        back_populates="quests"
    )
    
    player_progress: Mapped[List["PlayerQuestProgress"]] = relationship(
        "PlayerQuestProgress",
        back_populates="quest",
        cascade="all, delete-orphan"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_quest_type", "quest_type"),
        Index("idx_quest_active", "is_active", "order_priority"),
        Index("idx_quest_category", "category_id", "is_active"),
        Index("idx_quest_difficulty", "difficulty"),
        Index("idx_quest_featured", "is_featured", "order_priority"),
    )
    
    def __repr__(self) -> str:
        return f"<Quest(id={self.id}, type={self.quest_type.value}, title={self.title_en})>"
    
    @property
    def title(self) -> str:
        """Get default title (English)."""
        return self.title_en
    
    @property
    def description(self) -> str:
        """Get default description (English)."""
        return self.description_en
    
    def get_next_target(self) -> Optional[int]:
        """Get next target value for progressive quests."""
        if not self.is_progressive:
            return None
        
        if self.quest_type == QuestType.REFERRAL_INVITE:
            # Progressive referral targets: 1, 5, 10, 25, 50, 100, 250, 500
            current = self.current_target or 1
            if current >= 500:
                return None
            
            progression = [1, 5, 10, 25, 50, 100, 250, 500]
            for target in progression:
                if target > current:
                    return target
            return None
        
        return None
    
    def is_completable_by_player(self, player_level: int, completed_quest_ids: List[int]) -> bool:
        """Check if quest can be completed by player."""
        # Check level requirement
        if player_level < self.min_level:
            return False
        
        # Check required quests
        if self.required_quests:
            for required_id in self.required_quests:
                if required_id not in completed_quest_ids:
                    return False
        
        # Check if quest is active
        if not self.is_active:
            return False
        
        # Check if quest has expired
        if self.expires_at and self.expires_at < datetime.utcnow():
            return False
        
        return True


class PlayerQuestProgress(BaseModel, TimestampMixin):
    """Player progress tracking for quests."""
    
    __tablename__ = "player_quest_progress"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Player reference
    player_wallet: Mapped[str] = mapped_column(
        String(44),
        ForeignKey("players.wallet", ondelete="CASCADE"),
        comment="Player wallet address"
    )
    
    # Quest reference
    quest_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("quests.id", ondelete="CASCADE"),
        comment="Quest ID"
    )
    
    # Progress tracking
    current_progress: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Current progress value"
    )
    
    target_value: Mapped[int] = mapped_column(
        Integer,
        comment="Target value when quest was started"
    )
    
    # Status tracking
    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether quest is completed"
    )
    
    is_claimed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether reward has been claimed"
    )
    
    # Timing
    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        comment="When quest was started"
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="When quest was completed"
    )
    
    claimed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="When reward was claimed"
    )
    
    last_progress_update: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="Last time progress was updated"
    )
    
    # Rewards given
    prestige_points_rewarded: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Prestige points actually rewarded"
    )
    
    bonus_reward_given: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Bonus reward actually given"
    )
    
    # Metadata
    progress_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        comment="Additional progress-specific metadata"
    )
    
    # Relationships
    player: Mapped["Player"] = relationship(
        "Player",
        foreign_keys=[player_wallet]
    )
    
    quest: Mapped["Quest"] = relationship(
        "Quest",
        back_populates="player_progress"
    )
    
    # Indexes and constraints
    __table_args__ = (
        UniqueConstraint("player_wallet", "quest_id", name="uq_player_quest"),
        Index("idx_player_quest_progress_player", "player_wallet"),
        Index("idx_player_quest_progress_quest", "quest_id"),
        Index("idx_player_quest_progress_status", "is_completed", "is_claimed"),
        Index("idx_player_quest_progress_timing", "completed_at", "claimed_at"),
    )
    
    def __repr__(self) -> str:
        return f"<PlayerQuestProgress(player={self.player_wallet}, quest={self.quest_id}, progress={self.current_progress}/{self.target_value})>"
    
    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.target_value <= 0:
            return 100.0 if self.is_completed else 0.0
        return min(100.0, (self.current_progress / self.target_value) * 100)
    
    @property
    def is_ready_to_claim(self) -> bool:
        """Check if quest is ready to claim."""
        return self.is_completed and not self.is_claimed
    
    def update_progress(self, new_progress: int) -> bool:
        """Update progress and check if quest is completed."""
        self.current_progress = new_progress
        self.last_progress_update = datetime.utcnow()
        
        if not self.is_completed and self.current_progress >= self.target_value:
            self.is_completed = True
            self.completed_at = datetime.utcnow()
            return True  # Quest just completed
        
        return False
    
    def claim_reward(self, prestige_points: int, bonus_reward: Optional[int] = None) -> None:
        """Mark quest as claimed and record rewards."""
        if not self.is_completed:
            raise ValueError("Cannot claim reward for incomplete quest")
        
        if self.is_claimed:
            raise ValueError("Quest reward already claimed")
        
        self.is_claimed = True
        self.claimed_at = datetime.utcnow()
        self.prestige_points_rewarded = prestige_points
        if bonus_reward:
            self.bonus_reward_given = bonus_reward


class QuestTemplate(BaseModel, TimestampMixin):
    """Templates for creating quest instances."""
    
    __tablename__ = "quest_templates"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Template details
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        comment="Template name"
    )
    
    quest_type: Mapped[QuestType] = mapped_column(
        String(30),
        comment="Type of quest this template creates"
    )
    
    # Template data
    template_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        comment="Template configuration data"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether template is active"
    )
    
    def __repr__(self) -> str:
        return f"<QuestTemplate(id={self.id}, name={self.name}, type={self.quest_type.value})>"


class QuestReward(BaseModel, TimestampMixin):
    """Additional rewards configuration for quests."""
    
    __tablename__ = "quest_rewards"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Quest reference
    quest_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("quests.id", ondelete="CASCADE"),
        comment="Quest ID"
    )
    
    # Reward details
    reward_type: Mapped[str] = mapped_column(
        String(50),
        comment="Type of reward (prestige, sol, nft, etc.)"
    )
    
    reward_value: Mapped[int] = mapped_column(
        Integer,
        comment="Reward value"
    )
    
    reward_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        comment="Additional reward data"
    )
    
    # Conditions
    condition_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Condition type for this reward"
    )
    
    condition_value: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Condition value"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether reward is active"
    )
    
    def __repr__(self) -> str:
        return f"<QuestReward(quest_id={self.quest_id}, type={self.reward_type}, value={self.reward_value})>"
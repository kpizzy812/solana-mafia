"""
Prestige system models for tracking player prestige points and levels.
Implements mafia-themed ranking system with point rewards for game actions.
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


class PrestigeRank(Enum):
    """Mafia-themed prestige ranks."""
    WANNABE = "wannabe"          # 0-49 pts
    ASSOCIATE = "associate"      # 50-199 pts  
    SOLDIER = "soldier"          # 200-799 pts
    CAPO = "capo"               # 800-2999 pts
    UNDERBOSS = "underboss"     # 3000-9999 pts
    BOSS = "boss"               # 10000+ pts


class ActionType(Enum):
    """Types of actions that award prestige points."""
    
    # Player actions
    PLAYER_REGISTRATION = "player_registration"
    
    # Business actions
    BUSINESS_PURCHASE = "business_purchase"
    BUSINESS_UPGRADE = "business_upgrade"
    BUSINESS_SELL = "business_sell"
    
    # Slot actions  
    PREMIUM_SLOT_PURCHASE = "premium_slot_purchase"
    
    # Earnings actions
    EARNINGS_CLAIM = "earnings_claim"
    
    # Referral actions
    REFERRAL_INVITED = "referral_invited"
    REFERRAL_FIRST_BUSINESS = "referral_first_business"
    REFERRAL_BUSINESS_ACTIVITY = "referral_business_activity"
    REFERRAL_ACTIVITY_BONUS = "referral_activity_bonus"
    REFERRAL_NETWORK_BONUS = "referral_network_bonus"
    
    # Special actions
    DAILY_ACTIVITY = "daily_activity"
    ACHIEVEMENT_UNLOCK = "achievement_unlock"


class PrestigeLevel(BaseModel, TimestampMixin):
    """Prestige level definitions with requirements and rewards."""
    
    __tablename__ = "prestige_levels"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Level details
    rank: Mapped[PrestigeRank] = mapped_column(
        String(20),
        unique=True,
        comment="Prestige rank name"
    )
    
    display_name_en: Mapped[str] = mapped_column(
        String(50),
        comment="Display name in English"
    )
    
    display_name_ru: Mapped[str] = mapped_column(
        String(50),
        comment="Display name in Russian"
    )
    
    description_en: Mapped[str] = mapped_column(
        Text,
        comment="Level description in English"
    )
    
    description_ru: Mapped[str] = mapped_column(
        Text,
        comment="Level description in Russian"
    )
    
    # Requirements
    min_points: Mapped[int] = mapped_column(
        Integer,
        comment="Minimum prestige points required for this level"
    )
    
    max_points: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Maximum points for this level (null = unlimited)"
    )
    
    # Level order for sorting
    order_rank: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        comment="Numeric order for sorting levels"
    )
    
    # Bonuses and rewards
    bonus_multiplier: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4),
        default=Decimal("1.0000"),
        comment="Bonus multiplier for prestige point earning (1.0 = no bonus)"
    )
    
    referral_bonus: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4),
        default=Decimal("0.0000"),
        comment="Additional referral bonus percentage"
    )
    
    # Visual elements
    icon: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Icon identifier for UI"
    )
    
    color: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Color theme for this level"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether this level is active"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_prestige_level_points", "min_points", "max_points"),
        Index("idx_prestige_level_order", "order_rank"),
        Index("idx_prestige_level_active", "is_active", "order_rank"),
    )
    
    def __repr__(self) -> str:
        return f"<PrestigeLevel(rank={self.rank.value}, min={self.min_points}, max={self.max_points})>"
    
    @property
    def display_name(self) -> str:
        """Get default display name (English)."""
        return self.display_name_en
    
    @property
    def description(self) -> str:
        """Get default description (English)."""
        return self.description_en
    
    def is_in_range(self, points: int) -> bool:
        """Check if points fall within this level's range."""
        if points < self.min_points:
            return False
        if self.max_points is not None and points > self.max_points:
            return False
        return True


class PrestigeAction(BaseModel, TimestampMixin):
    """Prestige point calculation rules for different actions."""
    
    __tablename__ = "prestige_actions"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Action details
    action_type: Mapped[ActionType] = mapped_column(
        String(30),
        unique=True,
        comment="Type of action that awards points"
    )
    
    name_en: Mapped[str] = mapped_column(
        String(100),
        comment="Action name in English"
    )
    
    name_ru: Mapped[str] = mapped_column(
        String(100),
        comment="Action name in Russian"
    )
    
    description_en: Mapped[str] = mapped_column(
        Text,
        comment="Action description in English"
    )
    
    description_ru: Mapped[str] = mapped_column(
        Text,
        comment="Action description in Russian"
    )
    
    # Point calculation
    base_points: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Base points awarded (if not percentage-based)"
    )
    
    percentage_of_value: Mapped[Optional[Decimal]] = mapped_column(
        DECIMAL(8, 4),
        comment="Percentage of action value as points (e.g., 1.0000 = 1%)"
    )
    
    # Calculation parameters
    calculation_method: Mapped[str] = mapped_column(
        String(20),
        default="fixed",
        comment="Calculation method: 'fixed', 'percentage', 'formula'"
    )
    
    calculation_formula: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Custom calculation formula (for complex cases)"
    )
    
    # Limits and constraints
    min_points: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Minimum points that can be awarded"
    )
    
    max_points: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Maximum points that can be awarded (null = unlimited)"
    )
    
    # Frequency limits
    max_per_day: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Maximum times this action can award points per day"
    )
    
    cooldown_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Cooldown between point awards for this action"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether this action is active"
    )
    
    # Version for tracking changes
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Version of this action configuration"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_prestige_action_type", "action_type"),
        Index("idx_prestige_action_active", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<PrestigeAction(type={self.action_type.value}, base={self.base_points}, pct={self.percentage_of_value})>"
    
    def calculate_points(
        self, 
        action_value: Optional[int] = None,
        player_level: Optional[int] = None,
        **kwargs
    ) -> int:
        """Calculate prestige points for this action."""
        if not self.is_active:
            return 0
        
        points = 0
        
        if self.calculation_method == "fixed":
            points = self.base_points
            
        elif self.calculation_method == "percentage" and action_value is not None:
            if self.percentage_of_value:
                # Convert lamports to SOL, then calculate percentage
                sol_value = action_value / 1_000_000_000  # lamports to SOL
                points = int(sol_value * float(self.percentage_of_value) * 100)  # × 100 for scaling
            
        elif self.calculation_method == "direct" and action_value is not None:
            # Direct assignment - use action_value as points (for quests and achievements)
            points = action_value
            
        elif self.calculation_method == "formula":
            # Custom formula evaluation (implement as needed)
            points = self._evaluate_formula(action_value, player_level, **kwargs)
        
        # Apply limits
        points = max(points, self.min_points)
        if self.max_points is not None:
            points = min(points, self.max_points)
        
        return points
    
    def _evaluate_formula(self, action_value: Optional[int], player_level: Optional[int], **kwargs) -> int:
        """Evaluate custom formula (placeholder for future complex calculations)."""
        # This can be extended for complex formulas
        return self.base_points


class PrestigeHistory(BaseModel, TimestampMixin):
    """Historical record of prestige point awards."""
    
    __tablename__ = "prestige_history"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Player reference
    player_wallet: Mapped[str] = mapped_column(
        String(44),
        ForeignKey("players.wallet", ondelete="CASCADE"),
        comment="Player wallet address"
    )
    
    # Action details
    action_type: Mapped[ActionType] = mapped_column(
        String(30),
        ForeignKey("prestige_actions.action_type"),
        comment="Type of action that awarded points"
    )
    
    # Points awarded
    points_awarded: Mapped[int] = mapped_column(
        Integer,
        comment="Number of prestige points awarded"
    )
    
    points_before: Mapped[int] = mapped_column(
        Integer,
        comment="Player's points before this action"
    )
    
    points_after: Mapped[int] = mapped_column(
        Integer,
        comment="Player's points after this action"
    )
    
    # Level changes
    level_before: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Player's prestige level before this action"
    )
    
    level_after: Mapped[Optional[str]] = mapped_column(
        String(20),
        comment="Player's prestige level after this action"
    )
    
    level_up: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether this action resulted in a level up"
    )
    
    # Action context
    action_value: Mapped[Optional[int]] = mapped_column(
        BigInteger,
        comment="Value associated with the action (e.g., business cost in lamports)"
    )
    
    business_type: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Business type if action involves business"
    )
    
    business_level: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Business level if action involves business"
    )
    
    slot_index: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Slot index if action involves slots"
    )
    
    # Reference to source transaction/event
    related_transaction: Mapped[Optional[str]] = mapped_column(
        String(88),
        comment="Related blockchain transaction signature"
    )
    
    related_event_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Related event ID that triggered this prestige award"
    )
    
    # Metadata for complex actions
    action_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        comment="Additional metadata for the action"
    )
    
    # Processing info
    calculation_method: Mapped[str] = mapped_column(
        String(20),
        comment="Method used to calculate points"
    )
    
    multiplier_applied: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4),
        default=Decimal("1.0000"),
        comment="Multiplier applied during calculation"
    )
    
    # Relationships
    player: Mapped["Player"] = relationship(
        "Player",
        foreign_keys=[player_wallet]
    )
    
    action: Mapped["PrestigeAction"] = relationship(
        "PrestigeAction",
        foreign_keys=[action_type]
    )
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_prestige_history_player_time", "player_wallet", "created_at"),
        Index("idx_prestige_history_action_type", "action_type", "created_at"),
        Index("idx_prestige_history_level_up", "level_up", "created_at"),
        Index("idx_prestige_history_transaction", "related_transaction"),
        Index("idx_prestige_history_event", "related_event_id"),
    )
    
    def __repr__(self) -> str:
        return f"<PrestigeHistory(player={self.player_wallet}, action={self.action_type.value}, points={self.points_awarded})>"
    
    @classmethod
    def create_award_record(
        cls,
        player_wallet: str,
        action_type: ActionType,
        points_awarded: int,
        points_before: int,
        points_after: int,
        level_before: Optional[str] = None,
        level_after: Optional[str] = None,
        action_value: Optional[int] = None,
        business_type: Optional[int] = None,
        business_level: Optional[int] = None,
        slot_index: Optional[int] = None,
        related_transaction: Optional[str] = None,
        related_event_id: Optional[int] = None,
        calculation_method: str = "fixed",
        multiplier_applied: Decimal = Decimal("1.0000"),
        action_metadata: Optional[Dict[str, Any]] = None
    ) -> "PrestigeHistory":
        """Create a prestige award record."""
        level_up = level_before != level_after and level_after is not None
        
        return cls(
            player_wallet=player_wallet,
            action_type=action_type.value,
            points_awarded=points_awarded,
            points_before=points_before,
            points_after=points_after,
            level_before=level_before,
            level_after=level_after,
            level_up=level_up,
            action_value=action_value,
            business_type=business_type,
            business_level=business_level,
            slot_index=slot_index,
            related_transaction=related_transaction,
            related_event_id=related_event_id,
            calculation_method=calculation_method,
            multiplier_applied=multiplier_applied,
            action_metadata=action_metadata or {}
        )


class PrestigeConfig(BaseModel, TimestampMixin):
    """Configuration for the prestige system."""
    
    __tablename__ = "prestige_config"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # System settings
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether prestige system is enabled"
    )
    
    # Point calculation settings
    sol_to_points_multiplier: Mapped[int] = mapped_column(
        Integer,
        default=100,
        comment="Multiplier for converting SOL to points (100 = 1 SOL = 100 pts)"
    )
    
    # Bonus settings
    daily_activity_bonus: Mapped[int] = mapped_column(
        Integer,
        default=5,
        comment="Daily activity bonus points"
    )
    
    referral_points_percentage: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 4),
        default=Decimal("0.1000"),  # 10%
        comment="Percentage of referee's points awarded to referrer"
    )
    
    level_up_bonus: Mapped[int] = mapped_column(
        Integer,
        default=50,
        comment="Bonus points for leveling up"
    )
    
    # Anti-gaming measures
    min_action_value: Mapped[int] = mapped_column(
        BigInteger,
        default=1000000,  # 0.001 SOL
        comment="Minimum action value to award points"
    )
    
    max_points_per_day: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Maximum points that can be earned per day (null = unlimited)"
    )
    
    # Active period
    active_from: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        comment="When this config becomes active"
    )
    
    active_until: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="When this config expires (null = indefinite)"
    )
    
    # Version for tracking changes
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Configuration version"
    )
    
    def __repr__(self) -> str:
        return f"<PrestigeConfig(version={self.version}, enabled={self.is_enabled})>"
    
    @property
    def is_active(self) -> bool:
        """Check if this configuration is currently active."""
        now = datetime.utcnow()
        return (
            self.is_enabled and
            self.active_from <= now and
            (self.active_until is None or self.active_until > now)
        )


class PlayerPrestigeStats(BaseModel, TimestampMixin):
    """Aggregated prestige statistics for a player."""
    
    __tablename__ = "player_prestige_stats"
    
    # Primary key - player wallet
    player_wallet: Mapped[str] = mapped_column(
        String(44),
        ForeignKey("players.wallet", ondelete="CASCADE"),
        primary_key=True,
        comment="Player wallet address"
    )
    
    # Current status
    current_points: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Current total prestige points"
    )
    
    current_level: Mapped[str] = mapped_column(
        String(20),
        default=PrestigeRank.WANNABE.value,
        comment="Current prestige level"
    )
    
    # Historical tracking
    total_points_earned: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Total points earned (including spent/lost)"
    )
    
    points_from_business: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Points earned from business actions"
    )
    
    points_from_referrals: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Points earned from referral system"
    )
    
    points_from_activity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Points earned from daily activity"
    )
    
    # Level progression
    highest_level_reached: Mapped[str] = mapped_column(
        String(20),
        default=PrestigeRank.WANNABE.value,
        comment="Highest level ever reached"
    )
    
    level_up_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of times player leveled up"
    )
    
    last_level_up_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="When player last leveled up"
    )
    
    # Activity tracking
    last_points_awarded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="When points were last awarded"
    )
    
    daily_points_today: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Points earned today (resets daily)"
    )
    
    last_daily_reset: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="Last time daily counters were reset"
    )
    
    # Calculated fields
    points_to_next_level: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Points needed to reach next level"
    )
    
    progress_percentage: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 2),
        default=Decimal("0.00"),
        comment="Progress to next level as percentage"
    )
    
    # Relationships
    player: Mapped["Player"] = relationship(
        "Player",
        foreign_keys=[player_wallet]
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_player_prestige_stats_level", "current_level"),
        Index("idx_player_prestige_stats_points", "current_points"),
        Index("idx_player_prestige_daily", "last_daily_reset", "daily_points_today"),
    )
    
    def __repr__(self) -> str:
        return f"<PlayerPrestigeStats(player={self.player_wallet}, level={self.current_level}, points={self.current_points})>"
    
    def reset_daily_counters(self) -> None:
        """Reset daily counters."""
        self.daily_points_today = 0
        self.last_daily_reset = datetime.utcnow()
    
    def add_points(
        self, 
        points: int, 
        source: str = "business",
        level_after: Optional[str] = None
    ) -> bool:
        """Add points and return True if leveled up."""
        level_before = self.current_level
        
        self.current_points += points
        self.total_points_earned += points
        self.daily_points_today += points
        
        # Update source tracking
        if source == "business":
            self.points_from_business += points
        elif source == "referrals":
            self.points_from_referrals += points
        elif source == "activity":
            self.points_from_activity += points
        
        # Update level if provided
        if level_after and level_after != level_before:
            self.current_level = level_after
            self.level_up_count += 1
            self.last_level_up_at = datetime.utcnow()
            
            # Update highest level
            # (This should be done by comparing order_rank, simplified here)
            self.highest_level_reached = level_after
            
            return True
        
        self.last_points_awarded_at = datetime.utcnow()
        return False
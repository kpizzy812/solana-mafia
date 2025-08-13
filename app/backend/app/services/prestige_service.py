"""
Prestige system service for calculating and awarding prestige points.
Handles all prestige-related logic including point calculation, level progression, and history tracking.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, desc, func
from sqlalchemy.orm import selectinload

import structlog

from app.models.player import Player
from app.models.business import Business, BusinessType
from app.models.prestige import (
    PrestigeLevel, PrestigeAction, PrestigeHistory, PlayerPrestigeStats,
    PrestigeConfig, PrestigeRank, ActionType
)
from app.models.referral import ReferralRelation, ReferralStats
from app.core.exceptions import ValidationError, NotFoundError

logger = structlog.get_logger(__name__)


class PrestigeService:
    """Service for managing the prestige system."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logger.bind(service="prestige_service")
    
    # ============================================================================
    # INITIALIZATION AND SETUP
    # ============================================================================
    
    async def initialize_system(self) -> None:
        """Initialize the prestige system with default data."""
        await self._create_default_levels()
        await self._create_default_actions()
        await self._create_default_config()
        
        self.logger.info("Prestige system initialized")
    
    async def _create_default_levels(self) -> None:
        """Create default prestige levels."""
        levels_data = [
            {
                "rank": PrestigeRank.WANNABE.value,
                "display_name_en": "Wannabe",
                "display_name_ru": "Хочу быть",
                "description_en": "Just getting started in the mafia world",
                "description_ru": "Только начинаешь путь в мире мафии",
                "min_points": 0,
                "max_points": 49,
                "order_rank": 1,
                "icon": "wannabe",
                "color": "#64748b"
            },
            {
                "rank": PrestigeRank.ASSOCIATE.value,
                "display_name_en": "Associate",
                "display_name_ru": "Партнер", 
                "description_en": "Trusted partner with proven loyalty",
                "description_ru": "Надежный партнер с проверенной лояльностью",
                "min_points": 50,
                "max_points": 199,
                "order_rank": 2,
                "bonus_multiplier": Decimal("1.0500"),  # +5% points
                "icon": "associate",
                "color": "#22c55e"
            },
            {
                "rank": PrestigeRank.SOLDIER.value,
                "display_name_en": "Soldier", 
                "display_name_ru": "Солдат",
                "description_en": "Experienced soldier who follows orders",
                "description_ru": "Опытный солдат, выполняющий приказы",
                "min_points": 200,
                "max_points": 799,
                "order_rank": 3,
                "bonus_multiplier": Decimal("1.1000"),  # +10% points
                "referral_bonus": Decimal("0.0100"),   # +1% referral bonus
                "icon": "soldier",
                "color": "#3b82f6"
            },
            {
                "rank": PrestigeRank.CAPO.value,
                "display_name_en": "Capo",
                "display_name_ru": "Капо",
                "description_en": "Captain who commands respect and soldiers",
                "description_ru": "Капитан, командующий уважением и солдатами",
                "min_points": 800,
                "max_points": 2999,
                "order_rank": 4,
                "bonus_multiplier": Decimal("1.1500"),  # +15% points
                "referral_bonus": Decimal("0.0200"),   # +2% referral bonus
                "icon": "capo",
                "color": "#f59e0b"
            },
            {
                "rank": PrestigeRank.UNDERBOSS.value,
                "display_name_en": "Underboss",
                "display_name_ru": "Заместитель",
                "description_en": "Second in command with significant power",
                "description_ru": "Заместитель с серьезной властью",
                "min_points": 3000,
                "max_points": 9999,
                "order_rank": 5,
                "bonus_multiplier": Decimal("1.2000"),  # +20% points
                "referral_bonus": Decimal("0.0300"),   # +3% referral bonus
                "icon": "underboss",
                "color": "#8b5cf6"
            },
            {
                "rank": PrestigeRank.BOSS.value,
                "display_name_en": "Boss",
                "display_name_ru": "Босс",
                "description_en": "The ultimate leader of the organization",
                "description_ru": "Верховный лидер организации",
                "min_points": 10000,
                "max_points": None,
                "order_rank": 6,
                "bonus_multiplier": Decimal("1.2500"),  # +25% points
                "referral_bonus": Decimal("0.0500"),   # +5% referral bonus
                "icon": "boss",
                "color": "#ef4444"
            }
        ]
        
        for level_data in levels_data:
            # Check if level already exists
            result = await self.db.execute(
                select(PrestigeLevel).where(PrestigeLevel.rank == level_data["rank"])
            )
            if not result.scalar_one_or_none():
                level = PrestigeLevel(**level_data)
                self.db.add(level)
        
        await self.db.flush()
    
    async def _create_default_actions(self) -> None:
        """Create default prestige actions."""
        actions_data = [
            {
                "action_type": ActionType.PLAYER_REGISTRATION.value,
                "name_en": "Player Registration",
                "name_ru": "Регистрация игрока",
                "description_en": "Welcome bonus for joining the mafia",
                "description_ru": "Приветственный бонус за вступление в мафию",
                "base_points": 10,
                "calculation_method": "fixed"
            },
            {
                "action_type": ActionType.BUSINESS_PURCHASE.value,
                "name_en": "Business Purchase", 
                "name_ru": "Покупка бизнеса",
                "description_en": "Points for investing in businesses (1% of SOL value)",
                "description_ru": "Поинты за инвестиции в бизнес (1% от стоимости в SOL)",
                "base_points": 0,
                "percentage_of_value": Decimal("1.0000"),  # 1% of SOL value
                "calculation_method": "percentage",
                "min_points": 1
            },
            {
                "action_type": ActionType.BUSINESS_UPGRADE.value,
                "name_en": "Business Upgrade",
                "name_ru": "Улучшение бизнеса", 
                "description_en": "Points for upgrading businesses (50% of upgrade cost)",
                "description_ru": "Поинты за улучшение бизнеса (50% от стоимости)",
                "base_points": 0,
                "percentage_of_value": Decimal("0.5000"),  # 50% of upgrade cost
                "calculation_method": "percentage",
                "min_points": 1
            },
            {
                "action_type": ActionType.PREMIUM_SLOT_PURCHASE.value,
                "name_en": "Premium Slot Purchase",
                "name_ru": "Покупка премиум слота",
                "description_en": "Points for buying premium slots (25% of cost)",
                "description_ru": "Поинты за покупку премиум слотов (25% от стоимости)",
                "base_points": 0,
                "percentage_of_value": Decimal("0.2500"),  # 25% of slot cost
                "calculation_method": "percentage",
                "min_points": 5
            },
            {
                "action_type": ActionType.EARNINGS_CLAIM.value,
                "name_en": "Earnings Claim",
                "name_ru": "Получение доходов",
                "description_en": "Points for claiming earnings (0.1 pt per 0.001 SOL)",
                "description_ru": "Поинты за получение доходов (0.1 pt за 0.001 SOL)",
                "base_points": 0,
                "percentage_of_value": Decimal("0.0100"),  # 0.01% of claimed amount
                "calculation_method": "percentage",
                "min_points": 0,
                "max_points": 100  # Cap at 100 pts per claim
            },
            {
                "action_type": ActionType.REFERRAL_INVITED.value,
                "name_en": "Referral Invited",
                "name_ru": "Приглашение реферала",
                "description_en": "Points for successfully inviting a new player",
                "description_ru": "Поинты за успешное приглашение нового игрока",
                "base_points": 25,
                "calculation_method": "fixed"
            },
            {
                "action_type": ActionType.REFERRAL_FIRST_BUSINESS.value,
                "name_en": "Referral First Business",
                "name_ru": "Первый бизнес реферала",
                "description_en": "Bonus when your referral buys their first business",
                "description_ru": "Бонус когда ваш реферал покупает первый бизнес",
                "base_points": 25,
                "calculation_method": "fixed"
            },
            {
                "action_type": ActionType.REFERRAL_BUSINESS_ACTIVITY.value,
                "name_en": "Referral Business Activity",
                "name_ru": "Активность рефералов в бизнесах",
                "description_en": "Points for all referral business purchases and upgrades (5% of business value)",
                "description_ru": "Поинты за все покупки и улучшения бизнесов рефералов (5% от стоимости)",
                "base_points": 0,
                "percentage_of_value": Decimal("0.0500"),  # 5% of business action value
                "calculation_method": "percentage",
                "min_points": 1,
                "max_points": 200  # Cap referral business bonuses
            },
            {
                "action_type": ActionType.REFERRAL_NETWORK_BONUS.value,
                "name_en": "Referral Network Bonus",
                "name_ru": "Бонус реферальной сети",
                "description_en": "Points for active referral network (10% of referee points)",
                "description_ru": "Поинты за активную реферальную сеть (10% от поинтов реферала)",
                "base_points": 0,
                "percentage_of_value": Decimal("0.1000"),  # 10% of referee's points
                "calculation_method": "percentage",
                "min_points": 1,
                "max_points": 500  # Cap referral bonuses
            },
            {
                "action_type": ActionType.DAILY_ACTIVITY.value,
                "name_en": "Daily Activity",
                "name_ru": "Ежедневная активность",
                "description_en": "Daily bonus for being active",
                "description_ru": "Ежедневный бонус за активность",
                "base_points": 5,
                "calculation_method": "fixed",
                "max_per_day": 1
            },
            {
                "action_type": ActionType.ACHIEVEMENT_UNLOCK.value,
                "name_en": "Achievement Unlock",
                "name_ru": "Достижение разблокировано",
                "description_en": "Reward for unlocking achievements and completing quests",
                "description_ru": "Награда за разблокировку достижений и выполнение заданий",
                "base_points": 0,
                "calculation_method": "direct",
                "is_active": True
            }
        ]
        
        for action_data in actions_data:
            # Check if action already exists
            result = await self.db.execute(
                select(PrestigeAction).where(
                    PrestigeAction.action_type == action_data["action_type"]
                )
            )
            if not result.scalar_one_or_none():
                action = PrestigeAction(**action_data)
                self.db.add(action)
        
        await self.db.flush()
    
    async def _create_default_config(self) -> None:
        """Create default prestige configuration."""
        # Check if config exists
        result = await self.db.execute(
            select(PrestigeConfig).where(PrestigeConfig.is_enabled == True)
        )
        if result.scalar_one_or_none():
            return
        
        config = PrestigeConfig(
            is_enabled=True,
            sol_to_points_multiplier=100,  # 1 SOL = 100 base points
            daily_activity_bonus=5,
            referral_points_percentage=Decimal("0.1000"),  # 10%
            level_up_bonus=50,
            min_action_value=1000000,  # 0.001 SOL minimum
            max_points_per_day=1000    # Daily cap of 1000 points
        )
        
        self.db.add(config)
        await self.db.flush()
    
    # ============================================================================
    # POINT CALCULATION AND AWARDING
    # ============================================================================
    
    async def calculate_and_award_points(
        self,
        player_wallet: str,
        action_type: ActionType,
        action_value: Optional[int] = None,
        business_type: Optional[int] = None,
        business_level: Optional[int] = None,
        slot_index: Optional[int] = None,
        related_transaction: Optional[str] = None,
        related_event_id: Optional[int] = None,
        action_metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[int, bool]:
        """Calculate and award prestige points for an action.
        
        Returns:
            Tuple of (points_awarded, level_up_occurred)
        """
        self.logger.debug(f"PRESTIGE START: calculate_and_award_points called with action_type={action_type}, action_value={action_value}")
        
        # Get player
        player = await self._get_player(player_wallet)
        if not player:
            self.logger.warning("Player not found for prestige award", wallet=player_wallet)
            return (0, False)
        
        # Get action configuration
        action_config = await self._get_action_config(action_type)
        if not action_config or not action_config.is_active:
            self.logger.debug("Action not configured or inactive", action_type=action_type.value)
            return (0, False)
        
        # Check daily limits
        if not await self._check_daily_limits(player_wallet, action_type, action_config):
            self.logger.debug("Daily limit reached", wallet=player_wallet, action_type=action_type.value)
            return (0, False)
        
        # Calculate base points
        base_points = action_config.calculate_points(
            action_value=action_value,
            player_level=self._get_player_level_order(player.prestige_level)
        )
        
        if base_points <= 0:
            return (0, False)
        
        # Apply player level multiplier
        config = await self._get_current_config()
        level_multiplier = await self._get_level_multiplier(player.prestige_level)
        final_points = int(base_points * float(level_multiplier))
        
        # Apply daily cap
        if config.max_points_per_day:
            daily_points = await self._get_daily_points(player_wallet)
            remaining_daily = config.max_points_per_day - daily_points
            final_points = min(final_points, remaining_daily)
        
        if final_points <= 0:
            return (0, False)
        
        # Record current state
        points_before = player.prestige_points
        level_before = player.prestige_level
        
        # Award points to player
        level_up = player.add_prestige_points(final_points)
        await self.db.flush()
        
        # Create history record
        history = PrestigeHistory.create_award_record(
            player_wallet=player_wallet,
            action_type=action_type,
            points_awarded=final_points,
            points_before=points_before,
            points_after=player.prestige_points,
            level_before=level_before,
            level_after=player.prestige_level,
            action_value=action_value,
            business_type=business_type,
            business_level=business_level,
            slot_index=slot_index,
            related_transaction=related_transaction,
            related_event_id=related_event_id,
            calculation_method=action_config.calculation_method,
            multiplier_applied=level_multiplier,
            action_metadata=action_metadata
        )
        
        self.db.add(history)
        
        # Update player prestige stats
        await self._update_player_prestige_stats(player_wallet, final_points, level_up)
        
        self.logger.info(
            "Prestige points awarded",
            wallet=player_wallet,
            action_type=action_type.value,
            points_awarded=final_points,
            total_points=player.prestige_points,
            level_before=level_before,
            level_after=player.prestige_level,
            level_up=level_up
        )
        
        # Send WebSocket notifications
        await self._send_prestige_notifications(
            player_wallet=player_wallet,
            points_awarded=final_points,
            total_points=player.prestige_points,
            current_level=player.prestige_level,
            level_before=level_before,
            level_up=level_up,
            action_type=action_type,
            action_metadata=action_metadata
        )
        
        # If level up occurred, award level up bonus
        if level_up and config.level_up_bonus > 0:
            await self._award_level_up_bonus(player_wallet, config.level_up_bonus)
        
        await self.db.flush()
        return (final_points, level_up)
    
    # ============================================================================
    # SPECIFIC ACTION HANDLERS
    # ============================================================================
    
    async def award_business_purchase_points(
        self,
        player_wallet: str,
        business_cost: int,
        business_type: int,
        slot_index: int,
        transaction_signature: Optional[str] = None
    ) -> Tuple[int, bool]:
        """Award points for business purchase."""
        return await self.calculate_and_award_points(
            player_wallet=player_wallet,
            action_type=ActionType.BUSINESS_PURCHASE,
            action_value=business_cost,
            business_type=business_type,
            slot_index=slot_index,
            related_transaction=transaction_signature
        )
    
    async def award_business_upgrade_points(
        self,
        player_wallet: str,
        upgrade_cost: int,
        business_type: int,
        new_level: int,
        slot_index: int,
        transaction_signature: Optional[str] = None
    ) -> Tuple[int, bool]:
        """Award points for business upgrade."""
        return await self.calculate_and_award_points(
            player_wallet=player_wallet,
            action_type=ActionType.BUSINESS_UPGRADE,
            action_value=upgrade_cost,
            business_type=business_type,
            business_level=new_level,
            slot_index=slot_index,
            related_transaction=transaction_signature
        )
    
    async def award_referral_points(
        self,
        referrer_wallet: str,
        referee_wallet: str,
        referee_points: int,
        referral_type: str = "network_bonus"
    ) -> Tuple[int, bool]:
        """Award points for referral activities."""
        action_type = ActionType.REFERRAL_NETWORK_BONUS
        
        if referral_type == "invited":
            action_type = ActionType.REFERRAL_INVITED
            referee_points = None  # Fixed bonus, not percentage
        elif referral_type == "first_business":
            action_type = ActionType.REFERRAL_FIRST_BUSINESS
            referee_points = None  # Fixed bonus
        
        return await self.calculate_and_award_points(
            player_wallet=referrer_wallet,
            action_type=action_type,
            action_value=referee_points,
            action_metadata={"referee_wallet": referee_wallet, "referral_type": referral_type}
        )
    
    # ============================================================================
    # BULK OPERATIONS AND RECALCULATION
    # ============================================================================
    
    async def recalculate_player_prestige(self, player_wallet: str) -> Dict[str, Any]:
        """Recalculate prestige for a player based on all their activities."""
        player = await self._get_player(player_wallet)
        if not player:
            raise NotFoundError(f"Player {player_wallet} not found")
        
        total_points = 0
        breakdown = {
            "registration": 10,  # Base registration bonus
            "businesses": 0,
            "upgrades": 0,
            "slots": 0,
            "earnings_claims": 0,
            "referrals": 0
        }
        
        # Points from business purchases
        businesses = await self.db.execute(
            select(Business).where(
                and_(
                    Business.player_wallet == player_wallet,
                    Business.is_active == True
                )
            )
        )
        for business in businesses.scalars():
            # 1% of business cost as points
            sol_value = business.base_cost / 1_000_000_000
            business_points = int(sol_value * 100)  # 1 SOL = 100 points
            breakdown["businesses"] += business_points
            
            # Upgrade points (50% of upgrade costs)
            if business.level > 0:
                # Estimate upgrade costs (simplified)
                upgrade_cost_estimate = business.base_cost * business.level * 0.2  # Rough estimate
                sol_upgrade = upgrade_cost_estimate / 1_000_000_000
                upgrade_points = int(sol_upgrade * 50)  # 50% as points
                breakdown["upgrades"] += upgrade_points
        
        # Premium slots only (regular slots are all unlocked by default now)
        breakdown["slots"] = player.premium_slots_count * 50  # Estimate for premium slots
        
        # Points from earnings claims (simplified)
        claimed_amount = player.total_earned
        if claimed_amount > 0:
            sol_claimed = claimed_amount / 1_000_000_000
            breakdown["earnings_claims"] = int(sol_claimed * 1)  # 0.01% = 1 point per SOL
        
        # Points from referrals (check referral stats)
        referral_result = await self.db.execute(
            select(ReferralStats).where(ReferralStats.user_id == player_wallet)
        )
        referral_stats = referral_result.scalar_one_or_none()
        if referral_stats:
            # 25 points per direct referral + bonuses
            breakdown["referrals"] = referral_stats.level_1_referrals * 25
            breakdown["referrals"] += referral_stats.level_2_referrals * 10
            breakdown["referrals"] += referral_stats.level_3_referrals * 5
        
        # Calculate total
        total_points = sum(breakdown.values())
        
        # Update player
        old_level = player.prestige_level
        player.prestige_points = total_points
        player.total_prestige_earned = total_points
        player.prestige_level = player._calculate_prestige_level()
        player.last_prestige_update = datetime.utcnow()
        
        if player.prestige_level != old_level:
            player.prestige_level_up_count += 1
        
        await self.db.flush()
        
        self.logger.info(
            "Player prestige recalculated",
            wallet=player_wallet,
            total_points=total_points,
            breakdown=breakdown,
            level=player.prestige_level
        )
        
        return {
            "total_points": total_points,
            "level": player.prestige_level,
            "breakdown": breakdown,
            "level_changed": player.prestige_level != old_level
        }
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    async def _get_player(self, wallet: str) -> Optional[Player]:
        """Get player by wallet."""
        result = await self.db.execute(
            select(Player).where(Player.wallet == wallet)
        )
        return result.scalar_one_or_none()
    
    async def _get_action_config(self, action_type: ActionType) -> Optional[PrestigeAction]:
        """Get action configuration."""
        result = await self.db.execute(
            select(PrestigeAction).where(PrestigeAction.action_type == action_type.value)
        )
        return result.scalar_one_or_none()
    
    async def _get_current_config(self) -> PrestigeConfig:
        """Get current prestige configuration."""
        result = await self.db.execute(
            select(PrestigeConfig)
            .where(PrestigeConfig.is_enabled == True)
            .order_by(desc(PrestigeConfig.version))
            .limit(1)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            # Create default config
            config = PrestigeConfig()
            self.db.add(config)
            await self.db.flush()
        
        return config
    
    async def _get_level_multiplier(self, level: str) -> Decimal:
        """Get bonus multiplier for player's level."""
        result = await self.db.execute(
            select(PrestigeLevel.bonus_multiplier).where(PrestigeLevel.rank == level)
        )
        multiplier = result.scalar_one_or_none()
        return multiplier or Decimal("1.0000")
    
    def _get_player_level_order(self, level: str) -> int:
        """Get numeric order of player's level."""
        level_orders = {
            "wannabe": 1,
            "associate": 2,
            "soldier": 3,
            "capo": 4,
            "underboss": 5,
            "boss": 6
        }
        return level_orders.get(level, 1)
    
    async def _check_daily_limits(
        self,
        player_wallet: str,
        action_type: ActionType,
        action_config: PrestigeAction
    ) -> bool:
        """Check if daily limits allow awarding points."""
        if not action_config.max_per_day:
            return True
        
        # Count today's awards for this action
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        result = await self.db.execute(
            select(func.count())
            .select_from(PrestigeHistory)
            .where(
                and_(
                    PrestigeHistory.player_wallet == player_wallet,
                    PrestigeHistory.action_type == action_type.value,
                    PrestigeHistory.created_at >= today_start
                )
            )
        )
        
        today_count = result.scalar() or 0
        return today_count < action_config.max_per_day
    
    async def _get_daily_points(self, player_wallet: str) -> int:
        """Get total points earned today."""
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        result = await self.db.execute(
            select(func.sum(PrestigeHistory.points_awarded))
            .where(
                and_(
                    PrestigeHistory.player_wallet == player_wallet,
                    PrestigeHistory.created_at >= today_start
                )
            )
        )
        
        return result.scalar() or 0
    
    async def _update_player_prestige_stats(
        self,
        player_wallet: str,
        points_awarded: int,
        level_up: bool
    ) -> None:
        """Update aggregated prestige stats for player."""
        # Get or create stats record
        result = await self.db.execute(
            select(PlayerPrestigeStats).where(
                PlayerPrestigeStats.player_wallet == player_wallet
            )
        )
        stats = result.scalar_one_or_none()
        
        if not stats:
            player = await self._get_player(player_wallet)
            stats = PlayerPrestigeStats(
                player_wallet=player_wallet,
                current_points=player.prestige_points,
                current_level=player.prestige_level,
                total_points_earned=player.total_prestige_earned
            )
            self.db.add(stats)
        else:
            # Update existing stats
            stats.current_points = (await self._get_player(player_wallet)).prestige_points
            stats.current_level = (await self._get_player(player_wallet)).prestige_level
            stats.total_points_earned += points_awarded
            stats.last_points_awarded_at = datetime.utcnow()
            
            # Reset daily counter if needed
            if not stats.last_daily_reset or stats.last_daily_reset.date() < datetime.utcnow().date():
                stats.reset_daily_counters()
            
            stats.daily_points_today += points_awarded
            
            if level_up:
                stats.level_up_count += 1
                stats.last_level_up_at = datetime.utcnow()
        
        await self.db.flush()
    
    async def _award_level_up_bonus(self, player_wallet: str, bonus_points: int) -> None:
        """Award bonus points for leveling up."""
        await self.calculate_and_award_points(
            player_wallet=player_wallet,
            action_type=ActionType.ACHIEVEMENT_UNLOCK,
            action_value=bonus_points,
            action_metadata={"type": "level_up_bonus"}
        )
    
    async def _send_prestige_notifications(
        self,
        player_wallet: str,
        points_awarded: int,
        total_points: int,
        current_level: str,
        level_before: str,
        level_up: bool,
        action_type: ActionType,
        action_metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Send WebSocket notifications for prestige changes."""
        try:
            # Import here to avoid circular imports
            from app.websocket.notification_service import NotificationService
            
            # Common notification data
            notification_data = {
                "points_awarded": points_awarded,
                "current_points": total_points,
                "current_level": current_level,
                "source": "quest" if action_type == ActionType.ACHIEVEMENT_UNLOCK else action_type.value,
                "action_type": action_type.value,
                "total_earned": total_points,  # Since we track total earned = current points
            }
            
            # Add metadata if available
            if action_metadata:
                notification_data.update({
                    "quest_id": action_metadata.get("quest_id"),
                    "reason": action_metadata.get("reason", "Points awarded")
                })
            
            if level_up:
                # Send level up notification (special case)
                level_up_data = {
                    **notification_data,
                    "old_level": level_before,
                    "new_level": current_level,
                    "level_up_bonus": 0  # Will be added separately if applicable
                }
                
                await NotificationService.notify_prestige_level_up(player_wallet, level_up_data)
                self.logger.debug("Level up notification sent", wallet=player_wallet, new_level=current_level)
            else:
                # Send regular prestige update notification
                await NotificationService.notify_prestige_updated(player_wallet, notification_data)
                self.logger.debug("Prestige update notification sent", wallet=player_wallet, points=points_awarded)
            
        except Exception as e:
            self.logger.error(
                "Failed to send prestige notifications",
                wallet=player_wallet,
                points_awarded=points_awarded,
                error=str(e)
            )
    
    # ============================================================================
    # QUERY METHODS
    # ============================================================================
    
    async def get_player_prestige_info(self, player_wallet: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive prestige information for a player."""
        player = await self._get_player(player_wallet)
        if not player:
            return None
        
        # Get prestige stats
        result = await self.db.execute(
            select(PlayerPrestigeStats).where(
                PlayerPrestigeStats.player_wallet == player_wallet
            )
        )
        stats = result.scalar_one_or_none()
        
        # Get level info
        level_result = await self.db.execute(
            select(PrestigeLevel).where(PrestigeLevel.rank == player.prestige_level)
        )
        level_info = level_result.scalar_one_or_none()
        
        # Calculate progress to next level
        points_needed, progress_pct = player.prestige_progress_to_next
        
        return {
            "wallet": player_wallet,
            "current_points": player.prestige_points,
            "current_level": player.prestige_level,
            "level_info": {
                "rank": level_info.rank if level_info else player.prestige_level,
                "display_name_en": level_info.display_name_en if level_info else player.prestige_level.title(),
                "display_name_ru": level_info.display_name_ru if level_info else player.prestige_level.title(),
                "description_en": level_info.description_en if level_info else "",
                "description_ru": level_info.description_ru if level_info else "",
                "min_points": level_info.min_points if level_info else 0,
                "max_points": level_info.max_points if level_info else None,
                "order_rank": level_info.order_rank if level_info else 0,
                "icon": level_info.icon if level_info else "default",
                "color": level_info.color if level_info else "#64748b",
                "bonus_multiplier": level_info.bonus_multiplier if level_info else Decimal("1.0000"),
                "referral_bonus": level_info.referral_bonus if level_info else Decimal("0.0000")
            },
            "progress": {
                "points_to_next": points_needed,
                "progress_percentage": progress_pct
            },
            "stats": {
                "total_earned": player.total_prestige_earned,
                "level_up_count": player.prestige_level_up_count,
                "daily_points": stats.daily_points_today if stats else 0,
                "last_update": player.last_prestige_update
            }
        }
    
    async def get_prestige_leaderboard(
        self,
        limit: int = 100,
        period: str = "all"
    ) -> List[Dict[str, Any]]:
        """Get prestige leaderboard."""
        query = select(Player.wallet, Player.prestige_points, Player.prestige_level)
        
        if period == "weekly":
            week_ago = datetime.utcnow() - timedelta(days=7)
            query = query.where(Player.last_prestige_update >= week_ago)
        elif period == "monthly":
            month_ago = datetime.utcnow() - timedelta(days=30)
            query = query.where(Player.last_prestige_update >= month_ago)
        
        query = query.order_by(desc(Player.prestige_points)).limit(limit)
        
        result = await self.db.execute(query)
        players = result.all()
        
        leaderboard = []
        for i, (wallet, points, level) in enumerate(players, 1):
            leaderboard.append({
                "rank": i,
                "wallet": wallet,
                "points": points,
                "level": level,
                "level_display": level.title()
            })
        
        return leaderboard
    
    async def get_prestige_history(
        self,
        player_wallet: str,
        limit: int = 50,
        offset: int = 0,
        action_type: Optional[ActionType] = None
    ) -> List[PrestigeHistory]:
        """Get prestige history for a player."""
        query = select(PrestigeHistory).where(
            PrestigeHistory.player_wallet == player_wallet
        )
        
        if action_type:
            query = query.where(PrestigeHistory.action_type == action_type.value)
        
        query = query.order_by(desc(PrestigeHistory.created_at))
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        return result.scalars().all()


# Singleton service instance getter
_prestige_service_instance = None

async def get_prestige_service(db: AsyncSession) -> PrestigeService:
    """Get prestige service instance."""
    return PrestigeService(db)
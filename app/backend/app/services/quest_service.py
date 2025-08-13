"""
Quest system service for managing player quests and rewards.
Handles quest creation, progress tracking, completion, and reward distribution.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, desc, func, text
from sqlalchemy.orm import selectinload

import structlog

from app.models.player import Player
from app.models.quest import (
    Quest, QuestCategory, PlayerQuestProgress, QuestTemplate, QuestReward,
    QuestType, QuestDifficulty
)
from app.models.prestige import ActionType
from app.services.prestige_service import get_prestige_service
from app.core.exceptions import ValidationError, NotFoundError
from app.core.config import settings

logger = structlog.get_logger(__name__)


class QuestService:
    """Service for managing the quest system."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logger.bind(service="quest_service")
    
    # ============================================================================
    # QUEST MANAGEMENT
    # ============================================================================
    
    async def get_all_quests(
        self,
        category_id: Optional[int] = None,
        quest_type: Optional[QuestType] = None,
        difficulty: Optional[QuestDifficulty] = None,
        is_active: bool = True,
        include_expired: bool = False
    ) -> List[Quest]:
        """Get all quests with optional filtering."""
        query = select(Quest).options(selectinload(Quest.category))
        
        # Apply filters
        filters = []
        if is_active is not None:
            filters.append(Quest.is_active == is_active)
        if category_id:
            filters.append(Quest.category_id == category_id)
        if quest_type:
            filters.append(Quest.quest_type == quest_type.value)
        if difficulty:
            filters.append(Quest.difficulty == difficulty.value)
        
        # Handle expired quests
        if not include_expired:
            filters.append(
                or_(
                    Quest.expires_at.is_(None),
                    Quest.expires_at > datetime.utcnow()
                )
            )
        
        if filters:
            query = query.where(and_(*filters))
        
        query = query.order_by(Quest.order_priority, Quest.id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_quest_by_id(self, quest_id: int) -> Optional[Quest]:
        """Get quest by ID."""
        result = await self.db.execute(
            select(Quest)
            .options(selectinload(Quest.category))
            .where(Quest.id == quest_id)
        )
        return result.scalar_one_or_none()
    
    async def get_quests_for_player(
        self,
        player_wallet: str,
        include_completed: bool = True,
        include_claimed: bool = True
    ) -> List[Dict[str, Any]]:
        """Get quests for a specific player with their progress."""
        # Get all active quests (show all available quests, not just started ones)
        quests = await self.get_all_quests(is_active=True)
        
        # Get player's quest progress
        progress_result = await self.db.execute(
            select(PlayerQuestProgress)
            .where(PlayerQuestProgress.player_wallet == player_wallet)
        )
        progress_map = {p.quest_id: p for p in progress_result.scalars().all()}
        
        # Get completed quest IDs for requirement checking
        completed_quest_ids = [
            quest_id for quest_id, progress in progress_map.items()
            if progress.is_completed
        ]
        
        result = []
        for quest in quests:
            # Check if player can access this quest
            if not quest.is_completable_by_player(
                player_level=1,  # Simplified for now
                completed_quest_ids=completed_quest_ids
            ):
                continue
            
            progress = progress_map.get(quest.id)
            
            # Filter based on completion/claim status (only filter if there IS progress)
            if progress:
                if not include_completed and progress.is_completed and not progress.is_claimed:
                    continue
                if not include_claimed and progress.is_claimed:
                    continue
            
            quest_data = {
                "quest": quest,
                "progress": progress,  # Can be None for new quests
                "category": quest.category
            }
            result.append(quest_data)
        
        return result
    
    # ============================================================================
    # PLAYER QUEST PROGRESS
    # ============================================================================
    
    async def start_quest(self, player_wallet: str, quest_id: int) -> PlayerQuestProgress:
        """Start a quest for a player."""
        # Check if quest exists and is accessible
        quest = await self.get_quest_by_id(quest_id)
        if not quest:
            raise NotFoundError(f"Quest {quest_id} not found")
        
        # Check if player already has progress for this quest
        existing_result = await self.db.execute(
            select(PlayerQuestProgress).where(
                and_(
                    PlayerQuestProgress.player_wallet == player_wallet,
                    PlayerQuestProgress.quest_id == quest_id
                )
            )
        )
        existing_progress = existing_result.scalar_one_or_none()
        
        if existing_progress:
            if existing_progress.is_claimed and quest.is_repeatable:
                # Check cooldown for repeatable quests
                if quest.cooldown_hours:
                    cooldown_end = existing_progress.claimed_at + timedelta(hours=quest.cooldown_hours)
                    if datetime.utcnow() < cooldown_end:
                        raise ValidationError(f"Quest is on cooldown until {cooldown_end}")
                
                # Reset progress for repeatable quest
                existing_progress.current_progress = 0
                existing_progress.is_completed = False
                existing_progress.is_claimed = False
                existing_progress.started_at = datetime.utcnow()
                existing_progress.completed_at = None
                existing_progress.claimed_at = None
                await self.db.flush()
                return existing_progress
            else:
                raise ValidationError("Quest already started and not repeatable")
        
        # Create new progress record
        target_value = quest.current_target or quest.target_value
        progress = PlayerQuestProgress(
            player_wallet=player_wallet,
            quest_id=quest_id,
            current_progress=0,
            target_value=target_value,
            started_at=datetime.utcnow()
        )
        
        self.db.add(progress)
        await self.db.flush()
        
        self.logger.info(
            "Quest started",
            player_wallet=player_wallet,
            quest_id=quest_id,
            quest_type=quest.quest_type
        )
        
        return progress
    
    async def update_quest_progress(
        self,
        player_wallet: str,
        quest_type: QuestType,
        progress_value: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[PlayerQuestProgress]:
        """Update progress for quests of a specific type."""
        # Get active quests of this type that player has started
        result = await self.db.execute(
            select(PlayerQuestProgress)
            .join(Quest)
            .where(
                and_(
                    PlayerQuestProgress.player_wallet == player_wallet,
                    Quest.quest_type == quest_type.value,
                    Quest.is_active == True,
                    PlayerQuestProgress.is_completed == False
                )
            )
        )
        progress_records = result.scalars().all()
        
        updated_records = []
        for progress in progress_records:
            old_progress = progress.current_progress
            progress.update_progress(progress_value)
            
            if metadata:
                progress.progress_metadata = {
                    **(progress.progress_metadata or {}),
                    **metadata
                }
            
            if progress.current_progress != old_progress:
                updated_records.append(progress)
                
                self.logger.info(
                    "Quest progress updated",
                    player_wallet=player_wallet,
                    quest_id=progress.quest_id,
                    old_progress=old_progress,
                    new_progress=progress.current_progress,
                    completed=progress.is_completed
                )
        
        await self.db.flush()
        return updated_records
    
    async def claim_quest_reward(self, player_wallet: str, quest_id: int) -> Dict[str, Any]:
        """Claim reward for a completed quest."""
        # Get quest progress
        result = await self.db.execute(
            select(PlayerQuestProgress)
            .options(selectinload(PlayerQuestProgress.quest))
            .where(
                and_(
                    PlayerQuestProgress.player_wallet == player_wallet,
                    PlayerQuestProgress.quest_id == quest_id
                )
            )
        )
        progress = result.scalar_one_or_none()
        
        if not progress:
            raise NotFoundError("Quest progress not found")
        
        if not progress.is_completed:
            raise ValidationError("Quest is not completed")
        
        if progress.is_claimed:
            raise ValidationError("Quest reward already claimed")
        
        quest = progress.quest
        
        # Award prestige points
        prestige_points = quest.prestige_reward
        
        self.logger.info("BEFORE get_prestige_service", prestige_points=prestige_points)
        
        try:
            prestige_service = await get_prestige_service(self.db)
            self.logger.info("AFTER get_prestige_service SUCCESS")
        except Exception as e:
            self.logger.error("get_prestige_service FAILED", error=str(e))
            # Skip prestige awarding but continue with quest claim
            prestige_service = None
        
        self.logger.info(
            "CRITICAL DEBUG",
            quest_prestige_reward=quest.prestige_reward,
            prestige_points_var=prestige_points,
            prestige_points_type=type(prestige_points).__name__,
            prestige_points_greater_zero=prestige_points > 0,
            prestige_points_is_none=prestige_points is None
        )
        
        if prestige_points > 0:
            self.logger.info(
                "Attempting to award prestige points",
                player_wallet=player_wallet,
                quest_id=quest_id,
                prestige_points=prestige_points
            )
            try:
                await prestige_service.calculate_and_award_points(
                    player_wallet=player_wallet,
                    action_type=ActionType.ACHIEVEMENT_UNLOCK,
                    action_value=prestige_points,
                    action_metadata={
                        "quest_id": quest_id,
                        "quest_type": quest.quest_type,
                        "quest_title": quest.title_en
                    }
                )
                self.logger.info(
                    "Prestige points awarded successfully",
                    player_wallet=player_wallet,
                    quest_id=quest_id,
                    prestige_points=prestige_points
                )
            except Exception as e:
                self.logger.error(
                    "Failed to award prestige points",
                    player_wallet=player_wallet,
                    quest_id=quest_id,
                    prestige_points=prestige_points,
                    error=str(e)
                )
                # Re-raise the exception so the transaction fails
                raise
        
        # Mark as claimed
        progress.claim_reward(prestige_points, quest.bonus_reward)
        
        # Handle progressive quests
        next_quest_unlocked = None
        if quest.is_progressive:
            next_target = quest.get_next_target()
            if next_target:
                # Update quest with next target or create new progression
                quest.current_target = next_target
                next_quest_unlocked = quest
        
        await self.db.flush()
        
        # Get updated player prestige
        player_result = await self.db.execute(
            select(Player).where(Player.wallet == player_wallet)
        )
        player = player_result.scalar_one()
        
        self.logger.info(
            "Quest reward claimed",
            player_wallet=player_wallet,
            quest_id=quest_id,
            prestige_points=prestige_points,
            bonus_reward=quest.bonus_reward,
            new_total_prestige=player.prestige_points
        )
        
        return {
            "quest_id": quest_id,
            "prestige_points_awarded": prestige_points,
            "bonus_reward_awarded": quest.bonus_reward,
            "new_total_prestige": player.prestige_points,
            "next_quest_unlocked": next_quest_unlocked
        }
    
    # ============================================================================
    # AUTOMATIC PROGRESS TRACKING
    # ============================================================================
    
    async def track_business_purchase(self, player_wallet: str, business_cost: int) -> None:
        """Track business purchase for quest progress."""
        await self.update_quest_progress(
            player_wallet=player_wallet,
            quest_type=QuestType.BUSINESS_PURCHASE,
            progress_value=1,  # Increment count
            metadata={"business_cost": business_cost}
        )
    
    async def track_business_upgrade(self, player_wallet: str, upgrade_cost: int) -> None:
        """Track business upgrade for quest progress."""
        await self.update_quest_progress(
            player_wallet=player_wallet,
            quest_type=QuestType.BUSINESS_UPGRADE,
            progress_value=1,  # Increment count
            metadata={"upgrade_cost": upgrade_cost}
        )
    
    async def track_referral_invite(self, referrer_wallet: str, referee_wallet: str) -> None:
        """Track referral invite for quest progress."""
        # Count current referrals
        referral_count = await self._get_referral_count(referrer_wallet)
        
        await self.update_quest_progress(
            player_wallet=referrer_wallet,
            quest_type=QuestType.REFERRAL_INVITE,
            progress_value=referral_count,
            metadata={"latest_referee": referee_wallet}
        )
    
    async def track_earnings_claim(self, player_wallet: str, claim_amount: int) -> None:
        """Track earnings claim for quest progress."""
        await self.update_quest_progress(
            player_wallet=player_wallet,
            quest_type=QuestType.EARNINGS_CLAIM,
            progress_value=1,  # Increment count
            metadata={"claim_amount": claim_amount}
        )
    
    async def track_daily_login(self, player_wallet: str) -> None:
        """Track daily login for quest progress."""
        # Check if player already logged in today
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        result = await self.db.execute(
            select(PlayerQuestProgress)
            .join(Quest)
            .where(
                and_(
                    PlayerQuestProgress.player_wallet == player_wallet,
                    Quest.quest_type == QuestType.DAILY_LOGIN.value,
                    PlayerQuestProgress.last_progress_update >= today_start
                )
            )
        )
        
        if not result.scalar_one_or_none():
            await self.update_quest_progress(
                player_wallet=player_wallet,
                quest_type=QuestType.DAILY_LOGIN,
                progress_value=1,
                metadata={"login_date": datetime.utcnow().isoformat()}
            )
    
    # ============================================================================
    # QUEST STATISTICS
    # ============================================================================
    
    async def get_player_quest_stats(self, player_wallet: str) -> Dict[str, Any]:
        """Get quest statistics for a player."""
        result = await self.db.execute(
            select(
                func.count(PlayerQuestProgress.id).label("total_started"),
                func.count().filter(PlayerQuestProgress.is_completed == True).label("total_completed"),
                func.count().filter(PlayerQuestProgress.is_claimed == True).label("total_claimed"),
                func.sum(PlayerQuestProgress.prestige_points_rewarded).label("total_prestige"),
                func.sum(PlayerQuestProgress.bonus_reward_given).label("total_bonus"),
                func.count().filter(
                    and_(
                        PlayerQuestProgress.is_completed == True,
                        PlayerQuestProgress.is_claimed == False
                    )
                ).label("ready_to_claim")
            ).where(PlayerQuestProgress.player_wallet == player_wallet)
        )
        
        stats = result.first()
        
        return {
            "player_wallet": player_wallet,
            "total_quests_started": stats.total_started or 0,
            "total_quests_completed": stats.total_completed or 0,
            "total_quests_claimed": stats.total_claimed or 0,
            "total_prestige_earned": stats.total_prestige or 0,
            "total_bonus_earned": stats.total_bonus or 0,
            "quests_ready_to_claim": stats.ready_to_claim or 0
        }
    
    async def get_quest_leaderboard(
        self,
        limit: int = 50,
        period: str = "all"
    ) -> List[Dict[str, Any]]:
        """Get quest completion leaderboard."""
        base_query = select(
            PlayerQuestProgress.player_wallet,
            func.count().filter(PlayerQuestProgress.is_completed == True).label("completed_count"),
            func.sum(PlayerQuestProgress.prestige_points_rewarded).label("total_prestige")
        ).group_by(PlayerQuestProgress.player_wallet)
        
        if period == "weekly":
            week_ago = datetime.utcnow() - timedelta(days=7)
            base_query = base_query.where(PlayerQuestProgress.completed_at >= week_ago)
        elif period == "monthly":
            month_ago = datetime.utcnow() - timedelta(days=30)
            base_query = base_query.where(PlayerQuestProgress.completed_at >= month_ago)
        
        query = base_query.order_by(desc("completed_count")).limit(limit)
        
        result = await self.db.execute(query)
        entries = result.all()
        
        leaderboard = []
        for i, (wallet, completed, prestige) in enumerate(entries, 1):
            leaderboard.append({
                "rank": i,
                "player_wallet": wallet,
                "total_completed": completed or 0,
                "total_prestige_earned": prestige or 0
            })
        
        return leaderboard
    
    # ============================================================================
    # QUEST CATEGORIES
    # ============================================================================
    
    async def get_quest_categories(self, is_active: bool = True) -> List[QuestCategory]:
        """Get all quest categories."""
        query = select(QuestCategory)
        
        if is_active is not None:
            query = query.where(QuestCategory.is_active == is_active)
        
        query = query.order_by(QuestCategory.order_priority, QuestCategory.id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    # ============================================================================
    # SYSTEM INITIALIZATION
    # ============================================================================
    
    async def initialize_default_quests(self) -> None:
        """Initialize default quests for the system."""
        await self._create_default_categories()
        await self._create_default_quests()
        
        self.logger.info("Default quests initialized")
    
    async def _create_default_categories(self) -> None:
        """Create default quest categories."""
        categories_data = [
            {
                "name_en": "Social Media",
                "name_ru": "Социальные сети",
                "description_en": "Connect with our community on social platforms",
                "description_ru": "Присоединяйтесь к нашему сообществу в социальных сетях",
                "icon": "social",
                "color": "#3b82f6",
                "order_priority": 1
            },
            {
                "name_en": "Business Activities",
                "name_ru": "Бизнес активности",
                "description_en": "Build and grow your business empire",
                "description_ru": "Создавайте и развивайте свою бизнес-империю",
                "icon": "business",
                "color": "#10b981",
                "order_priority": 2
            },
            {
                "name_en": "Referral Program",
                "name_ru": "Реферальная программа",
                "description_en": "Invite friends and earn rewards",
                "description_ru": "Приглашайте друзей и получайте награды",
                "icon": "users",
                "color": "#f59e0b",
                "order_priority": 3
            },
            {
                "name_en": "Daily Tasks",
                "name_ru": "Ежедневные задания",
                "description_en": "Complete daily activities for consistent rewards",
                "description_ru": "Выполняйте ежедневные активности для постоянных наград",
                "icon": "calendar",
                "color": "#8b5cf6",
                "order_priority": 4
            }
        ]
        
        for category_data in categories_data:
            # Check if category already exists
            result = await self.db.execute(
                select(QuestCategory).where(QuestCategory.name_en == category_data["name_en"])
            )
            if not result.scalar_one_or_none():
                category = QuestCategory(**category_data)
                self.db.add(category)
        
        await self.db.flush()
    
    async def _create_default_quests(self) -> None:
        """Create default quests."""
        # Get categories
        categories_result = await self.db.execute(select(QuestCategory))
        categories = {cat.name_en: cat for cat in categories_result.scalars().all()}
        
        social_cat = categories.get("Social Media")
        business_cat = categories.get("Business Activities")
        referral_cat = categories.get("Referral Program")
        daily_cat = categories.get("Daily Tasks")
        
        quests_data = [
            # Social Media Quests
            {
                "category_id": social_cat.id if social_cat else None,
                "quest_type": QuestType.SOCIAL_FOLLOW.value,
                "title_en": "Follow us on Twitter",
                "title_ru": "Подпишитесь на нас в Twitter",
                "description_en": "Follow our official Twitter account @SolanaMafia",
                "description_ru": "Подпишитесь на наш официальный Twitter @SolanaMafia",
                "target_value": 1,
                "prestige_reward": 25,
                "social_links": {"twitter": settings.social_twitter_url},
                "order_priority": 1
            },
            {
                "category_id": social_cat.id if social_cat else None,
                "quest_type": QuestType.SOCIAL_FOLLOW.value,
                "title_en": "Join our Telegram",
                "title_ru": "Присоединяйтесь к нашему Telegram",
                "description_en": "Join our main Telegram channel",
                "description_ru": "Присоединитесь к нашему основному Telegram каналу",
                "target_value": 1,
                "prestige_reward": 30,
                "social_links": {"telegram": settings.social_telegram_url},
                "order_priority": 2
            },
            {
                "category_id": social_cat.id if social_cat else None,
                "quest_type": QuestType.SOCIAL_FOLLOW.value,
                "title_en": "Join our Telegram Chat",
                "title_ru": "Присоединяйтесь к чату в Telegram",
                "description_en": "Join our community chat",
                "description_ru": "Присоединитесь к нашему чату сообщества",
                "target_value": 1,
                "prestige_reward": 35,
                "social_links": {"telegram_chat": settings.social_telegram_chat_url},
                "order_priority": 3
            },
            {
                "category_id": social_cat.id if social_cat else None,
                "quest_type": QuestType.SOCIAL_FOLLOW.value,
                "title_en": "Follow CEO Channel",
                "title_ru": "Подпишитесь на канал CEO",
                "description_en": "Follow our CEO's personal channel",
                "description_ru": "Подпишитесь на персональный канал нашего CEO",
                "target_value": 1,
                "prestige_reward": 40,
                "social_links": {"ceo_channel": settings.social_ceo_channel_url},
                "order_priority": 4
            },
            
            # Business Quests
            {
                "category_id": business_cat.id if business_cat else None,
                "quest_type": QuestType.BUSINESS_PURCHASE.value,
                "title_en": "Purchase Your First Business",
                "title_ru": "Купите свой первый бизнес",
                "description_en": "Buy any business to start earning passive income",
                "description_ru": "Купите любой бизнес, чтобы начать получать пассивный доход",
                "target_value": 1,
                "prestige_reward": 50,
                "order_priority": 1
            },
            {
                "category_id": business_cat.id if business_cat else None,
                "quest_type": QuestType.BUSINESS_UPGRADE.value,
                "title_en": "Upgrade a Business",
                "title_ru": "Улучшите бизнес",
                "description_en": "Upgrade any of your businesses to increase earnings",
                "description_ru": "Улучшите любой из своих бизнесов для увеличения дохода",
                "target_value": 1,
                "prestige_reward": 30,
                "order_priority": 2
            },
            
            # Referral Quests (Progressive)
            {
                "category_id": referral_cat.id if referral_cat else None,
                "quest_type": QuestType.REFERRAL_INVITE.value,
                "title_en": "Invite Friends",
                "title_ru": "Пригласите друзей",
                "description_en": "Invite friends to join Solana Mafia",
                "description_ru": "Пригласите друзей присоединиться к Solana Mafia",
                "target_value": 1,
                "current_target": 1,
                "max_target": 500,
                "prestige_reward": 100,
                "is_progressive": True,
                "order_priority": 1
            },
            
            # Daily Quests
            {
                "category_id": daily_cat.id if daily_cat else None,
                "quest_type": QuestType.DAILY_LOGIN.value,
                "title_en": "Daily Login",
                "title_ru": "Ежедневный вход",
                "description_en": "Log in daily to earn rewards",
                "description_ru": "Входите ежедневно, чтобы получать награды",
                "target_value": 1,
                "prestige_reward": 10,
                "is_repeatable": True,
                "is_daily": True,
                "cooldown_hours": 20,
                "order_priority": 1
            },
            {
                "category_id": daily_cat.id if daily_cat else None,
                "quest_type": QuestType.EARNINGS_CLAIM.value,
                "title_en": "Claim Earnings",
                "title_ru": "Получите доходы",
                "description_en": "Claim your business earnings",
                "description_ru": "Получите доходы от своих бизнесов",
                "target_value": 1,
                "prestige_reward": 15,
                "is_repeatable": True,
                "cooldown_hours": 1,
                "order_priority": 2
            }
        ]
        
        for quest_data in quests_data:
            # Check if quest already exists
            result = await self.db.execute(
                select(Quest).where(
                    and_(
                        Quest.quest_type == quest_data["quest_type"],
                        Quest.title_en == quest_data["title_en"]
                    )
                )
            )
            if not result.scalar_one_or_none():
                quest = Quest(**quest_data)
                self.db.add(quest)
        
        await self.db.flush()
    
    # ============================================================================
    # HELPER METHODS
    # ============================================================================
    
    async def _get_referral_count(self, player_wallet: str) -> int:
        """Get current referral count for player."""
        # This would integrate with the referral system
        # For now, return a placeholder
        from app.models.referral import ReferralRelation
        
        result = await self.db.execute(
            select(func.count())
            .select_from(ReferralRelation)
            .where(ReferralRelation.referrer_id == player_wallet)
        )
        
        return result.scalar() or 0


# Singleton service instance getter
async def get_quest_service(db: AsyncSession) -> QuestService:
    """Get quest service instance."""
    return QuestService(db)
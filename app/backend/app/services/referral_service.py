"""
Referral system business logic.
Handles 3-level referral system with 5%, 2%, 1% commission rates.
"""

import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_, desc, func
from sqlalchemy.orm import selectinload

import structlog

from app.models.user import User, UserType
from app.models.referral import (
    ReferralCode, ReferralRelation, ReferralCommission,
    ReferralStats, ReferralConfig
)
from app.models.player import Player
from app.core.exceptions import ValidationError, NotFoundError

logger = structlog.get_logger(__name__)


class ReferralService:
    """Service for managing the referral system."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_user(
        self,
        user_id: str,
        user_type: UserType,
        telegram_user_id: Optional[int] = None,
        wallet_address: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        username: Optional[str] = None,
        language_code: Optional[str] = None,
        is_premium: Optional[bool] = None
    ) -> User:
        """Get or create a user."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            if user_type == UserType.TELEGRAM:
                user = User.create_telegram_user(
                    telegram_user_id=telegram_user_id,
                    first_name=first_name or "Unknown",
                    last_name=last_name,
                    username=username,
                    language_code=language_code,
                    is_premium=is_premium
                )
            else:
                user = User.create_wallet_user(wallet_address=wallet_address)
            
            # Generate referral code
            user.referral_code = await self._generate_unique_referral_code()
            
            self.db.add(user)
            await self.db.flush()
            
            logger.info("Created new user", user_id=user_id, user_type=user_type)
        
        return user
    
    async def create_referral_code(self, user_id: str) -> ReferralCode:
        """Create a referral code for a user."""
        # Get user
        user = await self._get_user_by_id(user_id)
        
        # Check if user already has an active code
        result = await self.db.execute(
            select(ReferralCode).where(
                and_(
                    ReferralCode.owner_id == user_id,
                    ReferralCode.is_active == True
                )
            )
        )
        existing_code = result.scalar_one_or_none()
        
        if existing_code and not existing_code.is_expired:
            return existing_code
        
        # Create new code
        code = ReferralCode(
            code=await self._generate_unique_referral_code(),
            owner_id=user_id,
            owner_type=user.user_type
        )
        
        self.db.add(code)
        await self.db.flush()
        
        logger.info("Created referral code", user_id=user_id, code=code.code)
        return code
    
    async def process_referral(
        self,
        referral_code: str,
        referee_id: str,
        referee_type: UserType,
        **referee_data
    ) -> Optional[List[ReferralRelation]]:
        """Process a new referral and create multi-level relations."""
        # Validate referral code
        result = await self.db.execute(
            select(ReferralCode).where(
                and_(
                    ReferralCode.code == referral_code,
                    ReferralCode.is_active == True
                )
            )
        )
        referral_code_obj = result.scalar_one_or_none()
        
        if not referral_code_obj or referral_code_obj.is_expired:
            logger.warning("Invalid or expired referral code", code=referral_code)
            return None
        
        # Get or create referee
        referee = await self.get_or_create_user(
            user_id=referee_id,
            user_type=referee_type,
            **referee_data
        )
        
        # Check if referee is already referred
        existing_relation = await self.db.execute(
            select(ReferralRelation).where(
                ReferralRelation.referee_id == referee_id
            )
        )
        if existing_relation.scalar_one_or_none():
            logger.warning("User already referred", referee_id=referee_id)
            return None
        
        # Can't refer yourself
        if referral_code_obj.owner_id == referee_id:
            logger.warning("Self-referral attempt", user_id=referee_id)
            return None
        
        # Get current config
        config = await self._get_current_config()
        
        # Create referral relations for multiple levels
        relations = []
        current_referrer_id = referral_code_obj.owner_id
        
        for level in range(1, config.max_referral_levels + 1):
            if not current_referrer_id:
                break
            
            # Create referral relation
            relation = ReferralRelation(
                referrer_id=current_referrer_id,
                referrer_type=UserType.WALLET if current_referrer_id.startswith('0x') or len(current_referrer_id) == 44 else UserType.TELEGRAM,
                referee_id=referee_id,
                referee_type=referee_type,
                referral_code_id=referral_code_obj.id,
                level=level,
                commission_rate=config.get_rate_for_level(level)
            )
            
            self.db.add(relation)
            relations.append(relation)
            
            logger.info(
                "Created referral relation",
                referrer_id=current_referrer_id,
                referee_id=referee_id,
                level=level,
                commission_rate=float(relation.commission_rate)
            )
            
            # Find next level referrer
            next_referrer = await self.db.execute(
                select(ReferralRelation).where(
                    ReferralRelation.referee_id == current_referrer_id
                ).limit(1)
            )
            next_relation = next_referrer.scalar_one_or_none()
            
            if next_relation:
                current_referrer_id = next_relation.referrer_id
            else:
                break
        
        # Update code usage
        referral_code_obj.usage_count += 1
        
        # Update referee's referrer
        referee.referrer_id = referral_code_obj.owner_id
        
        await self.db.flush()
        
        # Update referral stats
        await self._update_referral_stats_for_relations(relations)
        
        return relations
    
    async def process_earning_commission(
        self,
        user_id: str,
        earning_amount: int,
        earning_event_id: Optional[str] = None
    ) -> List[ReferralCommission]:
        """Process referral commissions when a user earns."""
        config = await self._get_current_config()
        
        if not config.is_enabled or earning_amount < config.min_earning_threshold:
            return []
        
        # Get all referral relations where this user is the referee
        result = await self.db.execute(
            select(ReferralRelation).where(
                and_(
                    ReferralRelation.referee_id == user_id,
                    ReferralRelation.is_active == True
                )
            ).order_by(ReferralRelation.level)
        )
        relations = result.scalars().all()
        
        commissions = []
        
        for relation in relations:
            # Calculate commission
            commission_amount = int(earning_amount * relation.commission_rate)
            
            if commission_amount > 0:
                # Create commission record
                commission = ReferralCommission(
                    referral_relation_id=relation.id,
                    earning_event_id=earning_event_id,
                    referee_earning_amount=earning_amount,
                    commission_amount=commission_amount,
                    commission_rate=relation.commission_rate,
                    status="pending"
                )
                
                self.db.add(commission)
                commissions.append(commission)
                
                # Update relation totals
                relation.total_earnings_referred += earning_amount
                relation.total_commission_earned += commission_amount
                
                if not relation.first_earning_at:
                    relation.first_earning_at = datetime.utcnow()
                
                logger.info(
                    "Created referral commission",
                    referrer_id=relation.referrer_id,
                    referee_id=relation.referee_id,
                    level=relation.level,
                    earning_amount=earning_amount,
                    commission_amount=commission_amount,
                    rate=float(relation.commission_rate)
                )
        
        await self.db.flush()
        
        if commissions:
            # Update referral stats
            await self._update_referral_stats_after_commission(commissions)
        
        return commissions
    
    async def get_user_referral_stats(self, user_id: str) -> Optional[ReferralStats]:
        """Get referral statistics for a user."""
        result = await self.db.execute(
            select(ReferralStats).where(ReferralStats.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_referrals(
        self,
        user_id: str,
        level: Optional[int] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get referrals made by a user."""
        query = select(ReferralRelation).where(
            ReferralRelation.referrer_id == user_id
        )
        
        if level:
            query = query.where(ReferralRelation.level == level)
        
        query = query.order_by(desc(ReferralRelation.created_at))
        query = query.limit(limit).offset(offset)
        
        result = await self.db.execute(query)
        relations = result.scalars().all()
        
        referrals = []
        for relation in relations:
            # Get referee info
            referee = await self._get_user_by_id(relation.referee_id)
            
            referrals.append({
                "referee_id": relation.referee_id,
                "referee_name": referee.display_name if referee else "Unknown",
                "level": relation.level,
                "commission_rate": float(relation.commission_rate),
                "total_earnings_referred": relation.total_earnings_referred,
                "total_commission_earned": relation.total_commission_earned,
                "first_earning_at": relation.first_earning_at,
                "created_at": relation.created_at
            })
        
        return referrals
    
    async def get_pending_commissions(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[ReferralCommission]:
        """Get pending commissions for a user."""
        result = await self.db.execute(
            select(ReferralCommission)
            .join(ReferralRelation)
            .where(
                and_(
                    ReferralRelation.referrer_id == user_id,
                    ReferralCommission.status == "pending"
                )
            )
            .order_by(desc(ReferralCommission.created_at))
            .limit(limit)
            .offset(offset)
        )
        return result.scalars().all()
    
    async def pay_commission(
        self,
        commission_id: int,
        transaction_signature: Optional[str] = None
    ) -> ReferralCommission:
        """Mark a commission as paid."""
        result = await self.db.execute(
            select(ReferralCommission).where(ReferralCommission.id == commission_id)
        )
        commission = result.scalar_one_or_none()
        
        if not commission:
            raise NotFoundError(f"Commission {commission_id} not found")
        
        commission.status = "paid"
        commission.paid_at = datetime.utcnow()
        commission.transaction_signature = transaction_signature
        
        await self.db.flush()
        
        logger.info(
            "Commission marked as paid",
            commission_id=commission_id,
            amount=commission.commission_amount,
            transaction=transaction_signature
        )
        
        return commission
    
    async def get_referral_leaderboard(
        self,
        period: str = "all",  # "daily", "weekly", "monthly", "all"
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get referral leaderboard."""
        # Calculate date filter
        now = datetime.utcnow()
        date_filter = None
        
        if period == "daily":
            date_filter = now - timedelta(days=1)
        elif period == "weekly":
            date_filter = now - timedelta(weeks=1)
        elif period == "monthly":
            date_filter = now - timedelta(days=30)
        
        # Build query
        query = select(
            ReferralStats.user_id,
            ReferralStats.user_type,
            ReferralStats.total_referrals,
            ReferralStats.total_referral_earnings,
            ReferralStats.level_1_referrals,
            ReferralStats.level_2_referrals,
            ReferralStats.level_3_referrals
        )
        
        if date_filter:
            query = query.where(ReferralStats.last_updated_at >= date_filter)
        
        query = query.order_by(desc(ReferralStats.total_referral_earnings))
        query = query.limit(limit)
        
        result = await self.db.execute(query)
        stats = result.all()
        
        leaderboard = []
        for i, stat in enumerate(stats, 1):
            # Get user info
            user = await self._get_user_by_id(stat.user_id)
            
            leaderboard.append({
                "rank": i,
                "user_id": stat.user_id,
                "user_name": user.display_name if user else "Unknown",
                "user_type": stat.user_type,
                "total_referrals": stat.total_referrals,
                "total_earnings": stat.total_referral_earnings,
                "level_breakdown": {
                    "level_1": stat.level_1_referrals,
                    "level_2": stat.level_2_referrals,
                    "level_3": stat.level_3_referrals
                }
            })
        
        return leaderboard
    
    # Private helper methods
    
    async def _get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def _generate_unique_referral_code(self, length: int = 8) -> str:
        """Generate a unique referral code."""
        max_attempts = 10
        
        for _ in range(max_attempts):
            code = ReferralCode.generate_code(length)
            
            # Check if code exists
            result = await self.db.execute(
                select(ReferralCode).where(ReferralCode.code == code)
            )
            if not result.scalar_one_or_none():
                return code
        
        # Fallback to longer code
        return ReferralCode.generate_code(length + 4)
    
    async def _get_current_config(self) -> ReferralConfig:
        """Get current referral configuration."""
        result = await self.db.execute(
            select(ReferralConfig)
            .where(
                and_(
                    ReferralConfig.is_enabled == True,
                    ReferralConfig.active_from <= datetime.utcnow(),
                    or_(
                        ReferralConfig.active_until.is_(None),
                        ReferralConfig.active_until > datetime.utcnow()
                    )
                )
            )
            .order_by(desc(ReferralConfig.version))
            .limit(1)
        )
        config = result.scalar_one_or_none()
        
        if not config:
            # Create default config
            config = ReferralConfig()
            self.db.add(config)
            await self.db.flush()
            
            logger.info("Created default referral config")
        
        return config
    
    async def _update_referral_stats_for_relations(
        self,
        relations: List[ReferralRelation]
    ) -> None:
        """Update referral stats after creating relations."""
        for relation in relations:
            await self._ensure_referral_stats(relation.referrer_id)
            
            # Increment referral count
            await self.db.execute(
                update(ReferralStats)
                .where(ReferralStats.user_id == relation.referrer_id)
                .values({
                    f"level_{relation.level}_referrals": ReferralStats.__table__.c[f"level_{relation.level}_referrals"] + 1,
                    "last_updated_at": datetime.utcnow()
                })
            )
    
    async def _update_referral_stats_after_commission(
        self,
        commissions: List[ReferralCommission]
    ) -> None:
        """Update referral stats after processing commissions."""
        for commission in commissions:
            relation = await self.db.execute(
                select(ReferralRelation).where(ReferralRelation.id == commission.referral_relation_id)
            )
            relation = relation.scalar_one()
            
            await self._ensure_referral_stats(relation.referrer_id)
            
            # Update earnings
            await self.db.execute(
                update(ReferralStats)
                .where(ReferralStats.user_id == relation.referrer_id)
                .values({
                    f"level_{relation.level}_earnings": ReferralStats.__table__.c[f"level_{relation.level}_earnings"] + commission.commission_amount,
                    "pending_commission": ReferralStats.__table__.c["pending_commission"] + commission.commission_amount,
                    "last_updated_at": datetime.utcnow()
                })
            )
    
    async def _ensure_referral_stats(self, user_id: str) -> None:
        """Ensure referral stats record exists for user."""
        result = await self.db.execute(
            select(ReferralStats).where(ReferralStats.user_id == user_id)
        )
        stats = result.scalar_one_or_none()
        
        if not stats:
            user = await self._get_user_by_id(user_id)
            stats = ReferralStats(
                user_id=user_id,
                user_type=user.user_type if user else UserType.WALLET
            )
            self.db.add(stats)
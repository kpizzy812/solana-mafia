"""
Notification service for event indexing.
"""

from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserType
from app.models.referral import ReferralRelation
from app.services.telegram_bot_service import get_telegram_service


logger = structlog.get_logger(__name__)


class NotificationService:
    """
    Handles notifications for various indexer events.
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize the notification service."""
        self.db = db
        self.logger = logger.bind(service="notification_service")
        
    async def notify_earnings_update(
        self,
        wallet_address: str,
        earning_amount: int,
        total_earnings: int
    ):
        """Send notification about earnings update."""
        try:
            # Get user by wallet address
            user = await self._get_user_by_wallet(wallet_address)
            if not user or user.user_type != UserType.TELEGRAM:
                return
            
            telegram_service = get_telegram_service()
            if telegram_service.is_available():
                await telegram_service.notify_earnings_available(
                    user=user,
                    earning_amount=earning_amount,
                    total_pending=total_earnings
                )
                
        except Exception as e:
            self.logger.error(
                "Failed to send earnings notification",
                error=str(e),
                wallet=wallet_address
            )
    
    async def notify_referral_commissions(self, commissions: List):
        """Send notifications about referral commissions."""
        try:
            telegram_service = get_telegram_service()
            if not telegram_service.is_available():
                return
            
            for commission in commissions:
                # Get referrer user
                relation_result = await self.db.execute(
                    select(ReferralRelation).where(
                        ReferralRelation.id == commission.referral_relation_id
                    )
                )
                relation = relation_result.scalar_one_or_none()
                
                if not relation:
                    continue
                
                referrer_user = await self._get_user_by_id(relation.referrer_id)
                referee_user = await self._get_user_by_id(relation.referee_id)
                
                if (referrer_user and 
                    referrer_user.user_type == UserType.TELEGRAM and 
                    referee_user):
                    
                    await telegram_service.notify_referral_commission(
                        user=referrer_user,
                        commission=commission,
                        referee_name=referee_user.display_name
                    )
                    
        except Exception as e:
            self.logger.error("Failed to send referral notifications", error=str(e))
    
    async def _get_user_by_wallet(self, wallet_address: str) -> Optional[User]:
        """Get user by wallet address."""
        try:
            result = await self.db.execute(
                select(User).where(User.wallet_address == wallet_address)
            )
            return result.scalar_one_or_none()
        except Exception:
            return None
    
    async def _get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            result = await self.db.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception:
            return None
"""
Event handlers for earnings-related events.
"""

from datetime import datetime

import structlog
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.event_parser import ParsedEvent
from app.models.player import Player
from app.models.earnings import EarningsHistory
from app.services.referral_service import ReferralService
from app.websocket.notification_service import notification_service
from app.services.prestige_service import PrestigeService
from app.models.prestige import ActionType


logger = structlog.get_logger(__name__)


class EarningsHandlers:
    """
    Handles earnings-related blockchain events.
    """
    
    def __init__(self, stats):
        """Initialize earnings handlers."""
        self.stats = stats
        self.logger = logger.bind(service="earnings_handlers")
        
    async def handle_earnings_updated(self, db: AsyncSession, event: ParsedEvent):
        """Handle EarningsUpdated event - update pending_earnings for claim system."""
        try:
            data = event.data
            wallet_address = data["player"]  # Fixed: use "player" from event
            earnings_added = data["earnings_added"]
            total_pending = data["total_pending"]
            
            self.logger.info(
                "💰 Processing earnings update from contract",
                wallet=wallet_address,
                earnings_added=earnings_added,
                total_pending=total_pending
            )
            
            # 🔧 ИСПРАВЛЕНИЕ: При обработке нескольких событий из одной транзакции,
            # берем максимальное total_pending (защита от перезаписи меньшим значением)
            from sqlalchemy import select
            
            # Получаем текущее значение
            result = await db.execute(
                select(Player.pending_earnings).where(Player.wallet == wallet_address)
            )
            current_pending = result.scalar()
            
            # Используем максимальное значение между текущим и новым
            max_pending = max(current_pending or 0, total_pending)
            
            self.logger.info(
                "🔧 Earnings update logic",
                wallet=wallet_address,
                current_pending=current_pending,
                event_total_pending=total_pending,
                final_pending=max_pending
            )
            
            # Update player pending_earnings from contract state
            await db.execute(
                update(Player)
                .where(Player.wallet == wallet_address)
                .values(
                    pending_earnings=max_pending,  # Use maximum value
                    last_earnings_update=event.block_time or datetime.utcnow(),
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            # 📝 ИСПРАВЛЕНИЕ: Записывать в earnings_history для отслеживания событий
            if earnings_added > 0:  # Только если действительно были начислены earnings
                earnings_history = EarningsHistory(
                    player_wallet=wallet_address,
                    event_type="earnings_updated",
                    amount=earnings_added,
                    previous_balance=max_pending - earnings_added,
                    new_balance=max_pending,
                    base_earnings=earnings_added,  # Простое начисление без бонусов
                    slot_bonus_earnings=0,
                    referral_earnings=0,
                    business_count=data.get("business_count", 1),
                    transaction_signature=event.signature,
                    processing_time_ms=0,
                    indexer_version="2.0",
                    created_at=event.block_time or datetime.utcnow(),
                    updated_at=event.block_time or datetime.utcnow()
                )
                db.add(earnings_history)
                
                self.logger.info(
                    "📝 Earnings event recorded to history",
                    wallet=wallet_address,
                    earnings_added=earnings_added,
                    total_pending=max_pending,
                    signature=event.signature
                )
            
            # Send WebSocket notification to user about earnings update
            try:
                await notification_service.notify_earnings_updated(
                    wallet=wallet_address, 
                    earnings_data={
                        "earnings_balance": max_pending,
                        "earnings_added": earnings_added,
                        "event_signature": event.signature,
                        "updated_at": (event.block_time or datetime.utcnow()).isoformat()
                    }
                )
            except Exception as notify_error:
                self.logger.error(
                    "Failed to send earnings update notification",
                    wallet=wallet_address,
                    error=str(notify_error)
                )
            
            self.stats.earnings_updated += 1
            
            self.logger.debug(
                "Earnings updated (commissions processed on claim)",
                wallet=wallet_address,
                amount=earnings_added
            )
            
        except Exception as e:
            self.logger.error("Failed to handle EarningsUpdated event", error=str(e))
            raise
            
    async def handle_earnings_claimed(self, db: AsyncSession, event: ParsedEvent):
        """Handle EarningsClaimed event."""
        try:
            data = event.data
            wallet_address = data["wallet"]
            net_amount = data["net_amount"]
            
            # Update player earnings and total claimed
            await db.execute(
                update(Player)
                .where(Player.wallet == wallet_address)
                .values(
                    earnings_balance=0,  # Reset after claiming
                    total_earnings=Player.total_earnings + net_amount,
                    last_earnings_update=event.block_time or datetime.utcnow(),
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            # Process referral commissions for claimed earnings
            await self._process_referral_commissions(
                db=db,
                wallet_address=wallet_address,
                earning_amount=net_amount,
                event_id=f"{event.signature}_{event.instruction_index if event.instruction_index is not None else hash(str(event.data))}_claimed"
            )
            
            # Award prestige points for earnings claim
            try:
                prestige_service = PrestigeService(db)
                points_awarded, level_up = await prestige_service.calculate_and_award_points(
                    player_wallet=wallet_address,
                    action_type=ActionType.EARNINGS_CLAIM,
                    action_value=net_amount,
                    related_transaction=event.signature,
                    related_event_id=None
                )
                
                if points_awarded > 0:
                    self.logger.info(
                        "Prestige points awarded for earnings claim",
                        wallet=wallet_address,
                        points=points_awarded,
                        level_up=level_up,
                        claimed_amount=net_amount
                    )
            except Exception as prestige_error:
                self.logger.error(
                    "Failed to award prestige points for earnings claim",
                    wallet=wallet_address,
                    error=str(prestige_error)
                )
                # Don't fail the claim if prestige fails
            
            # Send WebSocket notification about earnings claim
            try:
                await notification_service.notify_earnings_claimed(
                    wallet=wallet_address,
                    claim_data={
                        "amount": net_amount,
                        "remaining_balance": 0,  # Balance is reset to 0 after claiming
                        "event_signature": event.signature,
                        "claimed_at": (event.block_time or datetime.utcnow()).isoformat()
                    }
                )
            except Exception as notify_error:
                self.logger.error(
                    "Failed to send earnings claim notification",
                    wallet=wallet_address,
                    error=str(notify_error)
                )
            
            self.stats.earnings_claimed += 1
            
            self.logger.info(
                "Earnings claimed",
                wallet=data["wallet"],
                amount=data["amount_claimed"],
                net_amount=data["net_amount"]
            )
            
        except Exception as e:
            self.logger.error("Failed to handle EarningsClaimed event", error=str(e))
            raise
            
    async def _process_referral_commissions(
        self,
        db: AsyncSession,
        wallet_address: str,
        earning_amount: int,
        event_id: str
    ):
        """Process referral commissions for a user's earnings."""
        try:
            # Create referral service instance
            referral_service = ReferralService(db)
            
            # Process commissions for this earning
            commissions = await referral_service.process_earning_commission(
                user_id=wallet_address,
                earning_amount=earning_amount,
                earning_event_id=event_id
            )
            
            if commissions:
                self.logger.info(
                    "Referral commissions processed",
                    wallet=wallet_address,
                    earning_amount=earning_amount,
                    commissions_count=len(commissions),
                    total_commission=sum(c.commission_amount for c in commissions)
                )
                
                # Send WebSocket notifications to referrers about commissions
                try:
                    for commission in commissions:
                        # Notify referrer about commission earned
                        await notification_service.notify_referral_commission(
                            referrer_wallet=commission.referrer_id,
                            commission_data={
                                "referee_wallet": wallet_address,
                                "commission_amount": commission.commission_amount,
                                "commission_rate": float(commission.commission_rate),
                                "level": commission.level,
                                "referee_earning_amount": earning_amount,
                                "action_type": "earnings_claim",
                                "earning_event_id": event_id,
                                "commission_id": commission.id
                            }
                        )
                        
                        # Update referrer's stats and notify
                        referral_service = ReferralService(db)
                        updated_stats = await referral_service.get_user_referral_stats(commission.referrer_id)
                        if updated_stats:
                            await notification_service.notify_referral_stats_update(
                                wallet=commission.referrer_id,
                                stats_data={
                                    "total_referrals": updated_stats.total_referrals,
                                    "total_earnings": updated_stats.total_referral_earnings,
                                    "pending_commission": updated_stats.pending_commission,
                                    "level_1_referrals": updated_stats.level_1_referrals,
                                    "level_2_referrals": updated_stats.level_2_referrals,
                                    "level_3_referrals": updated_stats.level_3_referrals,
                                    "updated_reason": "referral_commission_earned",
                                    "commission_from": wallet_address,
                                    "commission_amount": commission.commission_amount
                                }
                            )
                    
                    self.logger.info(
                        "✅ WebSocket notifications sent for referral commissions",
                        referrer_count=len(commissions),
                        referee=wallet_address,
                        total_commissions=sum(c.commission_amount for c in commissions)
                    )
                    
                except Exception as notify_error:
                    self.logger.error(
                        "Failed to send referral commission notifications",
                        referee=wallet_address,
                        error=str(notify_error)
                    )
            
        except Exception as e:
            self.logger.error(
                "Failed to process referral commissions",
                error=str(e),
                wallet=wallet_address,
                earning_amount=earning_amount
            )
            # Don't raise here to avoid breaking earnings processing
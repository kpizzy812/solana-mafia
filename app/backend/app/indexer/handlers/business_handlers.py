"""
Event handlers for business-related events.
"""

from datetime import datetime

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.event_parser import ParsedEvent
from app.models.player import Player
from app.models.business import Business, BusinessType
from app.models.user import User, UserType
from app.services.prestige_service import PrestigeService
from app.services.referral_service import ReferralService
from app.models.prestige import ActionType
from app.websocket.notification_service import notification_service


logger = structlog.get_logger(__name__)


class BusinessHandlers:
    """
    Handles business-related blockchain events.
    """
    
    def __init__(self, stats):
        """Initialize business handlers."""
        self.stats = stats
        self.logger = logger.bind(service="business_handlers")
        
    async def handle_business_created(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessCreated event."""
        try:
            data = event.data
            player_wallet = data["owner"]
            
            # 🔧 ИСПРАВЛЕНИЕ: Найти или создать пользователя
            user = await self._get_or_create_user(db, player_wallet)
            
            # Check if this is player's first business (player creation)
            existing_businesses = await db.execute(
                select(Business).where(Business.player_wallet == player_wallet)
            )
            is_first_business = len(existing_businesses.scalars().all()) == 0
            
            # Create business record
            business = Business(
                owner_id=user.id,  # 🔧 ИСПРАВЛЕНИЕ: Используем user.id вместо wallet
                player_wallet=player_wallet,
                business_type=BusinessType(data["business_type"]),
                level=0,  # Base level matches contract upgrade_level=0
                slot_index=data["slot_index"],
                base_cost=data["base_cost"],
                total_invested_amount=data["total_paid"],
                daily_rate=data["daily_rate"],  # Already daily rate
                created_at=event.block_time or datetime.utcnow(),
                on_chain_created_at=event.block_time,
                creation_signature=event.signature,
                is_active=True
            )
            
            db.add(business)
            self.stats.businesses_created += 1
            
            # Award prestige points for business purchase
            try:
                prestige_service = PrestigeService(db)
                points_awarded, level_up = await prestige_service.award_business_purchase_points(
                    player_wallet=player_wallet,
                    business_cost=data["total_paid"],
                    business_type=data["business_type"],
                    slot_index=data["slot_index"],
                    transaction_signature=event.signature
                )
                
                if points_awarded > 0:
                    self.logger.info(
                        "Prestige points awarded for business purchase",
                        wallet=player_wallet,
                        points=points_awarded,
                        level_up=level_up
                    )
            except Exception as prestige_error:
                self.logger.error(
                    "Failed to award prestige points for business purchase",
                    wallet=player_wallet,
                    error=str(prestige_error)
                )
                # Don't fail the business creation if prestige fails
            
            # Award prestige to referrers for referral business activity
            try:
                referral_service = ReferralService(db)
                # Get all referrers who referred this player
                referrers = await referral_service.get_referrers(player_wallet)
                
                for referrer in referrers:
                    # Award prestige points to referrer for referral business activity
                    referrer_points, referrer_level_up = await prestige_service.calculate_and_award_points(
                        player_wallet=referrer["referrer_id"],
                        action_type=ActionType.REFERRAL_BUSINESS_ACTIVITY,
                        action_value=data["total_paid"],
                        action_metadata={
                            "referee_wallet": player_wallet,
                            "business_type": data["business_type"],
                            "referral_level": referrer["level"]
                        },
                        related_transaction=event.signature
                    )
                    
                    if referrer_points > 0:
                        self.logger.info(
                            "Prestige points awarded to referrer for business activity",
                            referrer=referrer["referrer_id"],
                            referee=player_wallet,
                            points=referrer_points,
                            level_up=referrer_level_up,
                            referral_level=referrer["level"]
                        )
                
                # Send WebSocket notifications to referrers about business activity
                try:
                    for referrer in referrers:
                        # Notify referrer about business activity
                        await notification_service.notify_referral_business_activity(
                            referrer_wallet=referrer["referrer_id"],
                            activity_data={
                                "referee_wallet": player_wallet,
                                "activity_type": "business_purchase",
                                "business_type": data["business_type"],
                                "amount": data["total_paid"],
                                "level": referrer["level"],
                                "slot_index": data["slot_index"],
                                "prestige_awarded": referrer_points if 'referrer_points' in locals() else 0,
                                "transaction_signature": event.signature
                            }
                        )
                        
                        # If referrer leveled up, send prestige notification
                        if 'referrer_level_up' in locals() and referrer_level_up:
                            await notification_service.notify_prestige_level_up(
                                wallet=referrer["referrer_id"],
                                prestige_data={
                                    "points_awarded": referrer_points,
                                    "reason": f"Referral business purchase by {player_wallet[:8]}...{player_wallet[-4:]}",
                                    "referral_related": True,
                                    "referee_wallet": player_wallet,
                                    "activity_type": "business_purchase"
                                }
                            )
                    
                    self.logger.info(
                        "✅ WebSocket notifications sent to referrers for business creation",
                        referee=player_wallet,
                        referrer_count=len(referrers),
                        business_type=data["business_type"]
                    )
                    
                except Exception as notification_error:
                    self.logger.error(
                        "Failed to send WebSocket notifications to referrers for business creation",
                        referee=player_wallet,
                        error=str(notification_error)
                    )
                    
            except Exception as referrer_prestige_error:
                self.logger.error(
                    "Failed to award prestige to referrers for business activity",
                    wallet=player_wallet,
                    error=str(referrer_prestige_error)
                )
                # Don't fail the business creation if referrer prestige fails
            
            # If this is player's first business, note it
            if is_first_business:
                self.logger.info(
                    "First business created - no earnings schedule needed in permissionless system",
                    wallet=player_wallet,
                    slot_index=data["slot_index"]
                )
            
            self.logger.info(
                "Business created",
                owner=data["owner"],
                business_type=data["business_type"],
                slot_index=data["slot_index"],
                is_first_business=is_first_business
            )
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessCreated event", error=str(e))
            raise
            
    async def handle_business_created_in_slot(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessCreatedInSlot event."""
        try:
            data = event.data
            
            # 🚨 ПРОВЕРКА НА ДУБЛИРОВАНИЕ: Check if business already exists for this signature
            existing_business_result = await db.execute(
                select(Business).where(Business.creation_signature == event.signature)
            )
            existing_business = existing_business_result.scalar_one_or_none()
            
            if existing_business:
                self.logger.debug(
                    "Business already exists for this transaction",
                    signature=event.signature,
                    existing_business_id=existing_business.id
                )
                return
            
            # Create or get user for the wallet
            owner_wallet = data["owner"]
            user_result = await db.execute(
                select(User).where(User.id == owner_wallet)
            )
            user = user_result.scalar_one_or_none()
            
            if not user:
                # Create wallet user if doesn't exist
                user = User.create_wallet_user(owner_wallet)
                db.add(user)
                self.logger.info("Created wallet user", wallet=owner_wallet)
                
            # Create or get player for the wallet  
            player_result = await db.execute(
                select(Player).where(Player.wallet == owner_wallet)
            )
            player = player_result.scalar_one_or_none()
            
            if not player:
                # Create player if doesn't exist
                player = Player(
                    wallet=owner_wallet,
                    unlocked_slots_count=5,  # BASE_BUSINESS_SLOTS from contract
                    is_active=True,
                    on_chain_created_at=event.block_time,
                    created_at=event.block_time or datetime.utcnow()
                )
                db.add(player)
                
                # Note: No earnings schedule needed in permissionless architecture
                self.logger.info(
                    "Created player - no earnings schedule needed in permissionless system", 
                    wallet=owner_wallet,
                    slot_index=data["slot_index"]
                )
            
            # Create business record (same as BusinessCreated but with slot context)
            business = Business(
                owner_id=data["owner"],  # Use owner_id instead of business_id
                player_wallet=data["owner"],
                business_type=BusinessType(data["business_type"]),
                level=data.get("level", 0),  # 🆕 USE ACTUAL LEVEL from event instead of hardcoded 0
                slot_index=data["slot_index"],
                base_cost=data["base_cost"],
                total_invested_amount=data["total_paid"],
                daily_rate=data["daily_rate"],  # Already daily rate
                created_at=event.block_time or datetime.utcnow(),
                on_chain_created_at=event.block_time,
                creation_signature=event.signature,
                is_active=True
            )
            
            db.add(business)
            self.stats.businesses_created += 1
            
            # 🔧 UPDATE PLAYER TOTAL_INVESTED
            await db.execute(
                update(Player)
                .where(Player.wallet == owner_wallet)
                .values(
                    total_invested=Player.total_invested + data["total_paid"],
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            self.logger.info(
                "Updated player total_invested",
                wallet=owner_wallet,
                amount_added=data["total_paid"],
                signature=event.signature
            )
            
            self.logger.info(
                "Business created in slot",
                owner=data["owner"],
                business_type=data["business_type"],
                level=data.get("level", 0),  # 🆕 LOG: Level field
                slot_index=data["slot_index"]
            )
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessCreatedInSlot event", error=str(e))
            raise
            
    async def handle_business_upgraded(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessUpgraded event."""
        try:
            data = event.data
            player_wallet = data["owner"]
            slot_index = data["slot_index"]
            
            # Get upgrade cost to add to total_invested_amount
            upgrade_cost = data.get("upgrade_cost", 0) or data.get("total_paid", 0)
            
            # Update business record by player_wallet and slot_index
            update_values = {
                "level": data["new_level"],
                "daily_rate": data["new_daily_rate"], 
                "updated_at": event.block_time or datetime.utcnow()
            }
            
            # Add upgrade cost to total_invested_amount if provided
            if upgrade_cost > 0:
                update_values["total_invested_amount"] = Business.total_invested_amount + upgrade_cost
            
            await db.execute(
                update(Business)
                .where(
                    (Business.player_wallet == player_wallet) &
                    (Business.slot_index == slot_index) &
                    (Business.is_active == True)
                )
                .values(**update_values)
            )
            
            self.stats.businesses_upgraded += 1
            
            # 🔧 UPDATE PLAYER TOTAL_INVESTED FOR UPGRADE
            upgrade_cost = data.get("upgrade_cost", 0) or data.get("total_paid", 0)
            if upgrade_cost > 0:
                await db.execute(
                    update(Player)
                    .where(Player.wallet == player_wallet)
                    .values(
                        total_invested=Player.total_invested + upgrade_cost,
                        updated_at=event.block_time or datetime.utcnow()
                    )
                )
                
                self.logger.info(
                    "Updated player total_invested for upgrade", 
                    wallet=player_wallet,
                    upgrade_cost=upgrade_cost,
                    signature=event.signature
                )
            
            # Award prestige points for business upgrade
            try:
                prestige_service = PrestigeService(db)
                # Calculate upgrade cost (simplified estimation based on level difference)
                business_type = data.get("business_type", 0)  # Get from event if available
                level_diff = data["new_level"] - data["old_level"]
                estimated_upgrade_cost = level_diff * 100000000  # Rough estimate in lamports
                
                points_awarded, level_up = await prestige_service.award_business_upgrade_points(
                    player_wallet=player_wallet,
                    upgrade_cost=estimated_upgrade_cost,
                    business_type=business_type,
                    new_level=data["new_level"],
                    slot_index=slot_index,
                    transaction_signature=event.signature
                )
                
                if points_awarded > 0:
                    self.logger.info(
                        "Prestige points awarded for business upgrade",
                        wallet=player_wallet,
                        points=points_awarded,
                        level_up=level_up
                    )
            except Exception as prestige_error:
                self.logger.error(
                    "Failed to award prestige points for business upgrade",
                    wallet=player_wallet,
                    error=str(prestige_error)
                )
                # Don't fail the upgrade if prestige fails
            
            # Award prestige to referrers for referral business activity
            try:
                referral_service = ReferralService(db)
                # Get all referrers who referred this player
                referrers = await referral_service.get_referrers(player_wallet)
                
                for referrer in referrers:
                    # Award prestige points to referrer for referral business activity
                    referrer_points, referrer_level_up = await prestige_service.calculate_and_award_points(
                        player_wallet=referrer["referrer_id"],
                        action_type=ActionType.REFERRAL_BUSINESS_ACTIVITY,
                        action_value=estimated_upgrade_cost,
                        action_metadata={
                            "referee_wallet": player_wallet,
                            "business_upgrade": True,
                            "old_level": data["old_level"],
                            "new_level": data["new_level"],
                            "referral_level": referrer["level"]
                        },
                        related_transaction=event.signature
                    )
                    
                    if referrer_points > 0:
                        self.logger.info(
                            "Prestige points awarded to referrer for business upgrade activity",
                            referrer=referrer["referrer_id"],
                            referee=player_wallet,
                            points=referrer_points,
                            level_up=referrer_level_up,
                            referral_level=referrer["level"]
                        )
                
                # Send WebSocket notifications to referrers about business upgrade activity
                try:
                    for referrer in referrers:
                        # Notify referrer about business upgrade activity
                        await notification_service.notify_referral_business_activity(
                            referrer_wallet=referrer["referrer_id"],
                            activity_data={
                                "referee_wallet": player_wallet,
                                "activity_type": "business_upgrade",
                                "business_type": data.get("business_type", 0),
                                "amount": estimated_upgrade_cost,
                                "level": referrer["level"],
                                "slot_index": slot_index,
                                "old_level": data["old_level"],
                                "new_level": data["new_level"],
                                "prestige_awarded": referrer_points if 'referrer_points' in locals() else 0,
                                "transaction_signature": event.signature
                            }
                        )
                        
                        # If referrer leveled up, send prestige notification
                        if 'referrer_level_up' in locals() and referrer_level_up:
                            await notification_service.notify_prestige_level_up(
                                wallet=referrer["referrer_id"],
                                prestige_data={
                                    "points_awarded": referrer_points,
                                    "reason": f"Referral business upgrade by {player_wallet[:8]}...{player_wallet[-4:]}",
                                    "referral_related": True,
                                    "referee_wallet": player_wallet,
                                    "activity_type": "business_upgrade"
                                }
                            )
                    
                    self.logger.info(
                        "✅ WebSocket notifications sent to referrers for business upgrade",
                        referee=player_wallet,
                        referrer_count=len(referrers),
                        old_level=data["old_level"],
                        new_level=data["new_level"]
                    )
                    
                except Exception as notification_error:
                    self.logger.error(
                        "Failed to send WebSocket notifications to referrers for business upgrade",
                        referee=player_wallet,
                        error=str(notification_error)
                    )
                    
            except Exception as referrer_prestige_error:
                self.logger.error(
                    "Failed to award prestige to referrers for business upgrade activity",
                    wallet=player_wallet,
                    error=str(referrer_prestige_error)
                )
                # Don't fail the upgrade if referrer prestige fails
            
            self.logger.info(
                "Business upgraded",
                player=player_wallet,
                slot_index=slot_index,
                old_level=data["old_level"],
                new_level=data["new_level"]
            )
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessUpgraded event", error=str(e))
            raise
            
    async def handle_business_upgraded_in_slot(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessUpgradedInSlot event."""
        try:
            data = event.data
            player_wallet = data["player"]
            slot_index = data["slot_index"]
            
            # Get upgrade cost to add to total_invested_amount
            upgrade_cost = data.get("upgrade_cost", 0) or data.get("total_paid", 0)
            
            # Update business record by player_wallet and slot_index
            update_values = {
                "level": data["new_level"],
                "daily_rate": data["new_daily_rate"], 
                "updated_at": event.block_time or datetime.utcnow()
            }
            
            # Add upgrade cost to total_invested_amount if provided
            if upgrade_cost > 0:
                update_values["total_invested_amount"] = Business.total_invested_amount + upgrade_cost
            
            await db.execute(
                update(Business)
                .where(
                    (Business.player_wallet == player_wallet) &
                    (Business.slot_index == slot_index) &
                    (Business.is_active == True)
                )
                .values(**update_values)
            )
            
            self.stats.businesses_upgraded += 1
            
            # 🔧 UPDATE PLAYER TOTAL_INVESTED FOR UPGRADE IN SLOT
            upgrade_cost = data.get("upgrade_cost", 0) or data.get("total_paid", 0)
            if upgrade_cost > 0:
                await db.execute(
                    update(Player)
                    .where(Player.wallet == player_wallet)
                    .values(
                        total_invested=Player.total_invested + upgrade_cost,
                        updated_at=event.block_time or datetime.utcnow()
                    )
                )
                
                self.logger.info(
                    "Updated player total_invested for upgrade in slot",
                    wallet=player_wallet,
                    upgrade_cost=upgrade_cost,
                    signature=event.signature
                )
            
            # Award prestige points for business upgrade
            try:
                prestige_service = PrestigeService(db)
                # Calculate upgrade cost (simplified estimation based on level difference)
                business_type = data.get("business_type", 0)  # Get from event if available
                level_diff = data["new_level"] - data["old_level"]
                estimated_upgrade_cost = level_diff * 100000000  # Rough estimate in lamports
                
                points_awarded, level_up = await prestige_service.award_business_upgrade_points(
                    player_wallet=player_wallet,
                    upgrade_cost=estimated_upgrade_cost,
                    business_type=business_type,
                    new_level=data["new_level"],
                    slot_index=slot_index,
                    transaction_signature=event.signature
                )
                
                if points_awarded > 0:
                    self.logger.info(
                        "Prestige points awarded for business upgrade in slot",
                        wallet=player_wallet,
                        points=points_awarded,
                        level_up=level_up
                    )
            except Exception as prestige_error:
                self.logger.error(
                    "Failed to award prestige points for business upgrade in slot",
                    wallet=player_wallet,
                    error=str(prestige_error)
                )
                # Don't fail the upgrade if prestige fails
            
            self.logger.info(
                "Business upgraded in slot",
                player=player_wallet,
                slot_index=slot_index,
                old_level=data["old_level"],
                new_level=data["new_level"]
            )
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessUpgradedInSlot event", error=str(e))
            raise
            
    async def handle_business_sold(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessSold event."""
        try:
            data = event.data
            player_wallet = data["seller"]
            slot_index = data.get("slot_index", 0)
            
            # Deactivate business by player_wallet and slot_index
            await db.execute(
                update(Business)
                .where(
                    (Business.player_wallet == player_wallet) &
                    (Business.slot_index == slot_index) &
                    (Business.is_active == True)
                )
                .values(
                    is_active=False,
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            self.stats.businesses_sold += 1
            
            self.logger.info(
                "Business sold",
                player=player_wallet,
                slot_index=slot_index,
                sale_price=data["sale_price"]
            )
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessSold event", error=str(e))
            raise
            
    async def handle_business_sold_from_slot(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessSoldFromSlot event."""
        try:
            data = event.data
            
            # Find business by player wallet and slot index (since business_id is synthetic)
            player_wallet = data["player"]
            slot_index = data["slot_index"]
            
            self.logger.info(
                "Processing BusinessSoldFromSlot event",
                player=player_wallet,
                slot_index=slot_index,
                return_amount=data.get("return_amount", 0)
            )
            
            # Deactivate business by finding it via player_wallet + slot_index
            result = await db.execute(
                update(Business)
                .where(
                    (Business.player_wallet == player_wallet) & 
                    (Business.slot_index == slot_index) & 
                    (Business.is_active == True)
                )
                .values(
                    is_active=False,
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            rows_updated = result.rowcount
            
            if rows_updated > 0:
                self.stats.businesses_sold += 1
                self.logger.info(
                    "Business sold from slot - DEACTIVATED",
                    player=player_wallet,
                    slot_index=slot_index,
                    rows_updated=rows_updated,
                    return_amount=data.get("return_amount", 0)
                )
            else:
                self.logger.warning(
                    "Business sold from slot - NO BUSINESS FOUND TO DEACTIVATE",
                    player=player_wallet,
                    slot_index=slot_index
                )
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessSoldFromSlot event", error=str(e))
            raise
            
    async def handle_business_transferred(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessTransferred event."""
        try:
            data = event.data
            old_owner = data["old_owner"]
            new_owner = data["new_owner"]
            slot_index = data.get("slot_index", 0)
            
            # 🔧 ИСПРАВЛЕНИЕ: Найти или создать нового пользователя
            new_user = await self._get_or_create_user(db, new_owner)
            
            # Update business owner by old_owner and slot_index
            await db.execute(
                update(Business)
                .where(
                    (Business.player_wallet == old_owner) &
                    (Business.slot_index == slot_index) &
                    (Business.is_active == True)
                )
                .values(
                    player_wallet=new_owner,
                    owner_id=new_user.id,  # 🔧 ИСПРАВЛЕНИЕ: Используем user.id
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            self.logger.info(
                "Business transferred",
                slot_index=slot_index,
                old_owner=old_owner,
                new_owner=new_owner
            )
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessTransferred event", error=str(e))
            raise
            
    async def handle_business_deactivated(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessDeactivated event."""
        try:
            data = event.data
            player_wallet = data["owner"]
            slot_index = data.get("slot_index", 0)
            
            # Deactivate business by player_wallet and slot_index
            await db.execute(
                update(Business)
                .where(
                    (Business.player_wallet == player_wallet) &
                    (Business.slot_index == slot_index) &
                    (Business.is_active == True)
                )
                .values(
                    is_active=False,
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            self.logger.info("Business deactivated", player=player_wallet, slot_index=slot_index)
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessDeactivated event", error=str(e))
            raise
    
    async def _get_or_create_user(self, db: AsyncSession, wallet_address: str) -> User:
        """Find or create user for wallet address using referral service."""
        # Find existing user first
        user_result = await db.execute(
            select(User).where(User.id == wallet_address)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            # Use referral service to create user with referral code
            referral_service = ReferralService(db)
            user = await referral_service.get_or_create_user(
                user_id=wallet_address,
                user_type=UserType.WALLET,
                wallet_address=wallet_address
            )
            self.logger.info(
                "Created wallet user with referral code", 
                wallet=wallet_address,
                referral_code=user.referral_code
            )
        else:
            # Ensure existing user has referral code
            if not user.referral_code:
                referral_service = ReferralService(db)
                user.referral_code = await referral_service._generate_unique_referral_code()
                self.logger.info(
                    "Added referral code to existing user",
                    wallet=wallet_address,
                    referral_code=user.referral_code
                )
            
        return user
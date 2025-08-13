"""
Event handlers for player-related events.
"""

from datetime import datetime

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.event_parser import ParsedEvent
from app.models.player import Player


logger = structlog.get_logger(__name__)


class PlayerHandlers:
    """
    Handles player-related blockchain events.
    """
    
    def __init__(self, stats):
        """Initialize player handlers."""
        self.stats = stats
        self.logger = logger.bind(service="player_handlers")
        
    async def handle_player_created(self, db: AsyncSession, event: ParsedEvent):
        """Handle PlayerCreated event."""
        try:
            data = event.data
            
            # Check if player already exists
            result = await db.execute(
                select(Player).where(Player.wallet == data["wallet"])
            )
            existing_player = result.scalar_one_or_none()
            
            if existing_player:
                self.logger.debug("Player already exists", wallet=data["wallet"])
                return
                
            # Create new player
            player = Player(
                wallet=data["wallet"],
                referrer_wallet=data.get("referrer"),
                unlocked_slots_count=data.get("slots_unlocked", 3),  # Fixed field name
                total_invested=0,
                total_earned=0,
                pending_earnings=0,  # Fixed field name
                has_paid_entry=True,  # ✅ КЛЮЧЕВОЕ ИСПРАВЛЕНИЕ - игрок заплатил entry fee
                is_active=True,
                last_earnings_update=event.block_time or datetime.utcnow(),
                on_chain_created_at=event.block_time or datetime.utcnow(),
                created_at=event.block_time or datetime.utcnow(),
                updated_at=event.block_time or datetime.utcnow()
            )
            
            db.add(player)
            self.stats.players_created += 1
            
            # Note: No earnings schedule needed in permissionless architecture
            
            self.logger.info("Player created", wallet=data["wallet"])
            
        except Exception as e:
            self.logger.error("Failed to handle PlayerCreated event", error=str(e))
            raise
            
    async def handle_slot_unlocked(self, db: AsyncSession, event: ParsedEvent):
        """Handle SlotUnlocked event."""
        try:
            data = event.data
            
            # Update player slots
            await db.execute(
                update(Player)
                .where(Player.wallet == data["wallet"])
                .values(
                    unlocked_slots_count=Player.unlocked_slots_count + 1,  # Fixed field name
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            self.logger.info(
                "Slot unlocked",
                wallet=data["wallet"],
                slot_index=data["slot_index"]
            )
            
        except Exception as e:
            self.logger.error("Failed to handle SlotUnlocked event", error=str(e))
            raise
            
    async def handle_premium_slot_purchased(self, db: AsyncSession, event: ParsedEvent):
        """Handle PremiumSlotPurchased event."""
        try:
            data = event.data
            
            # Update player premium slots
            await db.execute(
                update(Player)
                .where(Player.wallet == data["wallet"])
                .values(
                    premium_slots_count=Player.premium_slots_count + 1,  # Fixed to use premium slots
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            self.logger.info(
                "Premium slot purchased",
                wallet=data["wallet"],
                slot_index=data["slot_index"],
                cost=data["cost"]
            )
            
        except Exception as e:
            self.logger.error("Failed to handle PremiumSlotPurchased event", error=str(e))
            raise
"""
Transaction and event processing utilities.
"""

from datetime import datetime
from typing import Dict, Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.event_parser import EventType, ParsedEvent
from app.models.event import Event


logger = structlog.get_logger(__name__)


class TransactionProcessor:
    """
    Processes individual transactions and events.
    """
    
    def __init__(self, indexer):
        """Initialize the transaction processor."""
        self.indexer = indexer
        self.logger = logger.bind(service="transaction_processor")
        
    async def handle_event(self, db: AsyncSession, event_record: Event):
        """Handle a single event record."""
        try:
            # Convert event record to parsed event
            # Map database event type to parser event type
            db_to_parser_mapping = {
                "business_created": "BusinessCreated",
                "business_created_in_slot": "BusinessCreatedInSlot",
                "business_upgraded": "BusinessUpgraded", 
                "business_upgraded_in_slot": "BusinessUpgradedInSlot",
                "business_sold": "BusinessSold",
                "business_sold_from_slot": "BusinessSoldFromSlot",
                "player_created": "PlayerCreated",
                "earnings_updated": "EarningsUpdated",
                "earnings_claimed": "EarningsClaimed",
                "slot_unlocked": "SlotUnlocked",
                "premium_slot_purchased": "PremiumSlotPurchased",
            }
            
            parser_event_type_name = db_to_parser_mapping.get(event_record.event_type.value)
            if not parser_event_type_name:
                self.logger.warning(
                    "Unknown database event type",
                    db_event_type=event_record.event_type.value,
                    signature=event_record.transaction_signature
                )
                return
            
            event_type = EventType(parser_event_type_name)
            parsed_event = ParsedEvent(
                event_type=event_type,
                signature=event_record.transaction_signature,
                slot=event_record.slot,
                block_time=event_record.block_time,
                data=event_record.parsed_data or {},
                raw_data=event_record.raw_data or {}
            )
            
            # Get handler for this event type
            handler = self.indexer._event_handlers.get(event_type)
            if handler:
                await handler(db, parsed_event)
                self.indexer.stats.events_processed += 1
                
                # Send WebSocket notification
                try:
                    from app.websocket.notification_service import notification_service
                    await notification_service.process_blockchain_event(event_record)
                except Exception as e:
                    self.logger.warning(
                        "Failed to send WebSocket notification",
                        signature=event_record.transaction_signature,
                        event_type=event_record.event_type,
                        error=str(e)
                    )
                
                self.logger.debug(
                    "Event handled",
                    signature=event_record.transaction_signature,
                    event_type=event_record.event_type
                )
            else:
                self.logger.warning(
                    "No handler for event type",
                    event_type=event_record.event_type,
                    signature=event_record.transaction_signature
                )
                
        except Exception as e:
            self.logger.error(
                "Event handling failed",
                signature=event_record.transaction_signature,
                event_type=event_record.event_type,
                error=str(e)
            )
            raise
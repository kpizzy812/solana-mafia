#!/usr/bin/env python3
"""
Script to force process a specific transaction that was missed by the indexer.
Usage: python force_process_transaction.py <signature>
"""

import asyncio
import sys
import structlog
from datetime import datetime

from app.core.database import get_async_session, init_database
from app.services.solana_client import get_solana_client
from app.services.event_parser import get_event_parser
from app.indexer.handlers.business_handlers import BusinessHandlers
from app.indexer.handlers.earnings_handlers import EarningsHandlers
from app.indexer.core.types import ProcessingStats

logger = structlog.get_logger(__name__)


async def force_process_transaction(signature: str):
    """Force process a specific transaction by signature."""
    try:
        logger.info("🔧 Force processing transaction", signature=signature)
        
        # Initialize database
        await init_database()
        logger.info("✅ Database initialized")
        
        # Get services
        solana_client = await get_solana_client()
        event_parser = get_event_parser()
        
        # Initialize handlers with stats
        stats = ProcessingStats()
        business_handlers = BusinessHandlers(stats)
        earnings_handlers = EarningsHandlers(stats)
        
        # Event handler mappings
        event_handlers = {
            "BusinessCreatedInSlot": business_handlers.handle_business_created_in_slot,
            "BusinessSoldFromSlot": business_handlers.handle_business_sold_from_slot,
            "BusinessUpgradedInSlot": business_handlers.handle_business_upgraded_in_slot,
            "EarningsUpdated": earnings_handlers.handle_earnings_updated,
            # Also support enum values
            "BUSINESS_CREATED_IN_SLOT": business_handlers.handle_business_created_in_slot,
            "BUSINESS_SOLD_FROM_SLOT": business_handlers.handle_business_sold_from_slot,
            "BUSINESS_UPGRADED_IN_SLOT": business_handlers.handle_business_upgraded_in_slot,
            "EARNINGS_UPDATED": earnings_handlers.handle_earnings_updated,
        }
        
        # Get transaction from blockchain
        logger.info("📡 Fetching transaction from blockchain", signature=signature)
        
        tx_info = await solana_client.get_transaction(signature)
        if not tx_info:
            logger.error("❌ Transaction not found", signature=signature)
            return False
            
        logger.info("✅ Transaction found", 
                   signature=signature, 
                   slot=tx_info.slot,
                   block_time=tx_info.block_time)
        
        # Parse events from transaction
        logger.info("🔍 Parsing events from transaction")
        events = event_parser.parse_transaction_events(tx_info)
        
        if not events:
            logger.warning("⚠️ No events found in transaction", signature=signature)
            return True  # Not an error, just no events
            
        logger.info("🎯 Found events", 
                   signature=signature,
                   event_count=len(events),
                   event_types=[e.event_type.value for e in events])
        
        # Process each event
        async with get_async_session() as db:
            # 🆕 ИСПРАВЛЕНИЕ: Сначала сохраняем события в таблицу events
            db_events = []
            for event in events:
                try:
                    # Create Event record for database
                    from app.models.event import Event, EventType, EventStatus
                    
                    # Map event type string to EventType enum
                    event_type_map = {
                        "EarningsUpdated": EventType.EARNINGS_UPDATED,
                        "EARNINGS_UPDATED": EventType.EARNINGS_UPDATED,
                        "BusinessCreatedInSlot": EventType.BUSINESS_CREATED_IN_SLOT,
                        "BUSINESS_CREATED_IN_SLOT": EventType.BUSINESS_CREATED_IN_SLOT,
                        "BusinessSoldFromSlot": EventType.BUSINESS_SOLD_FROM_SLOT,
                        "BUSINESS_SOLD_FROM_SLOT": EventType.BUSINESS_SOLD_FROM_SLOT,
                        "BusinessUpgradedInSlot": EventType.BUSINESS_UPGRADED_IN_SLOT,
                        "BUSINESS_UPGRADED_IN_SLOT": EventType.BUSINESS_UPGRADED_IN_SLOT,
                    }
                    
                    event_type_enum = event_type_map.get(event.event_type.value)
                    if not event_type_enum:
                        logger.warning(f"⚠️ Unknown event type for DB save: {event.event_type.value}")
                        continue
                    
                    # Extract player wallet from event data
                    player_wallet = None
                    if hasattr(event, 'data') and event.data:
                        player_wallet = event.data.get('player') or event.data.get('owner')
                    
                    db_event = Event(
                        event_type=event_type_enum,
                        transaction_signature=event.signature,
                        instruction_index=event.instruction_index if hasattr(event, 'instruction_index') else 0,
                        event_index=0,  # Force process doesn't have log index
                        slot=event.slot,
                        block_time=event.block_time,
                        raw_data=event.raw_data if hasattr(event, 'raw_data') else {},
                        parsed_data=event.data,
                        player_wallet=player_wallet,
                        status=EventStatus.PROCESSED,
                        processed_at=datetime.utcnow(),
                        indexer_version="force_process_1.0"
                    )
                    
                    db.add(db_event)
                    db_events.append(db_event)
                    
                    logger.info("💾 Event saved to database", 
                               event_type=event.event_type.value,
                               signature=signature)
                    
                except Exception as e:
                    logger.error("❌ Failed to save event to database", 
                               event_type=event.event_type.value,
                               signature=signature,
                               error=str(e))
                    # Continue processing even if save fails
            
            # Flush to get IDs
            await db.flush()
            
            # Now process events with handlers
            for event in events:
                try:
                    logger.info("🏃‍♂️ Processing event", 
                               event_type=event.event_type.value,
                               signature=signature)
                    
                    # Get handler for this event type
                    handler = event_handlers.get(event.event_type.value)
                    if not handler:
                        logger.warning("⚠️ No handler for event type", 
                                     event_type=event.event_type.value)
                        continue
                        
                    # Process event
                    await handler(db, event)
                    
                    logger.info("✅ Event processed successfully",
                               event_type=event.event_type.value,
                               signature=signature)
                    
                except Exception as e:
                    logger.error("❌ Failed to process event",
                               event_type=event.event_type.value,
                               signature=signature,
                               error=str(e))
                    raise
                    
            # Commit all changes
            await db.commit()
            logger.info("💾 All changes committed to database")
            
        logger.info("🎉 Transaction processed successfully", 
                   signature=signature,
                   events_processed=len(events))
        return True
        
    except Exception as e:
        logger.error("💥 Failed to force process transaction",
                    signature=signature,
                    error=str(e))
        raise


async def main():
    """Main function."""
    if len(sys.argv) != 2:
        print("Usage: python force_process_transaction.py <signature>")
        sys.exit(1)
        
    signature = sys.argv[1]
    
    print(f"🚀 Force processing transaction: {signature}")
    
    try:
        success = await force_process_transaction(signature)
        if success:
            print("✅ Transaction processed successfully!")
        else:
            print("❌ Failed to process transaction")
            sys.exit(1)
    except Exception as e:
        print(f"💥 Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
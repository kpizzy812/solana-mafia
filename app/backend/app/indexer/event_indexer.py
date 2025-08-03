"""
Event indexer service for real-time processing of Solana Mafia program events.
Provides continuous monitoring and processing of blockchain events with database updates.
"""

import asyncio
from typing import Dict, List, Optional, Callable, Any, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_, or_
import structlog

from app.core.database import get_async_session
from app.core.config import settings
from app.core.exceptions import IndexerError, DatabaseError
from app.services.solana_client import SolanaClient, get_solana_client, TransactionInfo
from app.services.event_parser import EventParser, get_event_parser, ParsedEvent, EventType
from app.indexer.transaction_indexer import TransactionIndexer, get_transaction_indexer
from app.models.player import Player
from app.models.business import Business
from app.models.nft import BusinessNFT
from app.models.event import Event
from app.models.earnings import EarningsSchedule


logger = structlog.get_logger(__name__)


class IndexerStatus(Enum):
    """Status of the event indexer."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ProcessingStats:
    """Statistics for event processing."""
    events_processed: int = 0
    players_created: int = 0
    businesses_created: int = 0
    businesses_upgraded: int = 0
    businesses_sold: int = 0
    earnings_updated: int = 0
    earnings_claimed: int = 0
    nfts_minted: int = 0
    nfts_burned: int = 0
    errors: int = 0
    last_processed_slot: Optional[int] = None
    start_time: Optional[datetime] = None


class EventIndexer:
    """
    Real-time event indexer for Solana Mafia program.
    
    Features:
    - Continuous monitoring of blockchain events
    - Real-time database updates
    - Event-driven processing with retry logic
    - Comprehensive error handling and recovery
    - Statistics and monitoring
    """
    
    def __init__(self):
        """Initialize the event indexer."""
        self.logger = logger.bind(service="event_indexer")
        self.status = IndexerStatus.STOPPED
        self.stats = ProcessingStats()
        
        # Services
        self.solana_client: Optional[SolanaClient] = None
        self.event_parser: Optional[EventParser] = None
        self.transaction_indexer: Optional[TransactionIndexer] = None
        
        # Control flags
        self._running = False
        self._should_stop = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Event handlers
        self._event_handlers: Dict[EventType, Callable] = {}
        self._setup_event_handlers()
        
    def _setup_event_handlers(self):
        """Setup event type to handler mappings."""
        self._event_handlers = {
            EventType.PLAYER_CREATED: self._handle_player_created,
            EventType.BUSINESS_CREATED: self._handle_business_created,
            EventType.BUSINESS_UPGRADED: self._handle_business_upgraded,
            EventType.BUSINESS_SOLD: self._handle_business_sold,
            EventType.EARNINGS_UPDATED: self._handle_earnings_updated,
            EventType.EARNINGS_CLAIMED: self._handle_earnings_claimed,
            EventType.BUSINESS_NFT_MINTED: self._handle_nft_minted,
            EventType.BUSINESS_NFT_BURNED: self._handle_nft_burned,
            EventType.BUSINESS_NFT_UPGRADED: self._handle_nft_upgraded,
            EventType.BUSINESS_TRANSFERRED: self._handle_business_transferred,
            EventType.BUSINESS_DEACTIVATED: self._handle_business_deactivated,
            EventType.SLOT_UNLOCKED: self._handle_slot_unlocked,
            EventType.PREMIUM_SLOT_PURCHASED: self._handle_premium_slot_purchased,
        }
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
        
    async def initialize(self):
        """Initialize the indexer and all dependencies."""
        try:
            self.status = IndexerStatus.STARTING
            self.logger.info("Initializing event indexer")
            
            # Initialize services
            self.solana_client = await get_solana_client()
            self.event_parser = get_event_parser()
            self.transaction_indexer = await get_transaction_indexer()
            
            self.stats.start_time = datetime.utcnow()
            self.status = IndexerStatus.STOPPED
            
            self.logger.info("Event indexer initialized successfully")
            
        except Exception as e:
            self.status = IndexerStatus.ERROR
            self.logger.error("Failed to initialize event indexer", error=str(e))
            raise IndexerError(f"Failed to initialize event indexer: {e}")
            
    async def start(self):
        """Start the real-time event indexing."""
        if self.status == IndexerStatus.RUNNING:
            self.logger.warning("Event indexer already running")
            return
            
        try:
            self.status = IndexerStatus.STARTING
            self._should_stop = False
            self._running = True
            
            self.logger.info("Starting event indexer")
            
            # Start monitoring task
            self._monitor_task = asyncio.create_task(self._monitor_events())
            
            self.status = IndexerStatus.RUNNING
            self.logger.info("Event indexer started successfully")
            
        except Exception as e:
            self.status = IndexerStatus.ERROR
            self._running = False
            self.logger.error("Failed to start event indexer", error=str(e))
            raise IndexerError(f"Failed to start event indexer: {e}")
            
    async def stop(self):
        """Stop the event indexer."""
        if self.status == IndexerStatus.STOPPED:
            return
            
        try:
            self.status = IndexerStatus.STOPPING
            self.logger.info("Stopping event indexer")
            
            self._should_stop = True
            self._running = False
            
            # Cancel monitoring task
            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
                    
            self.status = IndexerStatus.STOPPED
            self.logger.info("Event indexer stopped")
            
        except Exception as e:
            self.status = IndexerStatus.ERROR
            self.logger.error("Error stopping event indexer", error=str(e))
            
    async def shutdown(self):
        """Shutdown the indexer completely."""
        await self.stop()
        
        if self.solana_client:
            await self.solana_client.close()
            
        self.logger.info("Event indexer shutdown complete")
        
    async def _monitor_events(self):
        """Main monitoring loop for real-time event processing."""
        self.logger.info("Starting event monitoring")
        
        last_processed_slot = 0
        if self.transaction_indexer.checkpoint:
            last_processed_slot = self.transaction_indexer.checkpoint.last_processed_slot
            
        retry_count = 0
        max_retries = settings.indexer_max_retries
        
        while not self._should_stop:
            try:
                # Get current slot
                current_slot = await self.solana_client.get_slot()
                
                # Process new transactions since last checkpoint
                if current_slot > last_processed_slot:
                    await self._process_new_transactions(last_processed_slot + 1, current_slot)
                    last_processed_slot = current_slot
                    self.stats.last_processed_slot = current_slot
                    retry_count = 0  # Reset retry count on success
                    
                # Wait before next poll
                await asyncio.sleep(settings.indexer_poll_interval)
                
            except asyncio.CancelledError:
                self.logger.info("Event monitoring cancelled")
                break
                
            except Exception as e:
                retry_count += 1
                self.stats.errors += 1
                
                self.logger.error(
                    "Error in event monitoring",
                    error=str(e),
                    retry_count=retry_count,
                    max_retries=max_retries
                )
                
                if retry_count >= max_retries:
                    self.status = IndexerStatus.ERROR
                    self.logger.error("Max retries exceeded, stopping indexer")
                    break
                    
                # Exponential backoff
                wait_time = min(settings.indexer_retry_delay * (2 ** retry_count), 300)
                await asyncio.sleep(wait_time)
                
        self.logger.info("Event monitoring stopped")
        
    async def _process_new_transactions(self, start_slot: int, end_slot: int):
        """Process new transactions in the given slot range."""
        try:
            self.logger.debug(
                "Processing new transactions",
                start_slot=start_slot,
                end_slot=end_slot
            )
            
            # Use transaction indexer to get and process transactions
            batch_stats = await self.transaction_indexer.index_transactions_batch(
                start_slot=start_slot,
                end_slot=end_slot,
                limit=settings.indexer_batch_size
            )
            
            # Process any new events that were stored
            await self._process_recent_events()
            
            self.logger.debug(
                "Processed transaction batch",
                transactions=batch_stats.transactions_processed,
                events=batch_stats.events_stored
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to process new transactions",
                start_slot=start_slot,
                end_slot=end_slot,
                error=str(e)
            )
            raise
            
    async def _process_recent_events(self):
        """Process recently stored events that haven't been handled yet."""
        try:
            async with get_async_session() as db:
                # Get unprocessed events (events without corresponding database updates)
                # For now, we'll process all recent events
                recent_cutoff = datetime.utcnow() - timedelta(minutes=5)
                
                result = await db.execute(
                    select(Event)
                    .where(Event.processed_at >= recent_cutoff)
                    .order_by(Event.slot, Event.processed_at)
                )
                
                recent_events = result.scalars().all()
                
                for event_record in recent_events:
                    try:
                        await self._handle_event(db, event_record)
                    except Exception as e:
                        self.logger.error(
                            "Failed to handle event",
                            signature=event_record.signature,
                            event_type=event_record.event_type,
                            error=str(e)
                        )
                        self.stats.errors += 1
                        
                await db.commit()
                
        except Exception as e:
            self.logger.error("Failed to process recent events", error=str(e))
            raise
            
    async def _handle_event(self, db: AsyncSession, event_record: Event):
        """Handle a single event record."""
        try:
            # Convert event record to parsed event
            event_type = EventType(event_record.event_type)
            parsed_event = ParsedEvent(
                event_type=event_type,
                signature=event_record.signature,
                slot=event_record.slot,
                block_time=event_record.block_time,
                data=event_record.event_data,
                raw_data=event_record.raw_data or {}
            )
            
            # Get handler for this event type
            handler = self._event_handlers.get(event_type)
            if handler:
                await handler(db, parsed_event)
                self.stats.events_processed += 1
                
                # Send WebSocket notification
                try:
                    from app.websocket.notification_service import notification_service
                    await notification_service.process_blockchain_event(event_record)
                except Exception as e:
                    self.logger.warning(
                        "Failed to send WebSocket notification",
                        signature=event_record.signature,
                        event_type=event_record.event_type,
                        error=str(e)
                    )
                
                self.logger.debug(
                    "Event handled",
                    signature=event_record.signature,
                    event_type=event_record.event_type
                )
            else:
                self.logger.warning(
                    "No handler for event type",
                    event_type=event_record.event_type,
                    signature=event_record.signature
                )
                
        except Exception as e:
            self.logger.error(
                "Event handling failed",
                signature=event_record.signature,
                event_type=event_record.event_type,
                error=str(e)
            )
            raise
            
    # Event Handlers
    
    async def _handle_player_created(self, db: AsyncSession, event: ParsedEvent):
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
                referrer=data.get("referrer"),
                slots_unlocked=data.get("slots_unlocked", 5),
                total_earnings=0,
                earnings_balance=0,
                last_earnings_update=event.block_time or datetime.utcnow(),
                created_at=event.block_time or datetime.utcnow()
            )
            
            db.add(player)
            self.stats.players_created += 1
            
            # Create initial earnings schedule
            earnings_schedule = EarningsSchedule(
                player_wallet=data["wallet"],
                next_update_time=event.block_time or datetime.utcnow(),
                update_interval=3600,  # 1 hour
                is_active=True
            )
            
            db.add(earnings_schedule)
            
            self.logger.info("Player created", wallet=data["wallet"])
            
        except Exception as e:
            self.logger.error("Failed to handle PlayerCreated event", error=str(e))
            raise
            
    async def _handle_business_created(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessCreated event."""
        try:
            data = event.data
            
            # Create business record
            business = Business(
                business_id=data["business_id"],
                owner=data["owner"],
                business_type=data["business_type"],
                name=data["name"],
                level=1,
                slot_index=data["slot_index"],
                cost=data["cost"],
                earnings_per_hour=data["earnings_per_hour"],
                created_at=event.block_time or datetime.utcnow(),
                is_active=True
            )
            
            db.add(business)
            self.stats.businesses_created += 1
            
            self.logger.info(
                "Business created",
                business_id=data["business_id"],
                owner=data["owner"],
                business_type=data["business_type"]
            )
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessCreated event", error=str(e))
            raise
            
    async def _handle_business_upgraded(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessUpgraded event."""
        try:
            data = event.data
            
            # Update business record
            await db.execute(
                update(Business)
                .where(Business.business_id == data["business_id"])
                .values(
                    level=data["new_level"],
                    earnings_per_hour=data["new_earnings_per_hour"],
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            self.stats.businesses_upgraded += 1
            
            self.logger.info(
                "Business upgraded",
                business_id=data["business_id"],
                old_level=data["old_level"],
                new_level=data["new_level"]
            )
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessUpgraded event", error=str(e))
            raise
            
    async def _handle_business_sold(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessSold event."""
        try:
            data = event.data
            
            # Deactivate business
            await db.execute(
                update(Business)
                .where(Business.business_id == data["business_id"])
                .values(
                    is_active=False,
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            self.stats.businesses_sold += 1
            
            self.logger.info(
                "Business sold",
                business_id=data["business_id"],
                seller=data["seller"],
                sale_price=data["sale_price"]
            )
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessSold event", error=str(e))
            raise
            
    async def _handle_earnings_updated(self, db: AsyncSession, event: ParsedEvent):
        """Handle EarningsUpdated event."""
        try:
            data = event.data
            
            # Update player earnings
            await db.execute(
                update(Player)
                .where(Player.wallet == data["wallet"])
                .values(
                    earnings_balance=data["total_earnings"],
                    last_earnings_update=event.block_time or datetime.utcnow(),
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            self.stats.earnings_updated += 1
            
            self.logger.debug(
                "Earnings updated",
                wallet=data["wallet"],
                amount=data["earnings_amount"]
            )
            
        except Exception as e:
            self.logger.error("Failed to handle EarningsUpdated event", error=str(e))
            raise
            
    async def _handle_earnings_claimed(self, db: AsyncSession, event: ParsedEvent):
        """Handle EarningsClaimed event."""
        try:
            data = event.data
            
            # Update player earnings and total claimed
            await db.execute(
                update(Player)
                .where(Player.wallet == data["wallet"])
                .values(
                    earnings_balance=0,  # Reset after claiming
                    total_earnings=Player.total_earnings + data["net_amount"],
                    last_earnings_update=event.block_time or datetime.utcnow(),
                    updated_at=event.block_time or datetime.utcnow()
                )
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
            
    async def _handle_nft_minted(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessNFTMinted event."""
        try:
            data = event.data
            
            # Create NFT record
            nft = BusinessNFT(
                mint=data["nft_mint"],
                business_id=data["business_id"],
                owner=data["owner"],
                business_type=data["business_type"],
                level=data["level"],
                metadata_uri=data.get("metadata_uri"),
                is_burned=False,
                created_at=event.block_time or datetime.utcnow()
            )
            
            db.add(nft)
            self.stats.nfts_minted += 1
            
            self.logger.info(
                "NFT minted",
                mint=data["nft_mint"],
                business_id=data["business_id"],
                owner=data["owner"]
            )
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessNFTMinted event", error=str(e))
            raise
            
    async def _handle_nft_burned(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessNFTBurned event."""
        try:
            data = event.data
            
            # Mark NFT as burned
            await db.execute(
                update(BusinessNFT)
                .where(BusinessNFT.mint == data["nft_mint"])
                .values(
                    is_burned=True,
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            self.stats.nfts_burned += 1
            
            self.logger.info("NFT burned", mint=data["nft_mint"])
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessNFTBurned event", error=str(e))
            raise
            
    async def _handle_nft_upgraded(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessNFTUpgraded event."""
        try:
            data = event.data
            
            # Update NFT level and metadata
            await db.execute(
                update(BusinessNFT)
                .where(BusinessNFT.mint == data["nft_mint"])
                .values(
                    level=data["level"],
                    metadata_uri=data.get("metadata_uri"),
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            self.logger.info(
                "NFT upgraded",
                mint=data["nft_mint"],
                level=data["level"]
            )
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessNFTUpgraded event", error=str(e))
            raise
            
    async def _handle_business_transferred(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessTransferred event."""
        try:
            data = event.data
            
            # Update business and NFT owner
            await db.execute(
                update(Business)
                .where(Business.business_id == data["business_id"])
                .values(
                    owner=data["new_owner"],
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            await db.execute(
                update(BusinessNFT)
                .where(BusinessNFT.mint == data["nft_mint"])
                .values(
                    owner=data["new_owner"],
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            self.logger.info(
                "Business transferred",
                business_id=data["business_id"],
                old_owner=data["old_owner"],
                new_owner=data["new_owner"]
            )
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessTransferred event", error=str(e))
            raise
            
    async def _handle_business_deactivated(self, db: AsyncSession, event: ParsedEvent):
        """Handle BusinessDeactivated event."""
        try:
            data = event.data
            
            # Deactivate business
            await db.execute(
                update(Business)
                .where(Business.business_id == data["business_id"])
                .values(
                    is_active=False,
                    updated_at=event.block_time or datetime.utcnow()
                )
            )
            
            self.logger.info("Business deactivated", business_id=data["business_id"])
            
        except Exception as e:
            self.logger.error("Failed to handle BusinessDeactivated event", error=str(e))
            raise
            
    async def _handle_slot_unlocked(self, db: AsyncSession, event: ParsedEvent):
        """Handle SlotUnlocked event."""
        try:
            data = event.data
            
            # Update player slots
            await db.execute(
                update(Player)
                .where(Player.wallet == data["wallet"])
                .values(
                    slots_unlocked=Player.slots_unlocked + 1,
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
            
    async def _handle_premium_slot_purchased(self, db: AsyncSession, event: ParsedEvent):
        """Handle PremiumSlotPurchased event."""
        try:
            data = event.data
            
            # Update player premium slots
            await db.execute(
                update(Player)
                .where(Player.wallet == data["wallet"])
                .values(
                    slots_unlocked=Player.slots_unlocked + 1,
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
            
    async def get_status(self) -> Dict[str, Any]:
        """Get current indexer status and statistics."""
        return {
            "status": self.status.value,
            "running": self._running,
            "stats": asdict(self.stats),
            "uptime": (
                datetime.utcnow() - self.stats.start_time
                if self.stats.start_time else None
            )
        }


# Global indexer instance
_event_indexer: Optional[EventIndexer] = None


async def get_event_indexer() -> EventIndexer:
    """Get or create a global event indexer instance."""
    global _event_indexer
    if _event_indexer is None:
        _event_indexer = EventIndexer()
        await _event_indexer.initialize()
    return _event_indexer


async def shutdown_event_indexer():
    """Shutdown the global event indexer instance."""
    global _event_indexer
    if _event_indexer:
        await _event_indexer.shutdown()
        _event_indexer = None
"""
Transaction indexer service for processing Solana blockchain transactions.
Provides basic transaction indexing functionality that can be used by the event indexer.
"""

import asyncio
from typing import Dict, List, Optional, Set, Callable, Any
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, asdict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, and_
import structlog

from app.core.database import get_async_session
from app.core.config import settings
from app.core.exceptions import IndexerError, ValidationError
from app.services.solana_client import SolanaClient, get_solana_client, TransactionInfo
from app.services.event_parser import EventParser, get_event_parser, ParsedEvent
from app.utils.validation import TransactionValidator, validate_event_data
from app.models.event import Event


logger = structlog.get_logger(__name__)


@dataclass
class IndexerCheckpoint:
    """Checkpoint for tracking indexer progress."""
    last_processed_slot: int
    last_processed_signature: str
    last_update: datetime
    processed_count: int
    error_count: int


@dataclass
class IndexingStats:
    """Statistics for indexing operations."""
    transactions_processed: int = 0
    events_found: int = 0
    events_stored: int = 0
    errors_encountered: int = 0
    start_time: Optional[datetime] = None
    last_processed_slot: Optional[int] = None


class TransactionIndexer:
    """
    Service for indexing Solana transactions and extracting events.
    
    Provides functionality to:
    - Index transactions from a specific slot range
    - Extract and validate events from transactions
    - Store processed data with checkpointing
    - Handle retries and error recovery
    """
    
    def __init__(self):
        """Initialize the transaction indexer."""
        self.logger = logger.bind(service="transaction_indexer")
        self.solana_client: Optional[SolanaClient] = None
        self.event_parser: Optional[EventParser] = None
        self.stats = IndexingStats()
        self.checkpoint: Optional[IndexerCheckpoint] = None
        self._running = False
        self._should_stop = False
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
        
    async def initialize(self):
        """Initialize the indexer components."""
        try:
            self.solana_client = await get_solana_client()
            self.event_parser = get_event_parser()
            self.stats.start_time = datetime.utcnow()
            
            # Load last checkpoint from database
            await self._load_checkpoint()
            
            self.logger.info("Transaction indexer initialized", checkpoint=self.checkpoint)
            
        except Exception as e:
            self.logger.error("Failed to initialize indexer", error=str(e))
            raise IndexerError(f"Failed to initialize indexer: {e}")
            
    async def shutdown(self):
        """Shutdown the indexer."""
        self._should_stop = True
        if self.solana_client:
            await self.solana_client.close()
        self.logger.info("Transaction indexer shutdown")
        
    async def index_transactions_batch(
        self,
        start_slot: int,
        end_slot: Optional[int] = None,
        limit: int = 1000
    ) -> IndexingStats:
        """
        Index a batch of transactions between slots.
        
        Args:
            start_slot: Starting slot number
            end_slot: Ending slot number (optional)
            limit: Maximum number of transactions to process
            
        Returns:
            Indexing statistics
            
        Raises:
            IndexerError: If indexing fails
        """
        try:
            if not self.solana_client:
                raise IndexerError("Indexer not initialized")
                
            batch_stats = IndexingStats(start_time=datetime.utcnow())
            
            self.logger.info(
                "Starting batch indexing",
                start_slot=start_slot,
                end_slot=end_slot,
                limit=limit
            )
            
            # Get signatures for our program
            signatures = await self.solana_client.get_signatures_for_address(
                settings.solana_program_id,
                limit=limit
            )
            
            # Filter signatures by slot range
            filtered_signatures = []
            self.logger.info(f"🔍 Filtering slots - Range: {start_slot} to {end_slot}")
            for sig_info in signatures:
                slot = sig_info["slot"]
                signature = sig_info["signature"]
                is_in_range = slot >= start_slot and (end_slot is None or slot <= end_slot)
                
                self.logger.info(f"📍 Checking slot {slot}: in_range={is_in_range}")
                
                if is_in_range:
                    filtered_signatures.append(sig_info)
                    self.logger.info(f"✅ Slot {slot} included (signature: {signature[:20]}...)")
                    
            self.logger.info(
                "Found signatures in range",
                total_signatures=len(signatures),
                filtered_signatures=len(filtered_signatures)
            )
            
            # Process each transaction
            async with get_async_session() as db:
                for sig_info in filtered_signatures:
                    if self._should_stop:
                        break
                        
                    try:
                        await self._process_transaction(
                            db,
                            sig_info["signature"],
                            batch_stats
                        )
                        
                        # Update checkpoint periodically
                        if batch_stats.transactions_processed % 100 == 0:
                            await self._save_checkpoint(db, sig_info["slot"], sig_info["signature"])
                            
                    except Exception as e:
                        batch_stats.errors_encountered += 1
                        self.logger.error(
                            "Failed to process transaction",
                            signature=sig_info["signature"],
                            error=str(e)
                        )
                        
                # Final checkpoint save
                if filtered_signatures:
                    last_sig = filtered_signatures[-1]
                    await self._save_checkpoint(db, last_sig["slot"], last_sig["signature"])
                    
            self.logger.info("Batch indexing completed", stats=asdict(batch_stats))
            return batch_stats
            
        except Exception as e:
            self.logger.error("Batch indexing failed", error=str(e))
            raise IndexerError(f"Batch indexing failed: {e}")
            
    async def _process_transaction(
        self,
        db: AsyncSession,
        signature: str,
        stats: IndexingStats
    ):
        """Process a single transaction."""
        try:
            self.logger.info(f"🔄 Processing transaction: {signature[:20]}...")
            
            # Check if already processed
            existing_events = await db.execute(
                select(Event).where(Event.transaction_signature == signature)
            )
            if existing_events.first():
                self.logger.debug("Transaction already processed", signature=signature)
                return
                
            self.logger.info(f"📡 Getting transaction from RPC: {signature[:20]}...")
            # Get transaction details
            tx_info = await self.solana_client.get_transaction(signature)
            if not tx_info:
                self.logger.warning(f"❌ Transaction not found on RPC: {signature[:20]}...")
                return
                
            self.logger.info(f"✅ Transaction retrieved successfully: {signature[:20]}...")
                
            stats.transactions_processed += 1
            
            self.logger.info(f"🔍 Validating transaction: {signature[:20]}...")
            # Validate transaction
            if not self._validate_transaction(tx_info):
                self.logger.warning(f"❌ Transaction validation failed: {signature[:20]}...")
                return
                
            self.logger.info(f"✅ Transaction validation passed: {signature[:20]}...")
            self.logger.info(f"🔍 Parsing events from transaction: {signature[:20]}...")
            # Parse events from transaction
            parsed_events = self.event_parser.parse_transaction_events(tx_info)
            self.logger.info(f"🎯 Found {len(parsed_events)} events in transaction: {signature[:20]}...")
            stats.events_found += len(parsed_events)
            
            # Store events in database
            for event in parsed_events:
                try:
                    await self._store_event(db, event)
                    stats.events_stored += 1
                except Exception as e:
                    self.logger.error(
                        "Failed to store event",
                        signature=signature,
                        event_type=event.event_type.value,
                        error=str(e)
                    )
                    stats.errors_encountered += 1
                    
            # Commit transaction
            await db.commit()
            
            self.logger.debug(
                "Transaction processed",
                signature=signature,
                events_count=len(parsed_events)
            )
            
        except Exception as e:
            await db.rollback()
            self.logger.error(
                "Transaction processing failed",
                signature=signature,
                error=str(e)
            )
            raise
            
    def _validate_transaction(self, tx_info: TransactionInfo) -> bool:
        """Validate transaction data."""
        try:
            # Basic validation
            if not TransactionValidator.validate_transaction_signature(tx_info.signature):
                return False
                
            if not TransactionValidator.validate_slot_number(tx_info.slot):
                return False
                
            if not TransactionValidator.validate_block_time(tx_info.block_time):
                return False
                
            if not TransactionValidator.validate_transaction_success(tx_info.success, tx_info.logs):
                return False
                
            # Only process successful transactions
            if not tx_info.success:
                return False
                
            return True
            
        except Exception as e:
            self.logger.error(
                "Transaction validation error",
                signature=tx_info.signature,
                error=str(e)
            )
            return False
            
    async def _store_event(self, db: AsyncSession, parsed_event: ParsedEvent):
        """Store a parsed event in the database."""
        try:
            # Validate event data
            if not self.event_parser.validate_event_data(parsed_event):
                raise ValidationError("Event validation failed")
                
            # Additional validation using utils
            validation_errors = validate_event_data(
                parsed_event.event_type.value,
                parsed_event.data
            )
            if validation_errors:
                raise ValidationError(f"Event validation errors: {validation_errors}")
                
            # Create event record
            from app.models.event import EventType as DBEventType
            
            # Map parser event types to database event types
            db_event_type_mapping = {
                "BusinessCreated": DBEventType.BUSINESS_CREATED,
                "BusinessCreatedInSlot": DBEventType.BUSINESS_CREATED_IN_SLOT,
                "BusinessUpgraded": DBEventType.BUSINESS_UPGRADED,
                "BusinessUpgradedInSlot": DBEventType.BUSINESS_UPGRADED_IN_SLOT,
                "BusinessSold": DBEventType.BUSINESS_SOLD,
                "BusinessSoldFromSlot": DBEventType.BUSINESS_SOLD_FROM_SLOT,
                "PlayerCreated": DBEventType.PLAYER_CREATED,
                "EarningsUpdated": DBEventType.EARNINGS_UPDATED,
                "EarningsClaimed": DBEventType.EARNINGS_CLAIMED,
                "SlotUnlocked": DBEventType.SLOT_UNLOCKED,
                "PremiumSlotPurchased": DBEventType.PREMIUM_SLOT_PURCHASED,
            }
            
            db_event_type = db_event_type_mapping.get(parsed_event.event_type.value)
            if not db_event_type:
                raise ValidationError(f"Unknown event type mapping: {parsed_event.event_type.value}")
            
            # Extract player_wallet from event data if available
            player_wallet = None
            if parsed_event.data:
                player_wallet = parsed_event.data.get("owner") or parsed_event.data.get("wallet")
            
            event = Event(
                transaction_signature=parsed_event.signature,
                slot=parsed_event.slot,
                block_time=parsed_event.block_time,
                event_type=db_event_type,
                raw_data=parsed_event.raw_data,
                parsed_data=parsed_event.data,
                player_wallet=player_wallet,
                processed_at=datetime.utcnow()
            )
            
            db.add(event)
            
            self.logger.debug(
                "Event stored",
                signature=parsed_event.signature,
                event_type=parsed_event.event_type.value
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to store event",
                signature=parsed_event.signature,
                event_type=parsed_event.event_type.value,
                error=str(e)
            )
            raise
            
    async def _load_checkpoint(self):
        """Load the last checkpoint from database."""
        try:
            async with get_async_session() as db:
                # Get the last processed event
                result = await db.execute(
                    select(Event)
                    .order_by(desc(Event.slot), desc(Event.processed_at))
                    .limit(1)
                )
                last_event = result.scalar_one_or_none()
                
                if last_event:
                    # Check if checkpoint is too old (configurable lag threshold)
                    current_slot = await self.solana_client.get_slot()
                    MAX_SLOT_LAG = 50000  # If checkpoint is more than 50k slots behind, reset
                    BACKFILL_SLOTS = 1000  # Start 1k slots back for backfill
                    
                    slot_lag = current_slot - last_event.slot
                    
                    if slot_lag > MAX_SLOT_LAG:
                        # Checkpoint too old, reset to recent slot
                        reset_slot = max(0, current_slot - BACKFILL_SLOTS)
                        self.logger.warning(
                            "Checkpoint too old, resetting to recent slot",
                            old_slot=last_event.slot,
                            current_slot=current_slot,
                            slot_lag=slot_lag,
                            reset_to_slot=reset_slot
                        )
                        self.checkpoint = IndexerCheckpoint(
                            last_processed_slot=reset_slot,
                            last_processed_signature="",
                            last_update=datetime.utcnow(),
                            processed_count=0,
                            error_count=0
                        )
                    else:
                        # Use existing checkpoint
                        self.checkpoint = IndexerCheckpoint(
                            last_processed_slot=last_event.slot,
                            last_processed_signature=last_event.transaction_signature,
                            last_update=last_event.processed_at,
                            processed_count=0,  # Could be calculated
                            error_count=0
                        )
                else:
                    # Start from earlier slot to catch historical transactions
                    current_slot = await self.solana_client.get_slot()
                    # Start from 10000 slots ago to catch business creation transactions (increased to cover user transactions)
                    start_slot = max(0, current_slot - 10000)
                    self.checkpoint = IndexerCheckpoint(
                        last_processed_slot=start_slot,
                        last_processed_signature="",
                        last_update=datetime.utcnow(),
                        processed_count=0,
                        error_count=0
                    )
                    
        except Exception as e:
            self.logger.error("Failed to load checkpoint", error=str(e))
            # Default checkpoint
            self.checkpoint = IndexerCheckpoint(
                last_processed_slot=0,
                last_processed_signature="",
                last_update=datetime.utcnow(),
                processed_count=0,
                error_count=0
            )
            
    async def _save_checkpoint(self, db: AsyncSession, slot: int, signature: str):
        """Save checkpoint to track progress."""
        try:
            if self.checkpoint:
                self.checkpoint.last_processed_slot = slot
                self.checkpoint.last_processed_signature = signature
                self.checkpoint.last_update = datetime.utcnow()
                
            # Note: In a production system, you might want to store checkpoints
            # in a dedicated table for better recovery capabilities
            
        except Exception as e:
            self.logger.error("Failed to save checkpoint", error=str(e))
            
    async def get_indexing_status(self) -> Dict[str, Any]:
        """Get current indexing status and statistics."""
        try:
            async with get_async_session() as db:
                # Get total events count
                total_events_result = await db.execute(
                    select(Event).count()
                )
                total_events = total_events_result.scalar()
                
                # Get recent activity (last hour)
                recent_cutoff = datetime.utcnow() - timedelta(hours=1)
                recent_events_result = await db.execute(
                    select(Event)
                    .where(Event.processed_at >= recent_cutoff)
                    .count()
                )
                recent_events = recent_events_result.scalar()
                
                # Get latest block info
                current_slot = await self.solana_client.get_slot()
                
                return {
                    "status": "running" if self._running else "stopped",
                    "current_slot": current_slot,
                    "last_processed_slot": self.checkpoint.last_processed_slot if self.checkpoint else None,
                    "total_events_indexed": total_events,
                    "recent_events_indexed": recent_events,
                    "checkpoint": asdict(self.checkpoint) if self.checkpoint else None,
                    "stats": asdict(self.stats)
                }
                
        except Exception as e:
            self.logger.error("Failed to get indexing status", error=str(e))
            return {"status": "error", "error": str(e)}
            
    async def reindex_from_slot(self, start_slot: int, batch_size: int = 1000):
        """
        Reindex transactions starting from a specific slot.
        
        Args:
            start_slot: Slot number to start reindexing from
            batch_size: Number of transactions to process per batch
        """
        try:
            self.logger.info("Starting reindexing", start_slot=start_slot)
            
            current_slot = await self.solana_client.get_slot()
            total_slots = current_slot - start_slot
            
            processed_slots = 0
            current_start = start_slot
            
            while current_start < current_slot and not self._should_stop:
                batch_end = min(current_start + batch_size, current_slot)
                
                self.logger.info(
                    "Processing slot batch",
                    start=current_start,
                    end=batch_end,
                    progress=f"{processed_slots}/{total_slots}"
                )
                
                batch_stats = await self.index_transactions_batch(
                    current_start,
                    batch_end,
                    batch_size
                )
                
                processed_slots += (batch_end - current_start)
                current_start = batch_end + 1
                
                # Brief pause to avoid overwhelming the RPC
                await asyncio.sleep(1)
                
            self.logger.info("Reindexing completed", processed_slots=processed_slots)
            
        except Exception as e:
            self.logger.error("Reindexing failed", error=str(e))
            raise IndexerError(f"Reindexing failed: {e}")
    
    async def start(self):
        """Start the transaction indexer."""
        self.logger.info("Starting transaction indexer")
        self._running = True
        self._should_stop = False
        
        # Start continuous indexing
        try:
            await self._continuous_indexing()
        except Exception as e:
            self.logger.error("Transaction indexer failed", error=str(e))
            raise
    
    async def stop(self):
        """Stop the transaction indexer."""
        self.logger.info("Stopping transaction indexer")
        self._should_stop = True
        self._running = False
    
    async def _continuous_indexing(self):
        """Continuously index new transactions."""
        while self._running and not self._should_stop:
            try:
                # Get current slot
                current_slot = await self.solana_client.get_slot()
                
                # Check if we need to process new slots
                if self.checkpoint and current_slot > self.checkpoint.last_processed_slot:
                    start_slot = self.checkpoint.last_processed_slot + 1
                    end_slot = min(start_slot + 2000, current_slot)  # Process in larger batches to catch up
                    
                    self.logger.debug(
                        "Processing new slots",
                        start_slot=start_slot,
                        end_slot=end_slot
                    )
                    
                    await self.index_transactions_batch(start_slot, end_slot, 50)
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except asyncio.CancelledError:
                self.logger.info("Transaction indexer cancelled")
                break
            except Exception as e:
                self.logger.error("Error in continuous indexing", error=str(e))
                await asyncio.sleep(60)  # Wait longer on error


# Global indexer instance
_indexer: Optional[TransactionIndexer] = None


async def get_transaction_indexer() -> TransactionIndexer:
    """Get or create a global transaction indexer instance."""
    global _indexer
    if _indexer is None:
        _indexer = TransactionIndexer()
        await _indexer.initialize()
    return _indexer


async def shutdown_transaction_indexer():
    """Shutdown the global transaction indexer instance."""
    global _indexer
    if _indexer:
        await _indexer.shutdown()
        _indexer = None
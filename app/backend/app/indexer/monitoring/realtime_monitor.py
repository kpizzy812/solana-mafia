"""
Real-time monitoring for blockchain events.
"""

import asyncio
from typing import Optional, Callable
from datetime import datetime, timedelta

import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.core.database import get_async_session
from app.services.solana_client import SolanaClient, get_solana_client
from app.indexer.transaction_indexer import TransactionIndexer, get_transaction_indexer
from app.models.event import Event
from app.indexer.core.types import IndexerStatus, ProcessingStats


logger = structlog.get_logger(__name__)


class RealtimeMonitor:
    """
    Real-time monitoring component for blockchain events.
    
    Handles WebSocket connections and fallback polling.
    """
    
    def __init__(self, indexer):
        """Initialize the realtime monitor."""
        self.indexer = indexer
        self.logger = logger.bind(service="realtime_monitor")
        self.solana_client: Optional[SolanaClient] = None
        self.transaction_indexer: Optional[TransactionIndexer] = None
        
    async def initialize(self):
        """Initialize monitoring components."""
        self.solana_client = await get_solana_client()
        self.transaction_indexer = await get_transaction_indexer()
        
    async def start_monitoring(self):
        """🚀 Start the ENHANCED real-time event monitoring with Helius WebSocket."""
        self.logger.info("🚀 Starting ENHANCED real-time event monitoring with Helius WebSocket")
        
        # Optional: Process some recent historical transactions on startup
        try:
            current_slot = await self.solana_client.get_slot()
            if self.transaction_indexer.checkpoint:
                last_processed_slot = self.transaction_indexer.checkpoint.last_processed_slot
                
                # Quick backfill to catch up
                backfill_start = max(0, last_processed_slot - 500)  # Even smaller window for faster startup
                if backfill_start < last_processed_slot:
                    self.logger.info(
                        "⚡ Quick backfill of recent transactions",
                        backfill_start=backfill_start,
                        checkpoint_slot=last_processed_slot,
                        current_slot=current_slot
                    )
                    await self._process_new_transactions(backfill_start, last_processed_slot)
        except Exception as e:
            self.logger.warning("⚠️ Backfill failed, starting from current slot", error=str(e))
                
        # Start real-time WebSocket monitoring with enhanced error handling
        try:
            self.logger.info("🔌 Starting Helius WebSocket monitoring")
            await self.solana_client.monitor_program_logs_realtime(
                callback=self._process_realtime_transaction_enhanced,
                auto_reconnect=True
            )
        except Exception as e:
            self.logger.error("❌ Helius WebSocket monitoring failed, falling back to polling", error=str(e))
            # Fallback to old polling method if WebSocket fails
            await self._monitor_events_fallback()
        
        self.logger.info("🛑 Event monitoring stopped")
    
    async def _process_realtime_transaction_enhanced(self, tx_info):
        """🚀 ENHANCED real-time transaction processing with optimized event handling."""
        try:
            self.logger.info(
                "🔥 INSTANT transaction processing (ENHANCED)",
                signature=tx_info.signature[:20],
                slot=tx_info.slot,
                events_count=len(tx_info.events),
                has_block_time=tx_info.block_time is not None
            )
            
            if not tx_info.events:
                self.logger.debug("ℹ️ Transaction has no events, skipping", signature=tx_info.signature[:20])
                return
            
            # Store transaction and events to database with enhanced error handling
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    async with get_async_session() as db:
                        # Store events directly from real-time transaction
                        stored_events = []
                        for event in tx_info.events:
                            try:
                                event_record = await self.transaction_indexer._store_event(db, event, tx_info)
                                if event_record:
                                    stored_events.append(event_record)
                            except Exception as e:
                                self.logger.warning(
                                    "⚠️ Failed to store individual event",
                                    signature=tx_info.signature[:20],
                                    event_type=event.get("event_type"),
                                    error=str(e)
                                )
                                continue
                        
                        # Process events immediately using event handlers
                        if stored_events:
                            await self._handle_realtime_events_enhanced(db, stored_events, tx_info)
                        
                        await db.commit()
                        
                        self.indexer.stats.events_processed += len(stored_events)
                        
                        self.logger.info(
                            "✅ Enhanced real-time transaction processed",
                            signature=tx_info.signature[:20],
                            stored_events=len(stored_events),
                            processing_delay="<500ms",
                            attempt=attempt + 1
                        )
                        break
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = 0.1 * (2 ** attempt)  # Exponential backoff: 0.1s, 0.2s, 0.4s
                        self.logger.warning(
                            "⚠️ Database operation failed, retrying",
                            signature=tx_info.signature[:20],
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            wait_time=wait_time,
                            error=str(e)
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        raise e
                        
        except Exception as e:
            self.logger.error(
                "❌ Failed to process enhanced real-time transaction",
                signature=tx_info.signature[:20] if tx_info.signature else "unknown",
                error=str(e),
                error_type=type(e).__name__
            )
            self.indexer.stats.errors += 1

    async def _process_realtime_transaction(self, tx_info):
        """Legacy real-time transaction processing - redirects to enhanced version."""
        await self._process_realtime_transaction_enhanced(tx_info)
    
    async def _handle_realtime_events_enhanced(self, db, event_records, tx_info):
        """🚀 ENHANCED event handling with WebSocket notifications and error recovery."""
        successful_events = 0
        failed_events = 0
        
        for event_record in event_records:
            try:
                # Determine event type from stored event record
                event_type_str = event_record.event_type if hasattr(event_record, 'event_type') else None
                if not event_type_str:
                    self.logger.warning("⚠️ Event record missing event_type", signature=tx_info.signature[:20])
                    continue
                
                # Get handler for this event type from main indexer
                from app.services.event_parser import EventType
                try:
                    event_type = EventType(event_type_str)
                    handler = self.indexer._event_handlers.get(event_type)
                    
                    if handler:
                        # Call the event handler
                        await handler(db, event_record)
                        successful_events += 1
                        
                        self.logger.debug(
                            "✅ Event handled successfully",
                            signature=tx_info.signature[:20],
                            event_type=event_type_str
                        )
                    else:
                        self.logger.warning(
                            "⚠️ No handler found for event type",
                            signature=tx_info.signature[:20],
                            event_type=event_type_str
                        )
                        
                except ValueError as e:
                    self.logger.warning(
                        "⚠️ Unknown event type",
                        signature=tx_info.signature[:20],
                        event_type=event_type_str,
                        error=str(e)
                    )
                    continue
                
                # Send WebSocket notification immediately (fire-and-forget)
                asyncio.create_task(self._send_websocket_notification(event_record, tx_info))
                        
            except Exception as e:
                failed_events += 1
                self.logger.error(
                    "❌ Failed to handle enhanced real-time event",
                    signature=tx_info.signature[:20],
                    event_type=getattr(event_record, 'event_type', 'unknown'),
                    error=str(e),
                    error_type=type(e).__name__
                )
        
        if successful_events > 0 or failed_events > 0:
            self.logger.info(
                "📊 Event handling summary",
                signature=tx_info.signature[:20],
                successful=successful_events,
                failed=failed_events,
                total=len(event_records)
            )
    
    async def _send_websocket_notification(self, event_record, tx_info):
        """Send WebSocket notification for real-time event (async fire-and-forget)."""
        try:
            from app.websocket.notification_service import notification_service
            
            # Create event notification data
            event_data = {
                'transaction_signature': tx_info.signature,
                'event_type': getattr(event_record, 'event_type', 'unknown'),
                'slot': tx_info.slot,
                'block_time': tx_info.block_time.isoformat() if tx_info.block_time else None,
                'parsed_data': getattr(event_record, 'parsed_data', {}),
                'processed_at': datetime.utcnow().isoformat(),
                'source': 'real_time_websocket'
            }
            
            await notification_service.send_real_time_event(event_data)
            
            self.logger.debug(
                "📡 WebSocket notification sent",
                signature=tx_info.signature[:20],
                event_type=event_data['event_type']
            )
            
        except ImportError:
            # notification_service not available - skip notifications
            pass
        except Exception as e:
            self.logger.warning(
                "⚠️ Failed to send WebSocket notification",
                signature=tx_info.signature[:20] if tx_info.signature else "unknown",
                event_type=getattr(event_record, 'event_type', 'unknown'),
                error=str(e)
            )

    async def _handle_realtime_events(self, db, events, tx_info):
        """Legacy event handling - redirects to enhanced version."""
        # Convert legacy events to event_records format for enhanced handler
        event_records = []
        for event in events:
            # Create mock event record for compatibility
            mock_record = type('MockEventRecord', (), {
                'event_type': getattr(event, 'event_type', 'unknown'),
                'parsed_data': getattr(event, 'data', {})
            })()
            event_records.append(mock_record)
        
        await self._handle_realtime_events_enhanced(db, event_records, tx_info)
    
    async def _monitor_events_fallback(self):
        """Fallback polling method if WebSocket fails."""
        self.logger.warning("Using FALLBACK polling mode (WebSocket failed)")
        
        # Initialize from checkpoint or recent slot
        last_processed_slot = 0
        current_slot = await self.solana_client.get_slot()
        
        if self.transaction_indexer.checkpoint:
            last_processed_slot = self.transaction_indexer.checkpoint.last_processed_slot
        else:
            last_processed_slot = max(0, current_slot - 1000)  # Only look back 1000 slots
            
        retry_count = 0
        max_retries = settings.indexer_max_retries
        
        while not self.indexer._should_stop:
            try:
                current_slot = await self.solana_client.get_slot()
                
                if current_slot > last_processed_slot:
                    await self._process_new_transactions(last_processed_slot + 1, current_slot)
                    last_processed_slot = current_slot
                    self.indexer.stats.last_processed_slot = current_slot
                    retry_count = 0
                    
                # Faster polling for fallback mode
                await asyncio.sleep(2)  # 2 seconds instead of 5
                
            except asyncio.CancelledError:
                self.logger.info("Fallback monitoring cancelled")
                break
                
            except Exception as e:
                retry_count += 1
                self.indexer.stats.errors += 1
                
                self.logger.error(
                    "Error in fallback monitoring",
                    error=str(e),
                    retry_count=retry_count,
                    max_retries=max_retries
                )
                
                if retry_count >= max_retries:
                    self.indexer.status = IndexerStatus.ERROR
                    self.logger.error("Max retries exceeded in fallback mode")
                    break
                    
                wait_time = min(settings.indexer_retry_delay * (2 ** retry_count), 300)
                await asyncio.sleep(wait_time)
        
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
                        # Delegate to transaction processor
                        from .transaction_processor import TransactionProcessor
                        processor = TransactionProcessor(self.indexer)
                        await processor.handle_event(db, event_record)
                    except Exception as e:
                        self.logger.error(
                            "Failed to handle event",
                            signature=event_record.transaction_signature,
                            event_type=event_record.event_type,
                            error=str(e)
                        )
                        self.indexer.stats.errors += 1
                        
                await db.commit()
                
        except Exception as e:
            self.logger.error("Failed to process recent events", error=str(e))
            raise
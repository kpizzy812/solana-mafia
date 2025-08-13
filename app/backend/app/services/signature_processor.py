"""
Simple async signature processor based on proven force_process_transaction logic.

This service provides:
- Async queue for incoming transaction signatures 
- Background processing using the proven force_process_transaction approach
- WebSocket notifications when processing is complete
- Simple, reliable architecture focused on what works
"""

import asyncio
import structlog
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum
import json

from app.core.database import get_async_session, init_database
from app.services.solana_client import get_solana_client
from app.services.event_parser import get_event_parser
from app.indexer.handlers.business_handlers import BusinessHandlers
from app.indexer.handlers.earnings_handlers import EarningsHandlers
from app.indexer.handlers.player_handlers import PlayerHandlers
from app.indexer.core.types import ProcessingStats
from app.websocket.notification_service import get_notification_service


logger = structlog.get_logger(__name__)


class ProcessingStatus(Enum):
    """Status of signature processing."""
    QUEUED = "queued"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ProcessingRequest:
    """Request to process a transaction signature."""
    signature: str
    user_wallet: Optional[str] = None
    slot_index: Optional[int] = None
    business_level: Optional[int] = None
    is_admin_transaction: bool = False
    queued_at: datetime = None
    status: ProcessingStatus = ProcessingStatus.QUEUED
    
    def __post_init__(self):
        if self.queued_at is None:
            self.queued_at = datetime.utcnow()


class SignatureProcessor:
    """
    Simple async signature processor.
    
    Architecture:
    1. Frontend sends signature → queue
    2. Background worker processes using force_process_transaction logic
    3. WebSocket notification when complete
    4. Simple, proven, reliable
    """
    
    def __init__(self):
        """Initialize the signature processor."""
        self.logger = logger.bind(service="signature_processor")
        
        # Processing queue
        self.queue: asyncio.Queue[ProcessingRequest] = asyncio.Queue()
        self.active_requests: Dict[str, ProcessingRequest] = {}
        self.completed_requests: Dict[str, Dict[str, Any]] = {}
        
        # State
        self._running = False
        self._should_stop = False
        self._worker_task: Optional[asyncio.Task] = None
        
        # Stats
        self.stats = {
            "total_queued": 0,
            "total_processed": 0,
            "total_failed": 0,
            "start_time": None,
            "last_processed": None
        }
        
        self.logger.info("SignatureProcessor initialized")
    
    async def start(self):
        """Start the signature processor worker."""
        if self._running:
            self.logger.warning("SignatureProcessor already running")
            return
            
        try:
            self.logger.info("Starting SignatureProcessor worker")
            
            # Initialize database
            await init_database()
            
            self._running = True
            self._should_stop = False
            self.stats["start_time"] = datetime.utcnow()
            
            # Start background worker
            self._worker_task = asyncio.create_task(self._worker_loop())
            
            self.logger.info("✅ SignatureProcessor started")
            
        except Exception as e:
            self.logger.error("Failed to start SignatureProcessor", error=str(e))
            raise
    
    async def stop(self):
        """Stop the signature processor."""
        if not self._running:
            return
            
        self.logger.info("Stopping SignatureProcessor")
        
        self._should_stop = True
        self._running = False
        
        # Cancel worker task
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("SignatureProcessor stopped")
    
    async def queue_signature(
        self, 
        signature: str, 
        user_wallet: Optional[str] = None,
        slot_index: Optional[int] = None,
        business_level: Optional[int] = None,
        is_admin_transaction: bool = False
    ) -> bool:
        """
        Queue a transaction signature for processing.
        
        Args:
            signature: Transaction signature to process
            user_wallet: User wallet (for UI notifications)
            slot_index: Business slot index (for UI updates)
            business_level: Business level (for UI context)
            
        Returns:
            bool: True if queued successfully
        """
        try:
            # Check if already queued or processing
            if signature in self.active_requests:
                self.logger.info("Signature already being processed", signature=signature)
                return True
            
            # Create processing request
            request = ProcessingRequest(
                signature=signature,
                user_wallet=user_wallet,
                slot_index=slot_index,
                business_level=business_level,
                is_admin_transaction=is_admin_transaction
            )
            
            # Add to queue
            await self.queue.put(request)
            self.active_requests[signature] = request
            self.stats["total_queued"] += 1
            
            self.logger.info("📥 Signature queued for processing",
                           signature=signature,
                           user_wallet=user_wallet,
                           queue_size=self.queue.qsize())
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to queue signature", 
                            signature=signature, 
                            error=str(e))
            return False
    
    async def _worker_loop(self):
        """Main worker loop processing signatures."""
        self.logger.info("🏃‍♂️ SignatureProcessor worker started")
        
        while self._running and not self._should_stop:
            try:
                # Get next request from queue (with timeout)
                try:
                    request = await asyncio.wait_for(self.queue.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    continue  # Check if should stop
                
                # Process the signature
                await self._process_signature(request)
                
            except asyncio.CancelledError:
                self.logger.info("Worker loop cancelled")
                break
            except Exception as e:
                self.logger.error("Error in worker loop", error=str(e))
                await asyncio.sleep(1)  # Brief pause on error
        
        self.logger.info("SignatureProcessor worker stopped")
    
    async def _process_signature(self, request: ProcessingRequest):
        """Process a single signature using proven force_process_transaction logic."""
        signature = request.signature
        
        try:
            self.logger.info("🔧 Processing signature", 
                           signature=signature,
                           user_wallet=request.user_wallet)
            
            # Update status
            request.status = ProcessingStatus.PROCESSING
            
            # Send processing notification
            await self._send_processing_notification(request, "processing")
            
            # === PROVEN FORCE_PROCESS_TRANSACTION LOGIC ===
            
            # Get services
            solana_client = await get_solana_client()
            event_parser = get_event_parser()
            
            # Initialize handlers with stats
            stats = ProcessingStats()
            business_handlers = BusinessHandlers(stats)
            earnings_handlers = EarningsHandlers(stats)
            player_handlers = PlayerHandlers(stats)
            
            # Event handler mappings (same as force_process_transaction)
            event_handlers = {
                "BusinessCreatedInSlot": business_handlers.handle_business_created_in_slot,
                "BusinessSoldFromSlot": business_handlers.handle_business_sold_from_slot,
                "BusinessUpgradedInSlot": business_handlers.handle_business_upgraded_in_slot,
                "BusinessUpgraded": business_handlers.handle_business_upgraded,
                "BusinessSold": business_handlers.handle_business_sold,
                "BusinessTransferred": business_handlers.handle_business_transferred,
                "BusinessDeactivated": business_handlers.handle_business_deactivated,
                "EarningsUpdated": earnings_handlers.handle_earnings_updated,
                "EarningsClaimed": earnings_handlers.handle_earnings_claimed,
                "PlayerCreated": player_handlers.handle_player_created,
                "SlotUnlocked": player_handlers.handle_slot_unlocked,
                # Also support enum values
                "BUSINESS_CREATED_IN_SLOT": business_handlers.handle_business_created_in_slot,
                "BUSINESS_SOLD_FROM_SLOT": business_handlers.handle_business_sold_from_slot,
                "BUSINESS_UPGRADED_IN_SLOT": business_handlers.handle_business_upgraded_in_slot,
                "BUSINESS_UPGRADED": business_handlers.handle_business_upgraded,
                "BUSINESS_SOLD": business_handlers.handle_business_sold,
                "EARNINGS_UPDATED": earnings_handlers.handle_earnings_updated,
                "EARNINGS_CLAIMED": earnings_handlers.handle_earnings_claimed,
                "PLAYER_CREATED": player_handlers.handle_player_created,
            }
            
            # Get transaction from blockchain
            self.logger.info("📡 Fetching transaction", signature=signature)
            
            tx_info = await solana_client.get_transaction(signature)
            if not tx_info:
                raise Exception(f"Transaction not found: {signature}")
            
            # Parse events from transaction
            events = event_parser.parse_transaction_events(tx_info)
            
            if not events:
                self.logger.info("No events found in transaction", signature=signature)
                result = {"events": [], "success": True}
            else:
                self.logger.info("🎯 Found events", 
                               signature=signature,
                               event_count=len(events),
                               event_types=[e.event_type.value for e in events])
                
                # Process each event
                processed_events = []
                async with get_async_session() as db:
                    for event in events:
                        try:
                            self.logger.info("🏃‍♂️ Processing event", 
                                           event_type=event.event_type.value,
                                           signature=signature)
                            
                            # Get handler for this event type
                            handler = event_handlers.get(event.event_type.value)
                            if not handler:
                                self.logger.warning("⚠️ No handler for event type", 
                                                 event_type=event.event_type.value)
                                continue
                                
                            # Process event
                            await handler(db, event)
                            processed_events.append({
                                "type": event.event_type.value,
                                "data": event.data
                            })
                            
                            self.logger.info("✅ Event processed successfully",
                                           event_type=event.event_type.value,
                                           signature=signature)
                            
                        except Exception as e:
                            self.logger.error("❌ Failed to process event",
                                           event_type=event.event_type.value,
                                           signature=signature,
                                           error=str(e))
                            raise
                    
                    # Commit all changes
                    await db.commit()
                    self.logger.info("💾 All changes committed")
                
                result = {
                    "events": processed_events,
                    "success": True,
                    "events_count": len(processed_events)
                }
            
            # Update status and store result
            request.status = ProcessingStatus.COMPLETED
            self.completed_requests[signature] = result
            self.stats["total_processed"] += 1
            self.stats["last_processed"] = datetime.utcnow()
            
            # Send completion notification
            await self._send_processing_notification(request, "completed", result)
            
            self.logger.info("🎉 Signature processed successfully", 
                           signature=signature,
                           events_processed=result.get("events_count", 0))
            
        except Exception as e:
            # Update status on failure
            request.status = ProcessingStatus.FAILED
            error_result = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
            self.completed_requests[signature] = error_result
            self.stats["total_failed"] += 1
            
            # Send failure notification
            await self._send_processing_notification(request, "failed", error_result)
            
            self.logger.error("💥 Failed to process signature",
                            signature=signature,
                            error=str(e))
        
        finally:
            # Remove from active requests
            self.active_requests.pop(signature, None)
    
    async def _send_processing_notification(
        self, 
        request: ProcessingRequest, 
        status: str, 
        result: Optional[Dict[str, Any]] = None
    ):
        """Send WebSocket notification about processing status."""
        try:
            # Skip WebSocket notifications for admin transactions
            if request.is_admin_transaction:
                self.logger.debug("Skipping WebSocket notification for admin transaction",
                                signature=request.signature,
                                status=status)
                return
            
            notification_service = get_notification_service()
            if not notification_service:
                return
            
            # Use the new specialized notification method for user transactions
            await notification_service.notify_signature_processing(
                signature=request.signature,
                status=status,
                user_wallet=request.user_wallet,
                slot_index=request.slot_index,
                business_level=request.business_level,
                result=result
            )
            
            self.logger.info("📡 Sent processing notification",
                           signature=request.signature,
                           status=status,
                           user_wallet=request.user_wallet)
            
        except Exception as e:
            self.logger.error("Failed to send processing notification", 
                            signature=request.signature,
                            error=str(e))
    
    def get_status(self) -> Dict[str, Any]:
        """Get current processor status."""
        return {
            "running": self._running,
            "queue_size": self.queue.qsize(),
            "active_requests": len(self.active_requests),
            "completed_requests": len(self.completed_requests),
            "stats": self.stats.copy()
        }
    
    def get_request_status(self, signature: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific signature request."""
        if signature in self.active_requests:
            request = self.active_requests[signature]
            return {
                "status": request.status.value,
                "queued_at": request.queued_at.isoformat(),
                "user_wallet": request.user_wallet,
                "slot_index": request.slot_index
            }
        elif signature in self.completed_requests:
            result = self.completed_requests[signature]
            return {
                "status": "completed" if result.get("success") else "failed",
                "result": result
            }
        else:
            return None


# Global signature processor instance
_signature_processor: Optional[SignatureProcessor] = None


async def get_signature_processor() -> SignatureProcessor:
    """Get or create global signature processor instance."""
    global _signature_processor
    if _signature_processor is None:
        _signature_processor = SignatureProcessor()
        await _signature_processor.start()
    return _signature_processor


async def queue_signature_for_processing(
    signature: str,
    user_wallet: Optional[str] = None,
    slot_index: Optional[int] = None,
    business_level: Optional[int] = None,
    is_admin_transaction: bool = False
) -> bool:
    """Queue a signature for processing."""
    processor = await get_signature_processor()
    return await processor.queue_signature(
        signature=signature,
        user_wallet=user_wallet,
        slot_index=slot_index,
        business_level=business_level,
        is_admin_transaction=is_admin_transaction
    )


async def queue_admin_transaction_for_processing(
    signature: str,
    admin_wallet: str,
    operation_type: str = "earnings_update",
    context: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Queue an admin transaction signature for processing.
    
    Args:
        signature: Admin transaction signature
        admin_wallet: Admin wallet that sent the transaction
        operation_type: Type of admin operation (earnings_update, etc.)
        context: Additional context for the operation
        
    Returns:
        bool: True if queued successfully
    """
    processor = await get_signature_processor()
    return await processor.queue_signature(
        signature=signature,
        user_wallet=admin_wallet,  # For logging purposes
        slot_index=None,
        business_level=None,
        is_admin_transaction=True
    )


async def get_processing_status(signature: str) -> Optional[Dict[str, Any]]:
    """Get processing status for a signature."""
    processor = await get_signature_processor()
    return processor.get_request_status(signature)


async def shutdown_signature_processor():
    """Shutdown the global signature processor."""
    global _signature_processor
    if _signature_processor:
        await _signature_processor.stop()
        _signature_processor = None
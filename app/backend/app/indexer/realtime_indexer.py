"""
Real-time WebSocket indexer for Solana events.
Replaces batch processing with instant WebSocket subscriptions.
"""

import asyncio
import json
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from dataclasses import dataclass, asdict

import websockets
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.config import settings
from app.core.exceptions import IndexerError
from app.services.event_parser import get_event_parser, ParsedEvent
from app.services.solana_client import get_solana_client
from app.models.event import Event, EventType as DBEventType
from app.websocket.notification_service import NotificationService
from app.indexer.handlers.business_handlers import BusinessHandlers
from app.indexer.handlers.earnings_handlers import EarningsHandlers  
from app.indexer.handlers.player_handlers import PlayerHandlers


logger = structlog.get_logger(__name__)


@dataclass 
class RealtimeStats:
    """Statistics for real-time indexing."""
    events_processed: int = 0
    events_stored: int = 0
    subscriptions_active: int = 0
    errors_encountered: int = 0
    start_time: Optional[datetime] = None
    last_event_time: Optional[datetime] = None
    # Business statistics  
    players_created: int = 0
    businesses_created: int = 0
    businesses_upgraded: int = 0
    businesses_sold: int = 0
    earnings_updated: int = 0
    earnings_claimed: int = 0


class RealTimeIndexer:
    """
    Real-time indexer using WebSocket subscriptions for instant event processing.
    
    Features:
    - programSubscribe: Instant account changes for our program
    - logsSubscribe: Real-time program logs and events
    - No delays: Events processed immediately when they occur
    - WebSocket notifications: Instant updates to frontend
    """
    
    def __init__(self):
        """Initialize the real-time indexer."""
        self.logger = logger.bind(service="realtime_indexer")
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.event_parser = get_event_parser()
        self.solana_client = get_solana_client()  # 🔧 Добавляем SolanaClient для RPC запросов
        self.notification_service: Optional[NotificationService] = None
        self.stats = RealtimeStats()
        self._running = False
        self._should_stop = False
        self._subscriptions: Dict[str, int] = {}  # subscription_type -> subscription_id
        self._tasks: List[asyncio.Task] = []
    
    async def initialize(self):
        """Initialize the real-time indexer."""
        try:
            self.logger.info("Initializing real-time indexer")
            
            # Initialize notification service for WebSocket updates
            from app.websocket.notification_service import get_notification_service
            self.notification_service = get_notification_service()
            
            # Initialize ALL event handlers for processing
            self.business_handlers = BusinessHandlers(self.stats)
            self.earnings_handlers = EarningsHandlers(self.stats)
            self.player_handlers = PlayerHandlers(self.stats)
            
            self.stats.start_time = datetime.utcnow()
            
            self.logger.info("Real-time indexer initialized successfully")
            
        except Exception as e:
            self.logger.error("Failed to initialize real-time indexer", error=str(e))
            raise IndexerError(f"Failed to initialize real-time indexer: {e}")
    
    async def start(self):
        """Start the real-time indexer with WebSocket subscriptions."""
        try:
            self.logger.info("Starting real-time indexer")
            self._running = True
            self._should_stop = False
            
            # Connect to Solana WebSocket
            await self._connect_websocket()
            
            # Start message processing loop FIRST (handles all WebSocket I/O)
            process_task = asyncio.create_task(self._process_messages())
            self._tasks.append(process_task)
            
            # Wait a bit for connection to stabilize
            await asyncio.sleep(0.1)
            
            # Send subscription requests (but don't wait for responses here)
            await self._send_program_subscription()
            await self._send_logs_subscription()
            
            # Start health check
            health_task = asyncio.create_task(self._periodic_health_check())
            self._tasks.append(health_task)
            
            self.logger.info("Real-time indexer started successfully")
            
            # Wait for all tasks
            await asyncio.gather(*self._tasks, return_exceptions=True)
            
        except Exception as e:
            self.logger.error("Real-time indexer failed", error=str(e))
            raise IndexerError(f"Real-time indexer failed: {e}")
    
    async def stop(self):
        """Stop the real-time indexer."""
        self.logger.info("Stopping real-time indexer")
        
        self._should_stop = True
        self._running = False
        
        # Unsubscribe from all subscriptions
        for sub_type, sub_id in self._subscriptions.items():
            try:
                await self._unsubscribe(sub_type, sub_id)
            except Exception as e:
                self.logger.warning(f"Failed to unsubscribe from {sub_type}", error=str(e))
        
        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Close WebSocket connection
        if self.websocket:
            await self.websocket.close()
        
        self.logger.info("Real-time indexer stopped")
    
    async def _connect_websocket(self):
        """Connect to Solana WebSocket RPC."""
        try:
            ws_url = settings.solana_ws_url
            self.logger.info("Connecting to Solana WebSocket", url=ws_url)
            
            self.websocket = await websockets.connect(ws_url)
            
            self.logger.info("✅ Connected to Solana WebSocket successfully")
            
        except Exception as e:
            self.logger.error("Failed to connect to Solana WebSocket", error=str(e))
            raise IndexerError(f"WebSocket connection failed: {e}")
    
    async def _send_program_subscription(self):
        """Send program accounts subscription request."""
        try:
            self.logger.info("📡 Sending program account subscription request")
            
            # programSubscribe request
            request = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "programSubscribe",
                "params": [
                    settings.solana_program_id,  # Our program ID
                    {
                        "commitment": "confirmed",
                        "encoding": "base64"
                    }
                ]
            }
            
            await self.websocket.send(json.dumps(request))
            self.logger.info("📤 Program subscription request sent")
                
        except Exception as e:
            self.logger.error("Failed to send program subscription", error=str(e))
            raise
    
    async def _send_logs_subscription(self):
        """Send program logs subscription request."""
        try:
            self.logger.info("📡 Sending program logs subscription request")
            
            # logsSubscribe request - filter by our program
            request = {
                "jsonrpc": "2.0", 
                "id": 2,
                "method": "logsSubscribe",
                "params": [
                    {"mentions": [settings.solana_program_id]},  # Filter by our program
                    {
                        "commitment": "confirmed"
                    }
                ]
            }
            
            await self.websocket.send(json.dumps(request))
            self.logger.info("📤 Logs subscription request sent")
                
        except Exception as e:
            self.logger.error("Failed to send logs subscription", error=str(e))
            raise
    
    async def _process_messages(self):
        """Process incoming WebSocket messages."""
        self.logger.info("🎯 Starting real-time message processing")
        
        while self._running and not self._should_stop:
            try:
                # Receive message from WebSocket
                message = await self.websocket.recv()
                message_data = json.loads(message)
                
                # DEBUG: Log ALL incoming messages
                self.logger.info("📨 Received WebSocket message", 
                               method=message_data.get("method"), 
                               has_params=bool(message_data.get("params")),
                               message_keys=list(message_data.keys()))
                
                # Check if it's a subscription response
                if "id" in message_data and "result" in message_data:
                    await self._handle_subscription_response(message_data)
                # Check if it's a subscription notification
                elif "method" in message_data and "params" in message_data:
                    self.logger.info("🎯 Processing subscription notification", method=message_data.get("method"))
                    await self._handle_subscription_notification(message_data)
                else:
                    self.logger.debug("📝 Non-notification message", message_data=message_data)
                
            except websockets.exceptions.ConnectionClosed:
                self.logger.warning("WebSocket connection closed")
                if not self._should_stop:
                    await self._reconnect_websocket()
            except Exception as e:
                self.logger.error("Error processing message", error=str(e))
                self.stats.errors_encountered += 1
                await asyncio.sleep(1)  # Brief pause on error
    
    async def _handle_subscription_response(self, message_data: Dict):
        """Handle subscription request responses."""
        try:
            request_id = message_data.get("id")
            result = message_data.get("result")
            error = message_data.get("error")
            
            if error:
                self.logger.error("Subscription request failed", request_id=request_id, error=error)
                self.stats.errors_encountered += 1
                return
            
            if request_id == 1:  # Program subscription
                self._subscriptions["program"] = result
                self.stats.subscriptions_active += 1
                self.logger.info("✅ Program subscription confirmed", subscription_id=result)
                
            elif request_id == 2:  # Logs subscription
                self._subscriptions["logs"] = result
                self.stats.subscriptions_active += 1
                self.logger.info("✅ Logs subscription confirmed", subscription_id=result)
                
            else:
                self.logger.debug("Unknown subscription response", request_id=request_id)
                
        except Exception as e:
            self.logger.error("Error handling subscription response", error=str(e))
            self.stats.errors_encountered += 1
    
    async def _handle_subscription_notification(self, message_data: Dict):
        """Handle incoming subscription notifications."""
        try:
            method = message_data.get("method")
            params = message_data.get("params", {})
            
            # 🔍 ENHANCED DEBUG: Log ALL subscription notifications
            self.logger.info("🎯 Processing subscription notification", 
                           method=method, 
                           has_params=bool(params),
                           params_keys=list(params.keys()) if params else [])
            
            if method == "programNotification":
                self.logger.info("📋 Handling program notification")
                await self._handle_program_notification(params)
            elif method == "logsNotification":
                self.logger.info("📋 Handling logs notification") 
                await self._handle_logs_notification(params)
            else:
                self.logger.info(f"🤷 Unknown notification method: {method}")
            
        except Exception as e:
            self.logger.error("Error handling subscription notification", error=str(e))
            self.stats.errors_encountered += 1
    
    async def _handle_program_notification(self, params: Dict):
        """Handle program account change notifications."""
        try:
            subscription_id = params.get("subscription")
            result = params.get("result", {})
            
            account_info = result.get("value", {})
            pubkey = result.get("pubkey")
            
            self.logger.info("🔄 Program account changed", pubkey=pubkey)
            
            # Here you could decode account data and trigger specific events
            # For now, we rely more on logs for event parsing
            
        except Exception as e:
            self.logger.error("Error handling program notification", error=str(e))
            self.stats.errors_encountered += 1
    
    async def _handle_logs_notification(self, params: Dict):
        """Handle logs notification and parse events."""
        try:
            subscription_id = params.get("subscription")
            result = params.get("result", {})
            
            # 🔍 ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ
            self.logger.info(f"🔍 DEBUG logs notification raw params", 
                            subscription_id=subscription_id,
                            has_result=bool(result),
                            result_keys=list(result.keys()) if result else [])
            
            value = result.get("value", {})
            logs = value.get("logs", [])
            signature = value.get("signature")
            slot = value.get("slot")
            block_time = value.get("blockTime")
            err = value.get("err")
            
            # 🔍 ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ параметров
            self.logger.info(f"🔍 DEBUG extracted values", 
                            signature=signature,
                            slot=slot, 
                            logs_count=len(logs) if logs else 0,
                            has_error=bool(err))
            
            # 🔍 LOG ALL SIGNATURES: Log every signature we receive via WebSocket
            if signature:
                self.logger.info(f"📝 WebSocket received transaction", signature=signature[:20] + "...")
            else:
                self.logger.warning(f"📝 WebSocket notification with NO signature", value_keys=list(value.keys()) if value else [])
            
            # Skip failed transactions
            if err:
                self.logger.debug("Skipping failed transaction", signature=signature, error=err)
                return
            
            # 🔍 ПРОВЕРЯЕМ signature
            if not signature:
                self.logger.warning("⚠️ No signature in logs notification - skipping", 
                                  value_keys=list(value.keys()) if value else [],
                                  raw_value=value)
                return
            
            self.logger.info(f"🎯 Processing real-time logs", signature=signature, slot=slot)
            
            # 🔍 EXTRA DEBUG: Check if signature matches our target
            if signature in ["4JArkZW4G3TsFEsS9Ebz2FpP6VuhoEtLM2m95vNY6e3j9zwRj53eKmWq8P8oQ88FmAtxnL6q92zqZmsTBb6AoPjG", 
                           "3XRfta7u6JBELdUf1u7tbv5nFRBzCNYu9CYRoskLBo4ZxrLeTa9qz3M9yDniqL9qrDsNMQeTbrL16gsAVa218xiE"]:
                self.logger.info(f"🎯🎯 FOUND TARGET TRANSACTION!", signature=signature)
            
            # 🔧 ИСПРАВЛЕНИЕ: WebSocket логи truncated - получаем полную транзакцию через RPC
            self.logger.info(f"📡 Fetching full transaction for real-time processing", signature=signature)
            
            try:
                # Получаем полную транзакцию через RPC (как в force_process_transaction)
                tx_info = await self.solana_client.get_transaction(signature)
                if not tx_info:
                    self.logger.warning(f"⚠️ Could not fetch transaction for real-time processing", signature=signature)
                    return
                
                # Парсим события из instruction data (не из логов!)
                parsed_events = self.event_parser.parse_transaction_events(tx_info)
                self.logger.info(f"✅ Parsed {len(parsed_events)} events from RPC transaction", signature=signature)
                
            except Exception as e:
                self.logger.error(f"❌ Failed to fetch/parse RPC transaction for real-time", 
                                signature=signature, error=str(e))
                # Fallback к старому методу парсинга логов
                parsed_events = self.event_parser.parse_logs_for_events(
                    logs=logs,
                    signature=signature,
                    slot=slot,
                    block_time=block_time
                )
                self.logger.info(f"📊 Fallback: Found {len(parsed_events)} events from WebSocket logs", signature=signature)
            
            # Store events in database
            if parsed_events:
                await self._store_events(parsed_events)
                
                # 🔧 CRITICAL FIX: Process events through business handlers
                await self._process_events_handlers(parsed_events)
                
                # Send real-time notifications to WebSocket clients
                for event in parsed_events:
                    await self._send_realtime_notification(event)
            
            self.stats.events_processed += len(parsed_events)
            self.stats.last_event_time = datetime.utcnow()
            
        except Exception as e:
            self.logger.error("Error handling logs notification", error=str(e), signature=signature)
            self.stats.errors_encountered += 1
    
    async def _process_events_handlers(self, parsed_events: List[ParsedEvent]):
        """Process events through business handlers."""
        async with get_async_session() as db:
            try:
                for parsed_event in parsed_events:
                    # Map ALL event types to handlers (same as force_process_transaction.py)
                    handler_mapping = {
                        # Business events
                        "BusinessCreated": self.business_handlers.handle_business_created,
                        "BusinessCreatedInSlot": self.business_handlers.handle_business_created_in_slot,
                        "BusinessUpgraded": self.business_handlers.handle_business_upgraded,
                        "BusinessUpgradedInSlot": self.business_handlers.handle_business_upgraded_in_slot,
                        "BusinessSold": self.business_handlers.handle_business_sold,
                        "BusinessSoldFromSlot": self.business_handlers.handle_business_sold_from_slot,
                        "BusinessTransferred": self.business_handlers.handle_business_transferred,
                        "BusinessDeactivated": self.business_handlers.handle_business_deactivated,
                        
                        # Earnings events
                        "EarningsUpdated": self.earnings_handlers.handle_earnings_updated,
                        "EarningsClaimed": self.earnings_handlers.handle_earnings_claimed,
                        
                        # Player events  
                        "PlayerCreated": self.player_handlers.handle_player_created,
                        "SlotUnlocked": self.player_handlers.handle_slot_unlocked,
                        "PremiumSlotPurchased": self.player_handlers.handle_premium_slot_purchased,
                        
                        # Also support enum-style names (uppercase with underscores)
                        "BUSINESS_CREATED": self.business_handlers.handle_business_created,
                        "BUSINESS_CREATED_IN_SLOT": self.business_handlers.handle_business_created_in_slot,
                        "BUSINESS_UPGRADED": self.business_handlers.handle_business_upgraded,
                        "BUSINESS_UPGRADED_IN_SLOT": self.business_handlers.handle_business_upgraded_in_slot,
                        "BUSINESS_SOLD": self.business_handlers.handle_business_sold,
                        "BUSINESS_SOLD_FROM_SLOT": self.business_handlers.handle_business_sold_from_slot,
                        "EARNINGS_UPDATED": self.earnings_handlers.handle_earnings_updated,
                        "EARNINGS_CLAIMED": self.earnings_handlers.handle_earnings_claimed,
                        "PLAYER_CREATED": self.player_handlers.handle_player_created,
                    }
                    
                    event_type = parsed_event.event_type.value
                    handler = handler_mapping.get(event_type)
                    
                    if handler:
                        self.logger.info("🏃‍♂️ Processing event via handler", 
                                       event_type=event_type, 
                                       signature=parsed_event.signature)
                        await handler(db, parsed_event)
                        self.logger.info("✅ Event processed via handler", 
                                       event_type=event_type,
                                       signature=parsed_event.signature)
                    else:
                        self.logger.warning("⚠️ No handler for event type", 
                                          event_type=event_type)
                
                # Commit all changes
                await db.commit()
                self.logger.info("💾 Event handlers - all changes committed")
                
            except Exception as e:
                await db.rollback()
                self.logger.error("Failed to process events via handlers", error=str(e))
                raise
    
    async def _store_events(self, parsed_events: List[ParsedEvent]):
        """Store parsed events in database."""
        async with get_async_session() as db:
            try:
                for parsed_event in parsed_events:
                    # Map to database event type
                    db_event_type_mapping = {
                        "BusinessCreated": DBEventType.BUSINESS_CREATED,
                        "BusinessCreatedInSlot": DBEventType.BUSINESS_CREATED,  # Slot version
                        "BusinessUpgraded": DBEventType.BUSINESS_UPGRADED,
                        "BusinessSold": DBEventType.BUSINESS_SOLD,
                        "BusinessSoldFromSlot": DBEventType.BUSINESS_SOLD,  # Slot version
                        "PlayerCreated": DBEventType.PLAYER_CREATED,
                        "EarningsUpdated": DBEventType.EARNINGS_UPDATED,
                        "EarningsClaimed": DBEventType.EARNINGS_CLAIMED,
                    }
                    
                    db_event_type = db_event_type_mapping.get(parsed_event.event_type.value)
                    if not db_event_type:
                        self.logger.warning("Unknown event type", event_type=parsed_event.event_type.value)
                        continue
                    
                    # Extract player wallet
                    player_wallet = None
                    if parsed_event.data:
                        player_wallet = parsed_event.data.get("owner") or parsed_event.data.get("wallet")
                    
                    # Create event record
                    event = Event(
                        transaction_signature=parsed_event.signature,
                        slot=parsed_event.slot or 0,  # 🔧 FIX: Use 0 as fallback for None slot
                        block_time=parsed_event.block_time or datetime.utcnow(),  # 🔧 FIX: Use current time as fallback
                        event_type=db_event_type,
                        raw_data=parsed_event.raw_data,
                        parsed_data=parsed_event.data,
                        player_wallet=player_wallet,
                        processed_at=datetime.utcnow()
                    )
                    
                    db.add(event)
                    self.stats.events_stored += 1
                
                await db.commit()
                self.logger.info(f"✅ Stored {len(parsed_events)} events in database")
                
            except Exception as e:
                await db.rollback()
                self.logger.error("Failed to store events", error=str(e))
                raise
    
    async def _send_realtime_notification(self, parsed_event: ParsedEvent):
        """Send real-time notification to WebSocket clients."""
        try:
            if not self.notification_service:
                return
            
            # Create notification payload
            notification = {
                "type": "event",
                "event_type": parsed_event.event_type.value,
                "signature": parsed_event.signature,
                "slot": parsed_event.slot,
                "data": parsed_event.data,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send to all connected WebSocket clients
            await self.notification_service.broadcast_event(notification)
            
            self.logger.info("📡 Sent real-time notification", event_type=parsed_event.event_type.value)
            
        except Exception as e:
            self.logger.error("Failed to send real-time notification", error=str(e))
    
    async def _unsubscribe(self, subscription_type: str, subscription_id: int):
        """Unsubscribe from a WebSocket subscription."""
        try:
            if subscription_type == "program":
                method = "programUnsubscribe"
            elif subscription_type == "logs":
                method = "logsUnsubscribe"
            else:
                return
            
            request = {
                "jsonrpc": "2.0",
                "id": 999,
                "method": method,
                "params": [subscription_id]
            }
            
            await self.websocket.send(json.dumps(request))
            self.logger.info(f"Unsubscribed from {subscription_type}", subscription_id=subscription_id)
            
        except Exception as e:
            self.logger.error(f"Failed to unsubscribe from {subscription_type}", error=str(e))
    
    async def _reconnect_websocket(self):
        """Reconnect WebSocket and restore subscriptions."""
        try:
            self.logger.info("Attempting to reconnect WebSocket...")
            
            # Clear existing subscriptions
            self._subscriptions.clear()
            self.stats.subscriptions_active = 0
            
            # Reconnect
            await self._connect_websocket()
            
            # Restore subscriptions (send requests - responses handled in main loop)
            await self._send_program_subscription()
            await self._send_logs_subscription()
            
            self.logger.info("✅ WebSocket reconnected successfully")
            
        except Exception as e:
            self.logger.error("Failed to reconnect WebSocket", error=str(e))
            await asyncio.sleep(5)  # Wait before next attempt
    
    async def _periodic_health_check(self):
        """Periodic health check and statistics logging."""
        while self._running:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                if not self._running:
                    break
                
                self.logger.info(
                    "Real-time indexer health check",
                    stats=asdict(self.stats),
                    subscriptions=len(self._subscriptions),
                    websocket_connected=bool(self.websocket and not self.websocket.closed)
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Health check error", error=str(e))
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current indexer status."""
        return {
            "status": "running" if self._running else "stopped",
            "subscriptions_active": self.stats.subscriptions_active,
            "events_processed": self.stats.events_processed,
            "events_stored": self.stats.events_stored,
            "errors_encountered": self.stats.errors_encountered,
            "last_event_time": self.stats.last_event_time.isoformat() if self.stats.last_event_time else None,
            "websocket_connected": bool(self.websocket and not self.websocket.closed),
            "subscriptions": list(self._subscriptions.keys())
        }


# Global real-time indexer instance
_realtime_indexer: Optional[RealTimeIndexer] = None


async def get_realtime_indexer() -> RealTimeIndexer:
    """Get or create global real-time indexer instance."""
    global _realtime_indexer
    if _realtime_indexer is None:
        _realtime_indexer = RealTimeIndexer()
        await _realtime_indexer.initialize()
    return _realtime_indexer


async def shutdown_realtime_indexer():
    """Shutdown global real-time indexer instance."""
    global _realtime_indexer
    if _realtime_indexer:
        await _realtime_indexer.stop()
        _realtime_indexer = None
"""
Simple real-time notifier for UI updates only.

Replaced the complex WebSocket blockchain subscription system with a simple
notification-only service that supports our new signature processing flow.

This service provides:
- Simple WebSocket connections for UI notifications
- No blockchain subscriptions (signatures come from frontend)
- Clean separation: blockchain processing vs UI notifications
- Based on proven WebSocket notification infrastructure
"""

import asyncio
import structlog
from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from app.websocket.notification_service import get_notification_service
from app.core.config import settings


logger = structlog.get_logger(__name__)


@dataclass
class SimpleNotifierStats:
    """Statistics for simple real-time notifier."""
    start_time: Optional[datetime] = None
    notifications_sent: int = 0
    websocket_connections: int = 0
    errors_encountered: int = 0


class SimpleRealtimeNotifier:
    """
    Simple real-time notifier that only handles UI notifications.
    
    No blockchain subscriptions, no complex WebSocket parsing - just clean
    UI notifications when transactions are processed through our queue system.
    
    Architecture:
    - Frontend sends signature → API queue
    - SignatureProcessor processes in background  
    - This notifier sends WebSocket updates to UI
    - Clean, simple, reliable
    """
    
    def __init__(self):
        """Initialize the simple real-time notifier."""
        self.logger = logger.bind(service="simple_realtime_notifier")
        
        # State
        self._running = False
        self._should_stop = False
        self.stats = SimpleNotifierStats()
        self.notification_service: Optional[Any] = None
        
        self.logger.info("SimpleRealtimeNotifier initialized")
    
    async def initialize(self):
        """Initialize the simple notifier."""
        try:
            self.logger.info("Initializing simple real-time notifier")
            
            # Get notification service (WebSocket manager)
            self.notification_service = get_notification_service()
            
            self.stats.start_time = datetime.utcnow()
            
            self.logger.info("✅ Simple real-time notifier initialized successfully")
            
        except Exception as e:
            self.logger.error("Failed to initialize simple notifier", error=str(e))
            raise
    
    async def start(self):
        """Start the simple notifier (just initialization, no background tasks)."""
        try:
            self.logger.info("Starting simple real-time notifier")
            self._running = True
            self._should_stop = False
            
            # No background tasks needed - notifications are sent on-demand
            # by SignatureProcessor through the notification_service
            
            self.logger.info("✅ Simple real-time notifier started")
            
        except Exception as e:
            self.logger.error("Failed to start simple notifier", error=str(e))
            raise
    
    async def stop(self):
        """Stop the simple notifier."""
        self.logger.info("Stopping simple real-time notifier")
        
        self._should_stop = True
        self._running = False
        
        self.logger.info("Simple real-time notifier stopped")
    
    async def send_business_update(
        self, 
        user_wallet: str, 
        event_type: str, 
        business_data: Dict[str, Any]
    ):
        """
        Send business update notification to user.
        
        Args:
            user_wallet: User's wallet address
            event_type: Type of business event (created, upgraded, sold)
            business_data: Business data for the notification
        """
        try:
            if not self.notification_service:
                await self.initialize()
            
            # Send appropriate notification based on event type
            if event_type == "business_created":
                await self.notification_service.notify_business_created(
                    user_wallet, business_data
                )
            elif event_type == "business_upgraded":
                await self.notification_service.notify_business_upgraded(
                    user_wallet, business_data
                )
            elif event_type == "business_sold":
                await self.notification_service.notify_business_sold(
                    user_wallet, business_data
                )
            
            self.stats.notifications_sent += 1
            
            self.logger.info("🎯 Business update notification sent",
                           user_wallet=user_wallet,
                           event_type=event_type,
                           business_id=business_data.get("business_id"))
            
        except Exception as e:
            self.stats.errors_encountered += 1
            self.logger.error("Failed to send business update notification",
                            user_wallet=user_wallet,
                            event_type=event_type,
                            error=str(e))
    
    async def send_earnings_update(
        self, 
        user_wallet: str, 
        earnings_data: Dict[str, Any]
    ):
        """Send earnings update notification to user."""
        try:
            if not self.notification_service:
                await self.initialize()
            
            await self.notification_service.notify_earnings_updated(
                user_wallet, earnings_data
            )
            
            self.stats.notifications_sent += 1
            
            self.logger.info("💰 Earnings update notification sent",
                           user_wallet=user_wallet,
                           new_balance=earnings_data.get("earnings_balance"))
            
        except Exception as e:
            self.stats.errors_encountered += 1
            self.logger.error("Failed to send earnings update notification",
                            user_wallet=user_wallet,
                            error=str(e))
    
    async def send_player_update(
        self, 
        user_wallet: str, 
        player_data: Dict[str, Any]
    ):
        """Send player update notification to user."""
        try:
            if not self.notification_service:
                await self.initialize()
            
            await self.notification_service.notify_player_updated(
                user_wallet, player_data
            )
            
            self.stats.notifications_sent += 1
            
            self.logger.info("👤 Player update notification sent",
                           user_wallet=user_wallet)
            
        except Exception as e:
            self.stats.errors_encountered += 1
            self.logger.error("Failed to send player update notification",
                            user_wallet=user_wallet,
                            error=str(e))
    
    async def send_processing_status(
        self,
        signature: str,
        status: str,
        user_wallet: str,
        slot_index: Optional[int] = None,
        business_level: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None
    ):
        """
        Send transaction processing status to user.
        
        This is the main method for our new architecture - immediate feedback
        about transaction processing status.
        """
        try:
            if not self.notification_service:
                await self.initialize()
            
            await self.notification_service.notify_signature_processing(
                signature=signature,
                status=status,
                user_wallet=user_wallet,
                slot_index=slot_index,
                business_level=business_level,
                result=result
            )
            
            self.stats.notifications_sent += 1
            
            self.logger.info("🔄 Processing status notification sent",
                           signature=signature[:20] + "...",
                           status=status,
                           user_wallet=user_wallet,
                           slot_index=slot_index)
            
        except Exception as e:
            self.stats.errors_encountered += 1
            self.logger.error("Failed to send processing status notification",
                            signature=signature,
                            status=status,
                            user_wallet=user_wallet,
                            error=str(e))
    
    async def get_status(self) -> Dict[str, Any]:
        """Get current notifier status."""
        try:
            # Get WebSocket connection count from connection manager
            from app.websocket.connection_manager import connection_manager
            connection_count = len(connection_manager._connections)
            
            return {
                "running": self._running,
                "websocket_connections": connection_count,
                "stats": asdict(self.stats),
                "message": "Simple real-time notifier - UI notifications only"
            }
        except Exception as e:
            return {
                "running": self._running,
                "error": str(e),
                "stats": asdict(self.stats)
            }


# Global simple notifier instance
_simple_realtime_notifier: Optional[SimpleRealtimeNotifier] = None


async def get_simple_realtime_notifier() -> SimpleRealtimeNotifier:
    """Get or create global simple real-time notifier instance."""
    global _simple_realtime_notifier
    if _simple_realtime_notifier is None:
        _simple_realtime_notifier = SimpleRealtimeNotifier()
        await _simple_realtime_notifier.initialize()
    return _simple_realtime_notifier


async def shutdown_simple_realtime_notifier():
    """Shutdown the global simple real-time notifier."""
    global _simple_realtime_notifier
    if _simple_realtime_notifier:
        await _simple_realtime_notifier.stop()
        _simple_realtime_notifier = None
"""
WebSocket connection manager for handling real-time connections.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Set, Optional, Any
from fastapi import WebSocket, WebSocketDisconnect
from collections import defaultdict

from .schemas import (
    WebSocketMessage, 
    MessageType,
    ConnectionStatusMessage,
    ErrorMessage,
    WebSocketResponse
)

import structlog

logger = structlog.get_logger(__name__)


class Connection:
    """Represents a single WebSocket connection."""
    
    def __init__(self, websocket: WebSocket, wallet: str, client_id: str):
        self.websocket = websocket
        self.wallet = wallet
        self.client_id = client_id
        self.connected_at = datetime.utcnow()
        self.last_ping = datetime.utcnow()
        self.subscriptions: Set[MessageType] = set()
        self.filters: Dict[str, Any] = {}
        
    async def send_message(self, message: WebSocketMessage) -> bool:
        """Send a message to this connection."""
        try:
            await self.websocket.send_json(message.model_dump())
            return True
        except Exception as e:
            logger.error(
                "Failed to send message to connection",
                client_id=self.client_id,
                wallet=self.wallet,
                error=str(e)
            )
            return False
    
    async def send_error(self, error_code: str, error_message: str):
        """Send an error message to this connection."""
        error_msg = ErrorMessage(
            data={
                "code": error_code,
                "message": error_message
            }
        )
        await self.send_message(error_msg)
    
    def update_ping(self):
        """Update the last ping timestamp."""
        self.last_ping = datetime.utcnow()
    
    def add_subscription(self, event_type: MessageType, filters: Optional[Dict[str, Any]] = None):
        """Add a subscription for an event type."""
        self.subscriptions.add(event_type)
        if filters:
            self.filters.update(filters)
    
    def remove_subscription(self, event_type: MessageType):
        """Remove a subscription for an event type."""
        self.subscriptions.discard(event_type)
    
    def should_receive_message(self, message: WebSocketMessage) -> bool:
        """Check if this connection should receive a message based on subscriptions."""
        if message.type not in self.subscriptions:
            return False
        
        # Apply filters if any
        if self.filters:
            # For player-specific messages, check wallet filter
            if "wallet" in message.data and "wallet" in self.filters:
                return message.data["wallet"] == self.filters["wallet"]
        
        return True


class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        # Active connections by client_id
        self.connections: Dict[str, Connection] = {}
        # Connections grouped by wallet for efficient player-specific messaging
        self.wallet_connections: Dict[str, Set[str]] = defaultdict(set)
        # Subscription tracking
        self.subscription_map: Dict[MessageType, Set[str]] = defaultdict(set)
        # Background tasks
        self._background_tasks: Set[asyncio.Task] = set()
        self._cleanup_interval = 60  # seconds
        
    async def connect(self, websocket: WebSocket, wallet: str, client_id: str) -> Connection:
        """Accept a new WebSocket connection."""
        try:
            await websocket.accept()
            
            connection = Connection(websocket, wallet, client_id)
            
            # Store connection
            self.connections[client_id] = connection
            self.wallet_connections[wallet].add(client_id)
            
            # Send connection status
            status_msg = ConnectionStatusMessage(
                data={
                    "status": "connected",
                    "client_id": client_id,
                    "wallet": wallet,
                    "total_connections": len(self.connections)
                }
            )
            await connection.send_message(status_msg)
            
            logger.info(
                "WebSocket connection established",
                client_id=client_id,
                wallet=wallet,
                total_connections=len(self.connections)
            )
            
            # Start cleanup task if this is the first connection
            if len(self.connections) == 1:
                self._start_cleanup_task()
            
            return connection
            
        except Exception as e:
            logger.error(
                "Failed to establish WebSocket connection",
                client_id=client_id,
                wallet=wallet,
                error=str(e)
            )
            raise
    
    async def disconnect(self, client_id: str, code: int = 1000):
        """Disconnect a WebSocket connection."""
        if client_id not in self.connections:
            return
        
        connection = self.connections[client_id]
        wallet = connection.wallet
        
        try:
            # Remove from subscription tracking
            for event_type in connection.subscriptions:
                self.subscription_map[event_type].discard(client_id)
            
            # Remove from connection tracking
            self.wallet_connections[wallet].discard(client_id)
            if not self.wallet_connections[wallet]:
                del self.wallet_connections[wallet]
            
            del self.connections[client_id]
            
            # Close the websocket
            if connection.websocket.client_state.name != "DISCONNECTED":
                await connection.websocket.close(code=code)
            
            logger.info(
                "WebSocket connection closed",
                client_id=client_id,
                wallet=wallet,
                code=code,
                remaining_connections=len(self.connections)
            )
            
        except Exception as e:
            logger.error(
                "Error during WebSocket disconnection",
                client_id=client_id,
                wallet=wallet,
                error=str(e)
            )
        
        # Stop cleanup task if no connections remain
        if len(self.connections) == 0:
            self._stop_cleanup_task()
    
    async def send_to_wallet(self, wallet: str, message: WebSocketMessage) -> int:
        """Send a message to all connections for a specific wallet."""
        if wallet not in self.wallet_connections:
            return 0
        
        client_ids = list(self.wallet_connections[wallet])
        sent_count = 0
        
        for client_id in client_ids:
            if client_id in self.connections:
                connection = self.connections[client_id]
                if connection.should_receive_message(message):
                    success = await connection.send_message(message)
                    if success:
                        sent_count += 1
                    else:
                        # Connection failed, schedule for removal
                        await self.disconnect(client_id, code=1011)
        
        return sent_count
    
    async def broadcast_to_subscribers(self, message: WebSocketMessage) -> int:
        """Broadcast a message to all subscribers of the message type."""
        if message.type not in self.subscription_map:
            return 0
        
        client_ids = list(self.subscription_map[message.type])
        sent_count = 0
        
        for client_id in client_ids:
            if client_id in self.connections:
                connection = self.connections[client_id]
                if connection.should_receive_message(message):
                    success = await connection.send_message(message)
                    if success:
                        sent_count += 1
                    else:
                        # Connection failed, schedule for removal
                        await self.disconnect(client_id, code=1011)
        
        return sent_count
    
    async def broadcast_to_all(self, message: WebSocketMessage) -> int:
        """Broadcast a message to all connected clients."""
        client_ids = list(self.connections.keys())
        sent_count = 0
        
        for client_id in client_ids:
            connection = self.connections[client_id]
            if connection.should_receive_message(message):
                success = await connection.send_message(message)
                if success:
                    sent_count += 1
                else:
                    # Connection failed, schedule for removal
                    await self.disconnect(client_id, code=1011)
        
        return sent_count
    
    async def add_subscription(self, client_id: str, event_type: MessageType, filters: Optional[Dict[str, Any]] = None):
        """Add a subscription for a client."""
        if client_id not in self.connections:
            return False
        
        connection = self.connections[client_id]
        connection.add_subscription(event_type, filters)
        self.subscription_map[event_type].add(client_id)
        
        logger.debug(
            "Subscription added",
            client_id=client_id,
            event_type=event_type.value,
            filters=filters
        )
        
        return True
    
    async def remove_subscription(self, client_id: str, event_type: MessageType):
        """Remove a subscription for a client."""
        if client_id not in self.connections:
            return False
        
        connection = self.connections[client_id]
        connection.remove_subscription(event_type)
        self.subscription_map[event_type].discard(client_id)
        
        logger.debug(
            "Subscription removed",
            client_id=client_id,
            event_type=event_type.value
        )
        
        return True
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get current connection statistics."""
        return {
            "total_connections": len(self.connections),
            "connections_by_wallet": {
                wallet: len(client_ids) 
                for wallet, client_ids in self.wallet_connections.items()
            },
            "subscriptions_by_type": {
                event_type.value: len(client_ids)
                for event_type, client_ids in self.subscription_map.items()
            },
            "active_wallets": len(self.wallet_connections)
        }
    
    async def ping_all_connections(self):
        """Send ping to all connections to check health."""
        current_time = datetime.utcnow()
        failed_connections = []
        
        for client_id, connection in self.connections.items():
            try:
                # Send a simple ping message
                ping_msg = WebSocketMessage(
                    type=MessageType.CONNECTION_STATUS,
                    data={"ping": current_time.isoformat()}
                )
                success = await connection.send_message(ping_msg)
                if success:
                    connection.update_ping()
                else:
                    failed_connections.append(client_id)
            except Exception:
                failed_connections.append(client_id)
        
        # Clean up failed connections
        for client_id in failed_connections:
            await self.disconnect(client_id, code=1011)
        
        return len(self.connections) - len(failed_connections)
    
    def _start_cleanup_task(self):
        """Start the background cleanup task."""
        if not self._background_tasks:
            task = asyncio.create_task(self._cleanup_loop())
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)
    
    def _stop_cleanup_task(self):
        """Stop all background tasks."""
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        self._background_tasks.clear()
    
    async def _cleanup_loop(self):
        """Background task to clean up stale connections."""
        try:
            while self.connections:
                await asyncio.sleep(self._cleanup_interval)
                
                # Ping all connections to check health
                active_count = await self.ping_all_connections()
                
                logger.debug(
                    "Connection health check completed",
                    active_connections=active_count,
                    total_connections=len(self.connections)
                )
                
        except asyncio.CancelledError:
            logger.debug("Cleanup task cancelled")
        except Exception as e:
            logger.error("Error in cleanup loop", error=str(e))


# Global connection manager instance
connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    return connection_manager
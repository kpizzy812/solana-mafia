"""
WebSocket endpoint handler for real-time communication.
"""

import asyncio
import json
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import WebSocket, WebSocketDisconnect, Query, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.dependencies import validate_wallet_param
from app.utils.validation import is_valid_solana_address
from .auth import validate_websocket_permissions, get_connection_limits
from .connection_manager import connection_manager
from .schemas import (
    MessageType,
    SubscriptionRequest,
    PlayerUpdateMessage,
    EarningsUpdateMessage,
    WebSocketResponse,
    ErrorMessage
)

import structlog

logger = structlog.get_logger(__name__)


async def websocket_handler(
    websocket: WebSocket,
    wallet: str,
    client_id: Optional[str] = None
):
    """
    WebSocket endpoint for real-time player updates.
    
    Supports:
    - Real-time player earnings updates
    - Business creation/upgrade notifications
    - NFT transfer notifications
    - Custom event subscriptions
    """
    
    # Validate wallet address
    if not is_valid_solana_address(wallet):
        await websocket.close(code=4002, reason="Invalid wallet address")
        return
    
    # Generate client ID if not provided
    if not client_id:
        client_id = f"{wallet}_{uuid4().hex[:8]}"
    
    connection = None
    
    try:
        # Validate permissions
        if not await validate_websocket_permissions(wallet):
            await websocket.close(code=4003, reason="Insufficient permissions")
            return
        
        # Check connection limits
        limits = get_connection_limits(wallet)
        current_connections = len(connection_manager.wallet_connections.get(wallet, set()))
        
        if current_connections >= limits["max_connections_per_wallet"]:
            logger.warning(
                "WebSocket connection limit exceeded",
                wallet=wallet,
                current_connections=current_connections,
                limit=limits["max_connections_per_wallet"]
            )
            await websocket.close(code=4004, reason="Connection limit exceeded")
            return
        
        # Establish connection
        connection = await connection_manager.connect(websocket, wallet, client_id)
        
        # Default subscriptions for player updates
        await connection_manager.add_subscription(
            client_id, 
            MessageType.PLAYER_UPDATE,
            filters={"wallet": wallet}
        )
        await connection_manager.add_subscription(
            client_id,
            MessageType.EARNINGS_UPDATE,
            filters={"wallet": wallet}
        )
        await connection_manager.add_subscription(
            client_id,
            MessageType.BUSINESS_UPDATE,
            filters={"wallet": wallet}
        )
        await connection_manager.add_subscription(
            client_id,
            MessageType.NFT_UPDATE,
            filters={"wallet": wallet}
        )
        
        logger.info(
            "WebSocket client connected with default subscriptions",
            client_id=client_id,
            wallet=wallet
        )
        
        # Send initial player data
        await _send_initial_player_data(connection, wallet)
        
        # Listen for incoming messages
        while True:
            try:
                # Wait for client messages
                message = await websocket.receive_text()
                await _handle_client_message(connection, message)
                
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected", client_id=client_id, wallet=wallet)
                break
            except Exception as e:
                logger.error(
                    "Error processing WebSocket message",
                    client_id=client_id,
                    wallet=wallet,
                    error=str(e)
                )
                # Send error to client
                error_msg = ErrorMessage(
                    data={
                        "code": "MESSAGE_ERROR",
                        "message": f"Error processing message: {str(e)}"
                    }
                )
                await connection.send_message(error_msg)
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected during setup", wallet=wallet)
    except Exception as e:
        logger.error(
            "WebSocket connection error",
            client_id=client_id,
            wallet=wallet,
            error=str(e)
        )
    finally:
        # Clean up connection
        if connection:
            await connection_manager.disconnect(client_id)


async def _handle_client_message(connection, message_text: str):
    """Handle incoming client messages."""
    try:
        message_data = json.loads(message_text)
        message_type = message_data.get("type")
        
        if message_type == "subscribe":
            await _handle_subscription_request(connection, message_data)
        elif message_type == "unsubscribe":
            await _handle_unsubscription_request(connection, message_data)
        elif message_type == "ping":
            await _handle_ping(connection)
        else:
            logger.warning(
                "Unknown message type received",
                client_id=connection.client_id,
                message_type=message_type
            )
            
    except json.JSONDecodeError:
        logger.error(
            "Invalid JSON received from client",
            client_id=connection.client_id
        )
        error_msg = ErrorMessage(
            data={
                "code": "INVALID_JSON",
                "message": "Invalid JSON format in message"
            }
        )
        await connection.send_message(error_msg)
    except Exception as e:
        logger.error(
            "Error handling client message",
            client_id=connection.client_id,
            error=str(e)
        )


async def _handle_subscription_request(connection, message_data):
    """Handle subscription requests from clients."""
    try:
        event_types = message_data.get("events", [])
        filters = message_data.get("filters", {})
        
        for event_type_str in event_types:
            try:
                event_type = MessageType(event_type_str)
                await connection_manager.add_subscription(
                    connection.client_id,
                    event_type,
                    filters
                )
                logger.debug(
                    "Subscription added",
                    client_id=connection.client_id,
                    event_type=event_type.value
                )
            except ValueError:
                logger.warning(
                    "Invalid event type in subscription",
                    client_id=connection.client_id,
                    event_type=event_type_str
                )
        
        # Send confirmation as proper WebSocket message with type
        from .schemas import SubscriptionMessage
        response = SubscriptionMessage(
            data={
                "success": True,
                "message": "Subscriptions updated",
                "subscribed_events": event_types
            }
        )
        await connection.websocket.send_json(response.model_dump())
        
    except Exception as e:
        logger.error(
            "Error handling subscription request",
            client_id=connection.client_id,
            error=str(e)
        )


async def _handle_unsubscription_request(connection, message_data):
    """Handle unsubscription requests from clients."""
    try:
        event_types = message_data.get("events", [])
        
        for event_type_str in event_types:
            try:
                event_type = MessageType(event_type_str)
                await connection_manager.remove_subscription(
                    connection.client_id,
                    event_type
                )
                logger.debug(
                    "Subscription removed",
                    client_id=connection.client_id,
                    event_type=event_type.value
                )
            except ValueError:
                logger.warning(
                    "Invalid event type in unsubscription",
                    client_id=connection.client_id,
                    event_type=event_type_str
                )
        
        # Send confirmation as proper WebSocket message with type  
        from .schemas import SubscriptionMessage
        response = SubscriptionMessage(
            data={
                "success": True,
                "message": "Subscriptions updated", 
                "unsubscribed_events": event_types
            }
        )
        await connection.websocket.send_json(response.model_dump())
        
    except Exception as e:
        logger.error(
            "Error handling unsubscription request",
            client_id=connection.client_id,
            error=str(e)
        )


async def _handle_ping(connection):
    """Handle ping messages from clients."""
    connection.update_ping()
    from .schemas import ConnectionStatusMessage  
    response = ConnectionStatusMessage(
        data={
            "success": True,
            "message": "pong",
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    await connection.websocket.send_json(response.model_dump())


async def _send_initial_player_data(connection, wallet: str):
    """Send initial player data to a new connection."""
    try:
        # Import here to avoid circular imports
        from app.core.database import get_async_session, init_database
        from app.models.player import Player
        
        # WebSocket connected successfully - skip initial data load to avoid greenlet issues
        # Data will be sent when events occur via signature processor
        logger.info(
            "WebSocket client connected and ready for notifications",
            client_id=connection.client_id,
            wallet=wallet
        )
                
    except Exception as e:
        logger.warning(
            "Could not send initial player data, continuing without it",
            client_id=connection.client_id,
            wallet=wallet,
            error=str(e)
        )
        # Don't re-raise the error - WebSocket connection should continue working


async def get_websocket_stats():
    """Get WebSocket connection statistics."""
    stats = connection_manager.get_connection_stats()
    return JSONResponse(
        content={
            "success": True,
            "data": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Create FastAPI router for WebSocket endpoints
from fastapi import APIRouter

websocket_router = APIRouter()

# WebSocket endpoint wrapper to extract path parameter
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint wrapper that extracts wallet from path."""
    wallet = websocket.path_params.get("wallet")
    if not wallet:
        await websocket.close(code=4001, reason="Wallet parameter missing")
        return
    
    client_id = websocket.query_params.get("client_id")
    await websocket_handler(websocket, wallet, client_id)

# Add WebSocket endpoint
websocket_router.add_websocket_route("/ws/{wallet}", websocket_endpoint)

# Add HTTP endpoint for stats
websocket_router.add_api_route("/stats", get_websocket_stats, methods=["GET"])
"""
Main entry point for the WebSocket server.
Provides real-time communication for the game.
"""

import asyncio
import signal
from datetime import datetime

import uvicorn
from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging
from .websocket_handler import websocket_handler
from .connection_manager import get_connection_manager

import structlog

logger = structlog.get_logger(__name__)


def create_websocket_app() -> FastAPI:
    """Create FastAPI application for WebSocket server."""
    
    app = FastAPI(
        title="Solana Mafia WebSocket Server",
        description="Real-time communication for Solana Mafia game",
        version="1.0.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # WebSocket endpoint
    @app.websocket("/ws/{wallet}")
    async def websocket_endpoint(websocket: WebSocket, wallet: str):
        """WebSocket endpoint for real-time player updates."""
        client_id = websocket.query_params.get("client_id")
        await websocket_handler(websocket, wallet, client_id)
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        connection_manager = get_connection_manager()
        
        return {
            "status": "healthy",
            "service": "websocket",
            "timestamp": datetime.utcnow().isoformat(),
            "connections": connection_manager.get_connection_stats()
        }
    
    @app.get("/stats")
    async def websocket_stats():
        """WebSocket statistics endpoint."""
        connection_manager = get_connection_manager()
        
        return {
            "connections": connection_manager.get_connection_stats(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    @app.post("/notify")
    async def send_notification(request_data: dict):
        """HTTP endpoint for sending WebSocket notifications from other services."""
        from .schemas import WebSocketMessage, MessageType
        
        try:
            # Extract notification data
            notification_type = request_data.get("type", "signature_processing")
            user_wallet = request_data.get("user_wallet")
            data = request_data.get("data", {})
            
            if not user_wallet:
                return {"success": False, "error": "user_wallet is required"}
            
            # Create WebSocket message
            message = WebSocketMessage(
                type=MessageType.EVENT,
                data=data
            )
            
            # Send to specific wallet
            connection_manager = get_connection_manager()
            sent_count = await connection_manager.send_to_wallet(user_wallet, message)
            
            logger.info(
                "📡 HTTP notification sent via WebSocket",
                user_wallet=user_wallet,
                sent_to=sent_count,
                notification_type=notification_type
            )
            
            return {
                "success": True,
                "sent_to": sent_count,
                "message": f"Notification sent to {sent_count} connections"
            }
            
        except Exception as e:
            logger.error("Failed to send HTTP notification", error=str(e))
            return {"success": False, "error": str(e)}
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize WebSocket server."""
        logger.info("Starting WebSocket server")
        
        # Initialize database
        from app.core.database import init_database
        await init_database()
        logger.info("Database initialized for WebSocket server")
        
        # Initialize connection manager
        connection_manager = get_connection_manager()
        # Connection manager doesn't need explicit initialization
        
        logger.info("WebSocket server started successfully")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown."""
        logger.info("Shutting down WebSocket server")
        
        # Close all connections
        connection_manager = get_connection_manager()
        # Disconnect all active connections
        for client_id in list(connection_manager.connections.keys()):
            await connection_manager.disconnect(client_id)
        
        logger.info("WebSocket server shut down")
    
    return app


async def main():
    """Main function to run the WebSocket server."""
    setup_logging()
    
    app = create_websocket_app()
    
    # Configure Uvicorn
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=8001,
        log_level=settings.log_level.lower(),
        access_log=True,
        loop="uvloop" if not settings.is_development else "asyncio"
    )
    
    server = uvicorn.Server(config)
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        server.should_exit = True
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("Starting WebSocket server on http://0.0.0.0:8001")
        await server.serve()
    except Exception as e:
        logger.error("WebSocket server failed", error=str(e))
        raise


if __name__ == "__main__":
    asyncio.run(main())
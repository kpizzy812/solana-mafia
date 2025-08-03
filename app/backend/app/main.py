"""
Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.database import init_database, close_database
from app.api.middleware import add_middleware
from app.api.schemas.common import HealthCheckResponse, APIResponse
from app.api.routes import players, businesses, earnings, stats
from app.websocket.websocket_handler import websocket_handler, get_websocket_stats
from app.admin.admin_routes import admin_router

import structlog

# Setup logging
setup_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Solana Mafia Backend", version=settings.app_version)
    
    try:
        await init_database()
        logger.info("Database initialized successfully")
        
        # Initialize background services if needed
        if settings.is_production:
            logger.info("Production mode - background services would start here")
            
    except Exception as e:
        logger.error("Startup failed", error=str(e))
        raise
    
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    try:
        await close_database()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Shutdown error", error=str(e))
    
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Solana Mafia API",
    version=settings.app_version,
    description="""
    Backend API for Solana Mafia - a blockchain-based business simulation game.
    
    ## Features
    
    * **Player Management** - Create and manage player accounts
    * **Business Operations** - Create, upgrade, and sell businesses
    * **Earnings System** - Automatic earnings distribution and claiming
    * **NFT Integration** - Business ownership via NFTs
    * **Real-time Updates** - Live data from Solana blockchain
    * **WebSocket Support** - Real-time notifications and updates
    
    ## Authentication
    
    Use your Solana wallet address as a Bearer token for authentication:
    ```
    Authorization: Bearer <your-wallet-address>
    ```
    
    ## WebSocket Connection
    
    Connect to real-time updates:
    ```
    ws://localhost:8000/ws/{wallet_address}
    ```
    """,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add middleware
add_middleware(app)

# Health check endpoint
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    tags=["System"],
    summary="Health Check",
    description="Check API server health and service status"
)
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connectivity
        from app.core.database import get_async_session
        from sqlalchemy import text
        async with get_async_session() as db:
            await db.execute(text("SELECT 1"))
        
        return HealthCheckResponse(
            status="healthy",
            version=settings.app_version,
            services={
                "database": "healthy",
                "api": "healthy"
            }
        )
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "version": settings.app_version,
                "services": {
                    "database": "unhealthy",
                    "api": "healthy"
                },
                "error": str(e)
            }
        )

# Root endpoint
@app.get(
    "/",
    response_model=APIResponse,
    tags=["System"],
    summary="API Information",
    description="Get basic API information and status"
)
async def root():
    """Root endpoint with API information."""
    return APIResponse(
        message=f"Solana Mafia API v{settings.app_version} - Ready to serve!",
        data={
            "version": settings.app_version,
            "environment": settings.environment,
            "docs_url": "/docs" if settings.debug else None,
            "features": [
                "Player Management",
                "Business Operations", 
                "Earnings System",
                "NFT Integration",
                "Real-time Updates"
            ]
        }
    )

# Database health check
@app.get(
    "/health/db",
    tags=["System"],
    summary="Database Health Check",
    description="Check database connectivity and health"
)
async def database_health():
    """Database health check endpoint."""
    try:
        from app.core.database import get_async_session
        async with get_async_session() as db:
            await db.execute("SELECT 1")
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    except Exception as e:
        logger.error("Database health check failed", error=str(e))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e)
            }
        )

# Include API routers
app.include_router(
    players.router,
    prefix=f"{settings.api_v1_prefix}/players",
    tags=["Players"]
)

app.include_router(
    businesses.router,
    prefix=f"{settings.api_v1_prefix}/businesses",
    tags=["Businesses"]
)

app.include_router(
    earnings.router,
    prefix=f"{settings.api_v1_prefix}/earnings",
    tags=["Earnings"]
)

app.include_router(
    stats.router,
    prefix=f"{settings.api_v1_prefix}/stats",
    tags=["Statistics"]
)

# Admin endpoints
app.include_router(
    admin_router,
    prefix=f"{settings.api_v1_prefix}/admin",
    tags=["Admin"]
)

# WebSocket endpoints
@app.websocket("/ws/{wallet}")
async def websocket_endpoint(websocket, wallet: str, client_id: str = None):
    """WebSocket endpoint for real-time player updates."""
    await websocket_handler(websocket, wallet, client_id)

# WebSocket stats endpoint
@app.get(
    "/ws/stats",
    tags=["WebSocket"],
    summary="WebSocket Statistics",
    description="Get current WebSocket connection statistics"
)
async def websocket_stats():
    """Get WebSocket connection statistics."""
    return await get_websocket_stats()

logger.info("FastAPI application configured successfully")

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
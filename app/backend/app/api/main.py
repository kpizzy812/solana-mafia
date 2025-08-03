"""
Main FastAPI application for Solana Mafia backend.
Configures the API server with routes, middleware, and documentation.
"""

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

import structlog

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.middleware import add_middleware
from app.api.schemas.common import HealthCheckResponse, APIResponse
from app.api.routes import players, businesses, earnings, stats, tma
from app.indexer.event_indexer import get_event_indexer
from app.scheduler.earnings_scheduler import get_earnings_scheduler


logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Solana Mafia API server")
    
    # Initialize services
    try:
        if settings.is_production:
            # Start background services in production
            event_indexer = await get_event_indexer()
            earnings_scheduler = await get_earnings_scheduler()
            
            await event_indexer.start()
            await earnings_scheduler.start()
            
            logger.info("Background services started")
    except Exception as e:
        logger.error("Failed to start background services", error=str(e))
    
    yield
    
    # Shutdown
    logger.info("Shutting down Solana Mafia API server")
    
    try:
        if settings.is_production:
            # Stop background services
            from app.indexer.event_indexer import shutdown_event_indexer
            from app.scheduler.earnings_scheduler import shutdown_earnings_scheduler
            
            await shutdown_event_indexer()
            await shutdown_earnings_scheduler()
            
            logger.info("Background services stopped")
    except Exception as e:
        logger.error("Error during shutdown", error=str(e))


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    
    # Setup logging
    setup_logging()
    
    # App configuration
    app_config = {
        "title": "Solana Mafia API",
        "description": """
        Backend API for Solana Mafia - a blockchain-based business simulation game.
        
        ## Features
        
        * **Player Management** - Create and manage player accounts
        * **Business Operations** - Create, upgrade, and sell businesses
        * **Earnings System** - Automatic earnings distribution and claiming
        * **NFT Integration** - Business ownership via NFTs
        * **Real-time Updates** - Live data from Solana blockchain
        
        ## Authentication
        
        Two authentication methods are supported:
        
        **Wallet Authentication:**
        ```
        Authorization: Bearer <your-wallet-address>
        ```
        
        **Telegram Mini Apps Authentication:**
        ```
        Authorization: tma <telegram-init-data>
        ```
        
        ## Rate Limiting
        
        API is rate limited to ensure fair usage:
        - **100 requests per minute** per wallet/IP
        - Rate limit headers included in responses
        
        ## Error Handling
        
        All endpoints return consistent error responses with:
        - Error codes for programmatic handling
        - Human-readable messages
        - Additional details when available
        """,
        "version": settings.app_version,
        "lifespan": lifespan,
    }
    
    # Hide docs in production if configured
    if not settings.is_development and hasattr(settings, 'hide_docs') and settings.hide_docs:
        app_config["openapi_url"] = None
    
    app = FastAPI(**app_config)
    
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
            from app.core.database import get_db_session
            async with get_db_session() as db:
                await db.execute("SELECT 1")
            
            return HealthCheckResponse(
                status="healthy",
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
                "docs_url": "/docs" if not (hasattr(settings, 'hide_docs') and settings.hide_docs) else None,
                "features": [
                    "Player Management",
                    "Business Operations", 
                    "Earnings System",
                    "NFT Integration",
                    "Real-time Updates"
                ]
            }
        )
    
    # Include routers
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
    
    app.include_router(
        tma.router,
        prefix=f"{settings.api_v1_prefix}",
        tags=["Telegram Mini Apps"]
    )
    
    logger.info("FastAPI application created successfully")
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        log_level=settings.log_level.lower()
    )
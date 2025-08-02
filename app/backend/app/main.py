"""
Main FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.database import init_database, close_database

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Solana Mafia Backend", version=settings.app_version)
    await init_database()
    logger.info("Application startup complete")
    
    yield
    
    # Shutdown
    logger.info("Shutting down application")
    await close_database()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend service for Solana Mafia game",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Solana Mafia Backend API",
        "version": settings.app_version,
        "environment": settings.environment
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment
    }


@app.get("/health/db")
async def database_health():
    """Database health check."""
    from app.core.database import DatabaseManager
    
    is_healthy = await DatabaseManager.health_check()
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "database": "connected" if is_healthy else "disconnected"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
"""
Database configuration and session management.
Uses SQLAlchemy 2.0 with async support.
"""

from typing import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine
)
from sqlalchemy.orm import sessionmaker

from .config import settings, DatabaseConfig
from .logging import get_logger

logger = get_logger(__name__)

# Global engine and session maker
async_engine: AsyncEngine = None
async_session_maker: async_sessionmaker[AsyncSession] = None
sync_engine = None
sync_session_maker = None


async def init_database() -> None:
    """Initialize database connections and session makers."""
    global async_engine, async_session_maker, sync_engine, sync_session_maker
    
    logger.info("Initializing database connections")
    
    # Async engine for main application
    async_engine = create_async_engine(
        DatabaseConfig.get_database_url(async_driver=True),
        **DatabaseConfig.get_engine_config(),
        echo=settings.debug
    )
    
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    # Sync engine for migrations and admin tasks
    sync_engine = create_engine(
        DatabaseConfig.get_database_url(async_driver=False),
        **DatabaseConfig.get_engine_config(),
        echo=settings.debug
    )
    
    sync_session_maker = sessionmaker(
        sync_engine,
        expire_on_commit=False
    )
    
    logger.info("Database connections initialized")


async def close_database() -> None:
    """Close database connections."""
    global async_engine, sync_engine
    
    logger.info("Closing database connections")
    
    if async_engine:
        await async_engine.dispose()
    
    if sync_engine:
        sync_engine.dispose()
    
    logger.info("Database connections closed")


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session with automatic cleanup.
    
    Usage:
        async with get_async_session() as session:
            # Use session here
            pass
    """
    if not async_session_maker:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session():
    """
    Get a sync database session for migrations and admin tasks.
    
    Usage:
        with get_sync_session() as session:
            # Use session here
            pass
    """
    if not sync_session_maker:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    return sync_session_maker()


# Dependency for FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get database session.
    
    Usage in route:
        async def my_route(db: AsyncSession = Depends(get_db_session)):
            # Use db here
            pass
    """
    async with get_async_session() as session:
        yield session


class DatabaseManager:
    """Database manager for administrative operations."""
    
    @staticmethod
    async def create_tables() -> None:
        """Create all tables in the database."""
        from app.models.base import Base
        
        if not async_engine:
            raise RuntimeError("Database not initialized")
        
        logger.info("Creating database tables")
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
    
    @staticmethod
    async def drop_tables() -> None:
        """Drop all tables in the database."""
        from app.models.base import Base
        
        if not async_engine:
            raise RuntimeError("Database not initialized")
        
        logger.warning("Dropping all database tables")
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")
    
    @staticmethod
    async def health_check() -> bool:
        """Check database connectivity."""
        try:
            async with get_async_session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False
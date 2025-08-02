#!/usr/bin/env python3
"""
Simple test script to verify migration works.
"""

import asyncio
import sys
from pathlib import Path

# Add app to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.database import init_database, close_database, DatabaseManager

async def test_migration():
    """Test database migration and basic operations."""
    
    setup_logging()
    logger = get_logger(__name__)
    
    try:
        logger.info("Testing database migration...")
        
        # Initialize database
        await init_database()
        logger.info("✅ Database connection established")
        
        # Test health check
        is_healthy = await DatabaseManager.health_check()
        if is_healthy:
            logger.info("✅ Database health check passed")
        else:
            logger.error("❌ Database health check failed")
            return False
        
        logger.info("✅ Migration test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration test failed: {e}")
        return False
        
    finally:
        await close_database()
        logger.info("Database connection closed")


if __name__ == "__main__":
    success = asyncio.run(test_migration())
    sys.exit(0 if success else 1)
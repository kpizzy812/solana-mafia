"""
Main entry point for the indexer service.
Indexes Solana blockchain events and transactions for the game.
"""

import asyncio
import signal
from datetime import datetime, timedelta
from typing import Dict, Any

from app.core.config import settings
from app.core.database import get_db_session, init_database
from app.core.logging import setup_logging
from .event_indexer import EventIndexer
from .transaction_indexer import TransactionIndexer

import structlog

logger = structlog.get_logger(__name__)


class IndexerMain:
    """Main indexer service coordinator."""
    
    def __init__(self):
        self.event_indexer = None
        self.transaction_indexer = None
        self.running = False
        self.tasks = []
    
    async def initialize(self):
        """Initialize indexer components."""
        try:
            logger.info("Initializing indexer service")
            
            # Initialize database first
            await init_database()
            
            # Initialize indexers
            self.event_indexer = EventIndexer()
            self.transaction_indexer = TransactionIndexer()
            
            await self.event_indexer.initialize()
            await self.transaction_indexer.initialize()
            
            logger.info("Indexer service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize indexer", error=str(e))
            raise
    
    async def start(self):
        """Start the indexer service."""
        try:
            logger.info("Starting indexer service")
            
            self.running = True
            
            # Start event indexer
            event_task = asyncio.create_task(
                self.event_indexer.start()
            )
            self.tasks.append(event_task)
            
            # Start transaction indexer  
            transaction_task = asyncio.create_task(
                self.transaction_indexer.start()
            )
            self.tasks.append(transaction_task)
            
            # Add periodic health check
            health_check_task = asyncio.create_task(
                self._periodic_health_check()
            )
            self.tasks.append(health_check_task)
            
            logger.info("Indexer service started")
            
            # Wait for tasks
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error("Indexer service error", error=str(e))
            raise
    
    async def stop(self):
        """Stop the indexer service."""
        logger.info("Stopping indexer service")
        
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Stop indexers
        if self.event_indexer:
            await self.event_indexer.stop()
        
        if self.transaction_indexer:
            await self.transaction_indexer.stop()
        
        logger.info("Indexer service stopped")
    
    async def _periodic_health_check(self):
        """Periodic health check for indexer components."""
        while self.running:
            try:
                await asyncio.sleep(300)  # 5 minutes
                
                if not self.running:
                    break
                
                # Check indexer health
                event_health = await self.event_indexer.health_check()
                transaction_health = await self.transaction_indexer.health_check()
                
                logger.info(
                    "Indexer health check",
                    event_indexer=event_health,
                    transaction_indexer=transaction_health
                )
                
                # Restart components if needed
                if not event_health["healthy"]:
                    logger.warning("Restarting event indexer due to health check failure")
                    await self.event_indexer.restart()
                
                if not transaction_health["healthy"]:
                    logger.warning("Restarting transaction indexer due to health check failure")
                    await self.transaction_indexer.restart()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health check error", error=str(e))


async def main():
    """Main function to run the indexer service."""
    setup_logging()
    
    indexer = IndexerMain()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(indexer.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await indexer.initialize()
        await indexer.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error("Indexer service failed", error=str(e))
        raise
    finally:
        await indexer.stop()


if __name__ == "__main__":
    asyncio.run(main())
"""
Main entry point for the indexer service.
Now simplified to use SignatureProcessor-based architecture instead of complex WebSocket subscriptions.
"""

import asyncio
import signal
from datetime import datetime, timedelta
from typing import Dict, Any

from app.core.config import settings
from app.core.database import get_db_session, init_database
from app.core.logging import setup_logging
from .simple_realtime_notifier import SimpleRealtimeNotifier

import structlog

logger = structlog.get_logger(__name__)


class IndexerMain:
    """
    Simplified indexer service coordinator.
    
    Now uses SignatureProcessor architecture:
    - Frontend sends signatures to API
    - SignatureProcessor handles all blockchain processing
    - SimpleRealtimeNotifier handles UI notifications
    - No complex WebSocket blockchain subscriptions
    """
    
    def __init__(self):
        self.simple_notifier = None
        self.running = False
        self.tasks = []
    
    async def initialize(self):
        """Initialize simple notification components."""
        try:
            logger.info("🚀 Initializing simplified indexer service")
            
            # Initialize database first
            await init_database()
            
            # Initialize simple real-time notifier (UI only)
            self.simple_notifier = SimpleRealtimeNotifier()
            await self.simple_notifier.initialize()
            
            logger.info("✅ Simplified indexer service initialized successfully")
            
        except Exception as e:
            logger.error("❌ Failed to initialize simplified indexer", error=str(e))
            raise
    
    async def start(self):
        """Start the simplified indexer service."""
        try:
            logger.info("🚀 Starting simplified indexer service")
            
            self.running = True
            
            # Start simple real-time notifier (just WebSocket UI notifications)
            await self.simple_notifier.start()
            
            # Add periodic health check
            health_check_task = asyncio.create_task(
                self._periodic_health_check()
            )
            self.tasks.append(health_check_task)
            
            logger.info("✅ Simplified indexer service started - UI notifications ready")
            logger.info("📝 Note: Transaction processing handled by SignatureProcessor API")
            
            # Wait for health check task
            if self.tasks:
                await asyncio.gather(*self.tasks, return_exceptions=True)
            else:
                # Just keep running until stopped
                while self.running:
                    await asyncio.sleep(1)
            
        except Exception as e:
            logger.error("❌ Simplified indexer service error", error=str(e))
            raise
    
    async def stop(self):
        """Stop the simplified indexer service."""
        logger.info("⏹️ Stopping simplified indexer service")
        
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Stop simple notifier
        if self.simple_notifier:
            await self.simple_notifier.stop()
        
        logger.info("✅ Simplified indexer service stopped")
    
    async def _periodic_health_check(self):
        """Periodic health check for simplified indexer."""
        while self.running:
            try:
                await asyncio.sleep(300)  # 5 minutes
                
                if not self.running:
                    break
                
                # Check simple notifier health
                status = await self.simple_notifier.get_status()
                
                logger.info(
                    "📊 Simplified indexer health check",
                    status=status
                )
                
                # Log any issues
                if status.get("errors_encountered", 0) > 0:
                    logger.warning(f"⚠️ Errors encountered: {status.get('errors_encountered')}")
                
                # Log WebSocket connection status
                connection_count = status.get("websocket_connections", 0)
                logger.info(f"🔗 Active WebSocket connections: {connection_count}")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("❌ Health check error", error=str(e))


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
"""
Main entry point for the scheduler service.
Manages periodic earnings distribution and background tasks.
"""

import asyncio
import signal
from datetime import datetime, timedelta
from typing import Dict, Any

from app.core.config import settings
from app.core.database import get_db_session, init_database
from app.core.logging import setup_logging
from .earnings_scheduler import EarningsScheduler
from .task_scheduler import TaskScheduler

import structlog

logger = structlog.get_logger(__name__)


class SchedulerMain:
    """Main scheduler service coordinator."""
    
    def __init__(self):
        self.earnings_scheduler = None
        self.task_scheduler = None
        self.running = False
        self.tasks = []
    
    async def initialize(self):
        """Initialize scheduler components."""
        try:
            logger.info("Initializing scheduler service")
            
            # Initialize database first
            await init_database()
            
            # Initialize schedulers
            self.earnings_scheduler = EarningsScheduler()
            self.task_scheduler = TaskScheduler()
            
            await self.earnings_scheduler.initialize()
            await self.task_scheduler.initialize()
            
            logger.info("Scheduler service initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize scheduler", error=str(e))
            raise
    
    async def start(self):
        """Start the scheduler service."""
        try:
            logger.info("Starting scheduler service")
            
            self.running = True
            
            # Start earnings scheduler
            earnings_task = asyncio.create_task(
                self.earnings_scheduler.start()
            )
            self.tasks.append(earnings_task)
            
            # Start task scheduler
            task_scheduler_task = asyncio.create_task(
                self.task_scheduler.start()
            )
            self.tasks.append(task_scheduler_task)
            
            # Add periodic health check
            health_check_task = asyncio.create_task(
                self._periodic_health_check()
            )
            self.tasks.append(health_check_task)
            
            logger.info("Scheduler service started")
            
            # Wait for tasks
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error("Scheduler service error", error=str(e))
            raise
    
    async def stop(self):
        """Stop the scheduler service."""
        logger.info("Stopping scheduler service")
        
        self.running = False
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        # Stop schedulers
        if self.earnings_scheduler:
            await self.earnings_scheduler.stop()
        
        if self.task_scheduler:
            await self.task_scheduler.stop()
        
        logger.info("Scheduler service stopped")
    
    async def _periodic_health_check(self):
        """Periodic health check for scheduler components."""
        while self.running:
            try:
                await asyncio.sleep(300)  # 5 minutes
                
                if not self.running:
                    break
                
                # Check earnings scheduler health
                earnings_health = await self.earnings_scheduler.health_check()
                task_scheduler_health = await self.task_scheduler.health_check()
                
                logger.info(
                    "Scheduler health check",
                    earnings_scheduler=earnings_health,
                    task_scheduler=task_scheduler_health
                )
                
                # Restart components if needed
                if not earnings_health["healthy"]:
                    logger.warning("Restarting earnings scheduler due to health check failure")
                    await self.earnings_scheduler.restart()
                
                if not task_scheduler_health["healthy"]:
                    logger.warning("Restarting task scheduler due to health check failure")
                    await self.task_scheduler.restart()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health check error", error=str(e))


async def main():
    """Main function to run the scheduler service."""
    setup_logging()
    
    scheduler = SchedulerMain()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        asyncio.create_task(scheduler.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        await scheduler.initialize()
        await scheduler.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error("Scheduler service failed", error=str(e))
        raise
    finally:
        await scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
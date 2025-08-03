"""
Task scheduler for managing background tasks and periodic operations.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Callable, Optional

from app.core.database import get_async_session
from app.models.player import Player
from app.models.business import Business
from app.models.event import Event

import structlog

logger = structlog.get_logger(__name__)


class ScheduledTask:
    """Represents a scheduled task."""
    
    def __init__(
        self,
        name: str,
        func: Callable,
        interval_seconds: int,
        enabled: bool = True,
        run_immediately: bool = False
    ):
        self.name = name
        self.func = func
        self.interval_seconds = interval_seconds
        self.enabled = enabled
        self.last_run = None
        self.next_run = datetime.utcnow()
        self.run_count = 0
        self.error_count = 0
        self.last_error = None
        
        if not run_immediately:
            self.next_run = datetime.utcnow() + timedelta(seconds=interval_seconds)
    
    def should_run(self) -> bool:
        """Check if task should run now."""
        return self.enabled and datetime.utcnow() >= self.next_run
    
    def schedule_next_run(self):
        """Schedule the next run."""
        self.next_run = datetime.utcnow() + timedelta(seconds=self.interval_seconds)
    
    async def run(self):
        """Execute the task."""
        try:
            logger.debug(f"Running scheduled task: {self.name}")
            
            start_time = datetime.utcnow()
            await self.func()
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            self.last_run = start_time
            self.run_count += 1
            self.schedule_next_run()
            
            logger.debug(
                f"Task completed: {self.name}",
                duration=duration,
                run_count=self.run_count
            )
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            self.schedule_next_run()  # Still schedule next run
            
            logger.error(
                f"Task failed: {self.name}",
                error=str(e),
                error_count=self.error_count
            )
            raise


class TaskScheduler:
    """Manages scheduled background tasks."""
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self.loop_interval = 10  # Check every 10 seconds
    
    async def initialize(self):
        """Initialize the task scheduler with default tasks."""
        logger.info("Initializing task scheduler")
        
        # Add default tasks
        await self._register_default_tasks()
        
        logger.info(f"Task scheduler initialized with {len(self.tasks)} tasks")
    
    async def _register_default_tasks(self):
        """Register default periodic tasks."""
        
        # Database cleanup task - every hour
        self.register_task(
            "database_cleanup",
            self._cleanup_old_events,
            interval_seconds=3600,  # 1 hour
            enabled=True
        )
        
        # Player statistics update - every 30 minutes
        self.register_task(
            "player_stats_update",
            self._update_player_statistics,
            interval_seconds=1800,  # 30 minutes
            enabled=True
        )
        
        # Business statistics update - every 15 minutes
        self.register_task(
            "business_stats_update", 
            self._update_business_statistics,
            interval_seconds=900,  # 15 minutes
            enabled=True
        )
        
        # Global statistics calculation - every 5 minutes
        self.register_task(
            "global_stats_update",
            self._update_global_statistics,
            interval_seconds=300,  # 5 minutes
            enabled=True
        )
        
        # Cache warming task - every 2 hours
        self.register_task(
            "cache_warming",
            self._warm_cache,
            interval_seconds=7200,  # 2 hours
            enabled=True,
            run_immediately=True
        )
        
        # Health metrics collection - every minute
        self.register_task(
            "health_metrics",
            self._collect_health_metrics,
            interval_seconds=60,  # 1 minute
            enabled=True
        )
    
    def register_task(
        self,
        name: str,
        func: Callable,
        interval_seconds: int,
        enabled: bool = True,
        run_immediately: bool = False
    ):
        """Register a new scheduled task."""
        task = ScheduledTask(
            name=name,
            func=func,
            interval_seconds=interval_seconds,
            enabled=enabled,
            run_immediately=run_immediately
        )
        
        self.tasks[name] = task
        logger.info(f"Registered task: {name} (interval: {interval_seconds}s)")
    
    def enable_task(self, name: str):
        """Enable a task."""
        if name in self.tasks:
            self.tasks[name].enabled = True
            logger.info(f"Enabled task: {name}")
    
    def disable_task(self, name: str):
        """Disable a task."""
        if name in self.tasks:
            self.tasks[name].enabled = False
            logger.info(f"Disabled task: {name}")
    
    async def start(self):
        """Start the task scheduler."""
        logger.info("Starting task scheduler")
        self.running = True
        
        while self.running:
            try:
                await self._run_pending_tasks()
                await asyncio.sleep(self.loop_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Task scheduler loop error", error=str(e))
                await asyncio.sleep(self.loop_interval)
        
        logger.info("Task scheduler stopped")
    
    async def stop(self):
        """Stop the task scheduler."""
        logger.info("Stopping task scheduler")
        self.running = False
    
    async def restart(self):
        """Restart the task scheduler."""
        await self.stop()
        await self.start()
    
    async def _run_pending_tasks(self):
        """Run all pending tasks."""
        pending_tasks = [
            task for task in self.tasks.values()
            if task.should_run()
        ]
        
        if pending_tasks:
            logger.debug(f"Running {len(pending_tasks)} pending tasks")
            
            # Run tasks concurrently
            task_coroutines = [task.run() for task in pending_tasks]
            results = await asyncio.gather(*task_coroutines, return_exceptions=True)
            
            # Log any exceptions
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Task failed: {pending_tasks[i].name}",
                        error=str(result)
                    )
    
    async def health_check(self) -> Dict[str, Any]:
        """Get health status of task scheduler."""
        total_tasks = len(self.tasks)
        enabled_tasks = sum(1 for task in self.tasks.values() if task.enabled)
        tasks_with_errors = sum(1 for task in self.tasks.values() if task.error_count > 0)
        
        task_statuses = {}
        for name, task in self.tasks.items():
            task_statuses[name] = {
                "enabled": task.enabled,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "next_run": task.next_run.isoformat(),
                "run_count": task.run_count,
                "error_count": task.error_count,
                "last_error": task.last_error
            }
        
        return {
            "healthy": self.running and tasks_with_errors < total_tasks * 0.5,
            "running": self.running,
            "total_tasks": total_tasks,
            "enabled_tasks": enabled_tasks,
            "tasks_with_errors": tasks_with_errors,
            "tasks": task_statuses
        }
    
    # Task implementations
    async def _cleanup_old_events(self):
        """Clean up old events from database."""
        cutoff_date = datetime.utcnow() - timedelta(days=30)  # Keep 30 days
        
        async with get_async_session() as session:
            # This would delete old events, but for now just log
            logger.info(f"Would cleanup events older than {cutoff_date}")
            # In production: DELETE FROM events WHERE created_at < cutoff_date
    
    async def _update_player_statistics(self):
        """Update player statistics cache."""
        logger.info("Updating player statistics")
        # This would calculate and cache player stats
        
    async def _update_business_statistics(self):
        """Update business statistics cache."""
        logger.info("Updating business statistics")
        # This would calculate and cache business stats
        
    async def _update_global_statistics(self):
        """Update global statistics cache."""
        logger.info("Updating global statistics")
        # This would calculate global game statistics
        
    async def _warm_cache(self):
        """Warm frequently accessed cache entries."""
        try:
            from app.cache import get_cache_service
            
            cache_service = await get_cache_service()
            
            # Warm global stats
            await cache_service.cache_global_stats({
                "total_players": 0,
                "total_businesses": 0,
                "total_volume": 0,
                "updated_at": datetime.utcnow().isoformat()
            })
            
            # Warm leaderboards
            await cache_service.cache_leaderboard("net_worth", 10, [])
            await cache_service.cache_leaderboard("businesses_count", 10, [])
            
            logger.info("Cache warming completed")
            
        except Exception as e:
            logger.error("Cache warming failed", error=str(e))
    
    async def _collect_health_metrics(self):
        """Collect system health metrics."""
        # This would collect CPU, memory, database metrics
        logger.debug("Collecting health metrics")
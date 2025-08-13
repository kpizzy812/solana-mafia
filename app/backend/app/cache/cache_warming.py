"""
Cache warming and preloading strategies.
Provides intelligent cache warming based on usage patterns and priorities.
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from .cache_service import get_cache_service
from .cache_keys import get_cache_key_builder
from .business_cache import get_business_cache_manager
from .stats_cache import get_stats_cache_manager

import structlog

logger = structlog.get_logger(__name__)


class WarmingPriority(str, Enum):
    """Priority levels for cache warming."""
    CRITICAL = "critical"    # Must be warmed immediately
    HIGH = "high"           # Warm ASAP
    MEDIUM = "medium"       # Warm when convenient
    LOW = "low"             # Warm during low activity


class WarmingStrategy(str, Enum):
    """Cache warming strategies."""
    IMMEDIATE = "immediate"      # Warm immediately
    SCHEDULED = "scheduled"      # Warm at specific times
    PREDICTIVE = "predictive"    # Warm based on usage patterns
    ON_DEMAND = "on_demand"      # Warm when requested


@dataclass
class WarmingTask:
    """Represents a cache warming task."""
    name: str
    func: Callable
    priority: WarmingPriority
    strategy: WarmingStrategy
    estimated_duration: int  # seconds
    dependencies: List[str] = None
    schedule_times: List[str] = None  # HH:MM format
    last_run: Optional[datetime] = None
    success_count: int = 0
    error_count: int = 0
    average_duration: float = 0.0
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.schedule_times is None:
            self.schedule_times = []


class CacheWarmingManager:
    """Manages cache warming and preloading operations."""
    
    def __init__(self):
        self.cache_service = None
        self.key_builder = None
        self.business_cache = None
        self.nft_cache = None
        self.stats_cache = None
        
        self.warming_tasks: Dict[str, WarmingTask] = {}
        self.running = False
        self.warming_history = []
        
        # Warming metrics
        self.metrics = {
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "total_duration": 0.0,
            "last_run": None,
            "tasks_by_priority": {}
        }
    
    async def initialize(self):
        """Initialize cache warming manager."""
        self.cache_service = await get_cache_service()
        self.key_builder = get_cache_key_builder()
        self.business_cache = await get_business_cache_manager()
        # self.nft_cache = await get_nft_cache_manager()  # NFT functionality removed
        self.stats_cache = await get_stats_cache_manager()
        
        # Register default warming tasks
        await self._register_default_tasks()
        
        logger.info("Cache warming manager initialized", tasks=len(self.warming_tasks))
    
    async def _register_default_tasks(self):
        """Register default cache warming tasks."""
        
        # Critical tasks - must be available immediately
        self.register_task(WarmingTask(
            name="global_stats",
            func=self._warm_global_stats,
            priority=WarmingPriority.CRITICAL,
            strategy=WarmingStrategy.IMMEDIATE,
            estimated_duration=10,
            schedule_times=["00:00", "06:00", "12:00", "18:00"]
        ))
        
        self.register_task(WarmingTask(
            name="leaderboards",
            func=self._warm_leaderboards,
            priority=WarmingPriority.CRITICAL,
            strategy=WarmingStrategy.IMMEDIATE,
            estimated_duration=15,
            dependencies=["global_stats"],
            schedule_times=["00:05", "06:05", "12:05", "18:05"]
        ))
        
        # High priority tasks
        self.register_task(WarmingTask(
            name="business_metrics",
            func=self._warm_business_metrics,
            priority=WarmingPriority.HIGH,
            strategy=WarmingStrategy.SCHEDULED,
            estimated_duration=20,
            schedule_times=["00:15", "12:15"]
        ))
        
        self.register_task(WarmingTask(
            name="active_players",
            func=self._warm_active_players,
            priority=WarmingPriority.HIGH,
            strategy=WarmingStrategy.PREDICTIVE,
            estimated_duration=30,
            schedule_times=["01:00", "13:00"]
        ))
        
        # Medium priority tasks
        self.register_task(WarmingTask(
            name="popular_businesses",
            func=self._warm_popular_businesses,
            priority=WarmingPriority.MEDIUM,
            strategy=WarmingStrategy.SCHEDULED,
            estimated_duration=45,
            schedule_times=["02:00", "14:00"]
        ))
        
        self.register_task(WarmingTask(
            name="nft_metadata",
            func=self._warm_nft_metadata,
            priority=WarmingPriority.MEDIUM,
            strategy=WarmingStrategy.PREDICTIVE,
            estimated_duration=60,
            schedule_times=["03:00"]
        ))
        
        # Low priority tasks
        self.register_task(WarmingTask(
            name="historical_data",
            func=self._warm_historical_data,
            priority=WarmingPriority.LOW,
            strategy=WarmingStrategy.SCHEDULED,
            estimated_duration=120,
            schedule_times=["04:00"]
        ))
        
        self.register_task(WarmingTask(
            name="analytics_cache",
            func=self._warm_analytics_cache,
            priority=WarmingPriority.LOW,
            strategy=WarmingStrategy.SCHEDULED,
            estimated_duration=90,
            schedule_times=["05:00"]
        ))
    
    def register_task(self, task: WarmingTask):
        """Register a new warming task."""
        self.warming_tasks[task.name] = task
        
        # Update metrics
        priority = task.priority.value
        if priority not in self.metrics["tasks_by_priority"]:
            self.metrics["tasks_by_priority"][priority] = 0
        self.metrics["tasks_by_priority"][priority] += 1
        
        logger.debug(f"Registered warming task: {task.name}", priority=task.priority.value)
    
    async def warm_immediately(self, task_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Warm specified tasks immediately."""
        if task_names is None:
            task_names = list(self.warming_tasks.keys())
        
        logger.info("Starting immediate cache warming", tasks=task_names)
        start_time = datetime.utcnow()
        
        results = {}
        
        # Sort tasks by priority
        tasks_to_run = []
        for task_name in task_names:
            if task_name in self.warming_tasks:
                tasks_to_run.append(self.warming_tasks[task_name])
        
        tasks_to_run.sort(key=lambda t: self._priority_order(t.priority))
        
        # Run tasks respecting dependencies
        for task in tasks_to_run:
            try:
                # Check dependencies
                if not await self._check_dependencies(task):
                    results[task.name] = {
                        "success": False,
                        "error": "Dependencies not met",
                        "duration": 0
                    }
                    continue
                
                # Run task
                task_start = datetime.utcnow()
                await task.func()
                duration = (datetime.utcnow() - task_start).total_seconds()
                
                # Update task metrics
                task.last_run = task_start
                task.success_count += 1
                task.average_duration = (
                    (task.average_duration * (task.success_count - 1) + duration) / 
                    task.success_count
                )
                
                results[task.name] = {
                    "success": True,
                    "duration": duration,
                    "run_count": task.success_count
                }
                
                logger.debug(f"Task completed: {task.name}", duration=duration)
                
            except Exception as e:
                task.error_count += 1
                results[task.name] = {
                    "success": False,
                    "error": str(e),
                    "duration": 0
                }
                logger.error(f"Task failed: {task.name}", error=str(e))
        
        total_duration = (datetime.utcnow() - start_time).total_seconds()
        
        # Update global metrics
        self.metrics["total_runs"] += 1
        self.metrics["total_duration"] += total_duration
        self.metrics["last_run"] = start_time.isoformat()
        
        successful_tasks = sum(1 for r in results.values() if r["success"])
        self.metrics["successful_runs"] += successful_tasks
        self.metrics["failed_runs"] += len(results) - successful_tasks
        
        logger.info(
            "Immediate warming completed",
            total_duration=total_duration,
            successful=successful_tasks,
            failed=len(results) - successful_tasks
        )
        
        return {
            "success": True,
            "total_duration": total_duration,
            "tasks": results,
            "summary": {
                "total": len(results),
                "successful": successful_tasks,
                "failed": len(results) - successful_tasks
            }
        }
    
    async def warm_by_priority(self, max_priority: WarmingPriority) -> Dict[str, Any]:
        """Warm tasks up to specified priority level."""
        priority_order = [
            WarmingPriority.CRITICAL,
            WarmingPriority.HIGH,
            WarmingPriority.MEDIUM,
            WarmingPriority.LOW
        ]
        
        max_index = priority_order.index(max_priority)
        priorities_to_warm = priority_order[:max_index + 1]
        
        tasks_to_warm = [
            task.name for task in self.warming_tasks.values()
            if task.priority in priorities_to_warm
        ]
        
        return await self.warm_immediately(tasks_to_warm)
    
    async def warm_predictive(self, usage_patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Warm cache based on predicted usage patterns."""
        logger.info("Starting predictive cache warming")
        
        # Analyze usage patterns and determine what to warm
        predicted_tasks = await self._analyze_usage_patterns(usage_patterns)
        
        return await self.warm_immediately(predicted_tasks)
    
    async def _analyze_usage_patterns(self, patterns: Dict[str, Any]) -> List[str]:
        """Analyze usage patterns to predict what should be warmed."""
        tasks_to_warm = []
        
        # Always warm critical tasks
        tasks_to_warm.extend([
            task.name for task in self.warming_tasks.values()
            if task.priority == WarmingPriority.CRITICAL
        ])
        
        # Analyze patterns for other tasks
        if patterns.get("high_player_activity", False):
            tasks_to_warm.extend(["active_players", "leaderboards"])
        
        if patterns.get("high_trading_volume", False):
            tasks_to_warm.extend(["business_metrics", "popular_businesses"])
        
        if patterns.get("new_players", 0) > 10:
            tasks_to_warm.extend(["global_stats", "business_metrics"])
        
        if patterns.get("peak_hours", False):
            tasks_to_warm.extend(["nft_metadata", "active_players"])
        
        return list(set(tasks_to_warm))  # Remove duplicates
    
    async def _check_dependencies(self, task: WarmingTask) -> bool:
        """Check if task dependencies are met."""
        for dep_name in task.dependencies:
            if dep_name in self.warming_tasks:
                dep_task = self.warming_tasks[dep_name]
                # Check if dependency was run recently (within last hour)
                if (dep_task.last_run is None or 
                    datetime.utcnow() - dep_task.last_run > timedelta(hours=1)):
                    return False
        return True
    
    def _priority_order(self, priority: WarmingPriority) -> int:
        """Get numeric order for priority."""
        order = {
            WarmingPriority.CRITICAL: 0,
            WarmingPriority.HIGH: 1,
            WarmingPriority.MEDIUM: 2,
            WarmingPriority.LOW: 3
        }
        return order.get(priority, 999)
    
    # Warming task implementations
    async def _warm_global_stats(self):
        """Warm global statistics cache."""
        await self.stats_cache.get_global_overview()
        logger.debug("Global stats warmed")
    
    async def _warm_leaderboards(self):
        """Warm leaderboard caches."""
        metrics = ["net_worth", "businesses_count", "earnings_total", "trading_volume"]
        limits = [10, 25, 50]
        
        tasks = []
        for metric in metrics:
            for limit in limits:
                tasks.append(self.stats_cache.get_leaderboard(metric, limit))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.debug("Leaderboards warmed")
    
    async def _warm_business_metrics(self):
        """Warm business metrics cache."""
        # Warm general metrics
        await self.stats_cache.get_business_metrics()
        
        # Warm metrics for each business type
        tasks = []
        for business_type in range(10):  # Assuming 10 business types
            tasks.append(self.stats_cache.get_business_metrics(business_type))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.debug("Business metrics warmed")
    
    async def _warm_active_players(self):
        """Warm active player data."""
        # This would query for most active players and warm their data
        # For now, just warm some statistics
        await self.stats_cache.get_earnings_stats("24h")
        await self.stats_cache.get_network_activity(24)
        logger.debug("Active players data warmed")
    
    async def _warm_popular_businesses(self):
        """Warm popular business data."""
        # This would identify and warm popular business data
        # For now, warm business metrics by type
        tasks = []
        for business_type in range(5):  # Most popular types
            tasks.append(self.stats_cache.get_business_metrics(business_type))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.debug("Popular businesses warmed")
    
    async def _warm_nft_metadata(self):
        """Warm NFT metadata cache."""
        # This would warm frequently accessed NFT metadata
        # For now, just log the operation
        logger.debug("NFT metadata warming (placeholder)")
    
    async def _warm_historical_data(self):
        """Warm historical data cache."""
        # Warm various time periods
        periods = ["7d", "30d", "90d"]
        
        tasks = []
        for period in periods:
            tasks.append(self.stats_cache.get_earnings_stats(period))
            tasks.append(self.stats_cache.get_trading_volume(period))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.debug("Historical data warmed")
    
    async def _warm_analytics_cache(self):
        """Warm analytics and reporting cache."""
        await self.stats_cache.get_game_progression()
        await self.stats_cache.get_network_activity(168)  # 7 days
        logger.debug("Analytics cache warmed")
    
    async def get_warming_status(self) -> Dict[str, Any]:
        """Get current warming status and metrics."""
        task_statuses = {}
        for name, task in self.warming_tasks.items():
            task_statuses[name] = {
                "priority": task.priority.value,
                "strategy": task.strategy.value,
                "last_run": task.last_run.isoformat() if task.last_run else None,
                "success_count": task.success_count,
                "error_count": task.error_count,
                "average_duration": task.average_duration,
                "estimated_duration": task.estimated_duration,
                "dependencies": task.dependencies,
                "schedule_times": task.schedule_times
            }
        
        return {
            "metrics": self.metrics,
            "tasks": task_statuses,
            "total_tasks": len(self.warming_tasks),
            "running": self.running
        }
    
    async def schedule_warming(self):
        """Run scheduled warming based on time."""
        current_time = datetime.utcnow().strftime("%H:%M")
        
        tasks_to_run = []
        for task in self.warming_tasks.values():
            if current_time in task.schedule_times:
                tasks_to_run.append(task.name)
        
        if tasks_to_run:
            logger.info(f"Running scheduled warming tasks: {tasks_to_run}")
            return await self.warm_immediately(tasks_to_run)
        
        return {"success": True, "message": "No scheduled tasks at this time"}


# Global cache warming manager instance
_warming_manager: Optional[CacheWarmingManager] = None


async def get_warming_manager() -> CacheWarmingManager:
    """Get global cache warming manager instance."""
    global _warming_manager
    
    if _warming_manager is None:
        _warming_manager = CacheWarmingManager()
        await _warming_manager.initialize()
    
    return _warming_manager


# Convenience functions
async def warm_critical_cache():
    """Warm critical cache immediately."""
    manager = await get_warming_manager()
    return await manager.warm_by_priority(WarmingPriority.CRITICAL)


async def warm_all_cache():
    """Warm all cache levels."""
    manager = await get_warming_manager()
    return await manager.warm_by_priority(WarmingPriority.LOW)


async def warm_for_peak_hours():
    """Warm cache for peak usage hours."""
    manager = await get_warming_manager()
    return await manager.warm_predictive({
        "peak_hours": True,
        "high_player_activity": True,
        "high_trading_volume": True
    })
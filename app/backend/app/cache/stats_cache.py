"""
Global statistics caching with TTL optimization.
Provides intelligent caching for game statistics, leaderboards, and metrics.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
from enum import Enum

from .cache_service import get_cache_service
from .cache_keys import get_cache_key_builder
from .cache_decorators import cached, cache_stats_data

import structlog

logger = structlog.get_logger(__name__)


class StatsCacheLevel(str, Enum):
    """Cache levels for different statistics types."""
    REAL_TIME = "real_time"      # 30 seconds TTL
    FAST = "fast"                # 5 minutes TTL
    MEDIUM = "medium"            # 15 minutes TTL
    SLOW = "slow"                # 1 hour TTL
    DAILY = "daily"              # 24 hours TTL


class StatsType(str, Enum):
    """Types of statistics we cache."""
    GLOBAL_OVERVIEW = "global_overview"
    PLAYER_LEADERBOARD = "player_leaderboard"
    BUSINESS_METRICS = "business_metrics"
    EARNINGS_STATS = "earnings_stats"
    TRADING_VOLUME = "trading_volume"
    NETWORK_ACTIVITY = "network_activity"
    GAME_PROGRESSION = "game_progression"


class GlobalStatsCacheManager:
    """Manages caching for global game statistics."""
    
    def __init__(self):
        self.cache_service = None
        self.key_builder = None
        
        # Define TTL for different cache levels
        self.ttl_config = {
            StatsCacheLevel.REAL_TIME: 30,      # 30 seconds
            StatsCacheLevel.FAST: 300,          # 5 minutes
            StatsCacheLevel.MEDIUM: 900,        # 15 minutes
            StatsCacheLevel.SLOW: 3600,         # 1 hour
            StatsCacheLevel.DAILY: 86400        # 24 hours
        }
        
        # Define cache levels for different stats types
        self.stats_cache_levels = {
            StatsType.GLOBAL_OVERVIEW: StatsCacheLevel.FAST,
            StatsType.PLAYER_LEADERBOARD: StatsCacheLevel.MEDIUM,
            StatsType.BUSINESS_METRICS: StatsCacheLevel.MEDIUM,
            StatsType.EARNINGS_STATS: StatsCacheLevel.FAST,
            StatsType.TRADING_VOLUME: StatsCacheLevel.REAL_TIME,
            StatsType.NETWORK_ACTIVITY: StatsCacheLevel.REAL_TIME,
            StatsType.GAME_PROGRESSION: StatsCacheLevel.SLOW
        }
    
    async def initialize(self):
        """Initialize stats cache manager."""
        self.cache_service = await get_cache_service()
        self.key_builder = get_cache_key_builder()
        
        logger.info("Global stats cache manager initialized")
    
    def _get_ttl_for_stats_type(self, stats_type: StatsType) -> int:
        """Get appropriate TTL for statistics type."""
        cache_level = self.stats_cache_levels.get(stats_type, StatsCacheLevel.MEDIUM)
        return self.ttl_config[cache_level]
    
    # Global overview statistics
    @cache_stats_data(ttl=300)  # 5 minutes
    async def get_global_overview(self) -> Dict[str, Any]:
        """Get global game overview statistics."""
        return await self._calculate_global_overview()
    
    async def _calculate_global_overview(self) -> Dict[str, Any]:
        """Calculate global overview statistics."""
        # This would query the database for real statistics
        # For now, return mock data structure
        return {
            "total_players": 0,
            "active_players_24h": 0,
            "total_businesses": 0,
            "total_business_value": 0,
            "total_earnings_claimed": 0,
            "average_business_level": 0,
            "total_transactions": 0,
            "market_cap": 0,
            "calculated_at": datetime.utcnow().isoformat(),
            "cache_level": StatsCacheLevel.FAST.value
        }
    
    async def cache_global_overview(self, stats: Dict[str, Any]) -> bool:
        """Cache global overview statistics."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            ttl = self._get_ttl_for_stats_type(StatsType.GLOBAL_OVERVIEW)
            key = self.key_builder.global_stats_key()
            
            await self.cache_service.set(key, stats, ttl=ttl, cache_type="stats")
            
            logger.debug("Global overview cached", ttl=ttl)
            return True
            
        except Exception as e:
            logger.error("Failed to cache global overview", error=str(e))
            return False
    
    # Leaderboard statistics
    async def get_leaderboard(
        self, 
        metric: str, 
        limit: int = 10,
        time_period: str = "all_time"
    ) -> List[Dict[str, Any]]:
        """Get leaderboard for specific metric."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            key = self.key_builder.leaderboard_key(f"{metric}_{time_period}", limit)
            cached_leaderboard = await self.cache_service.get(key)
            
            if cached_leaderboard:
                logger.debug(f"Cache hit for leaderboard: {metric}")
                return cached_leaderboard
            
            # Calculate leaderboard
            leaderboard = await self._calculate_leaderboard(metric, limit, time_period)
            
            # Cache with appropriate TTL
            ttl = self._get_ttl_for_stats_type(StatsType.PLAYER_LEADERBOARD)
            await self.cache_service.set(key, leaderboard, ttl=ttl, cache_type="stats")
            
            return leaderboard
            
        except Exception as e:
            logger.error("Failed to get leaderboard", metric=metric, error=str(e))
            return []
    
    async def _calculate_leaderboard(
        self, 
        metric: str, 
        limit: int, 
        time_period: str
    ) -> List[Dict[str, Any]]:
        """Calculate leaderboard for specific metric."""
        # This would query the database for real leaderboard data
        return []
    
    # Business metrics
    async def get_business_metrics(self, business_type: Optional[int] = None) -> Dict[str, Any]:
        """Get business-related metrics."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            cache_key = self.key_builder.build(
                "business_metrics", 
                business_type if business_type is not None else "all"
            )
            
            cached_metrics = await self.cache_service.get(cache_key)
            if cached_metrics:
                logger.debug("Cache hit for business metrics")
                return cached_metrics
            
            # Calculate metrics
            metrics = await self._calculate_business_metrics(business_type)
            
            # Cache with appropriate TTL
            ttl = self._get_ttl_for_stats_type(StatsType.BUSINESS_METRICS)
            await self.cache_service.set(cache_key, metrics, ttl=ttl, cache_type="stats")
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get business metrics", error=str(e))
            return {}
    
    async def _calculate_business_metrics(self, business_type: Optional[int]) -> Dict[str, Any]:
        """Calculate business metrics."""
        # This would calculate real business metrics
        return {
            "business_type": business_type,
            "total_count": 0,
            "average_level": 0,
            "total_value": 0,
            "average_earnings": 0,
            "most_popular_level": 1,
            "upgrade_rate": 0,
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    # Earnings statistics
    async def get_earnings_stats(self, time_period: str = "24h") -> Dict[str, Any]:
        """Get earnings-related statistics."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            cache_key = self.key_builder.build("earnings_stats", time_period)
            cached_stats = await self.cache_service.get(cache_key)
            
            if cached_stats:
                logger.debug(f"Cache hit for earnings stats: {time_period}")
                return cached_stats
            
            # Calculate earnings stats
            stats = await self._calculate_earnings_stats(time_period)
            
            # Cache with appropriate TTL
            ttl = self._get_ttl_for_stats_type(StatsType.EARNINGS_STATS)
            await self.cache_service.set(cache_key, stats, ttl=ttl, cache_type="stats")
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get earnings stats", error=str(e))
            return {}
    
    async def _calculate_earnings_stats(self, time_period: str) -> Dict[str, Any]:
        """Calculate earnings statistics."""
        # This would calculate real earnings statistics
        return {
            "time_period": time_period,
            "total_earnings_claimed": 0,
            "total_players_claimed": 0,
            "average_claim_amount": 0,
            "highest_claim": 0,
            "total_treasury_fees": 0,
            "claim_frequency": 0,
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    # Trading volume statistics
    async def get_trading_volume(self, time_period: str = "24h") -> Dict[str, Any]:
        """Get trading volume statistics."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            cache_key = self.key_builder.build("trading_volume", time_period)
            cached_volume = await self.cache_service.get(cache_key)
            
            if cached_volume:
                logger.debug(f"Cache hit for trading volume: {time_period}")
                return cached_volume
            
            # Calculate trading volume
            volume = await self._calculate_trading_volume(time_period)
            
            # Cache with real-time TTL (30 seconds)
            ttl = self._get_ttl_for_stats_type(StatsType.TRADING_VOLUME)
            await self.cache_service.set(cache_key, volume, ttl=ttl, cache_type="stats")
            
            return volume
            
        except Exception as e:
            logger.error("Failed to get trading volume", error=str(e))
            return {}
    
    async def _calculate_trading_volume(self, time_period: str) -> Dict[str, Any]:
        """Calculate trading volume statistics."""
        # This would calculate real trading volume
        return {
            "time_period": time_period,
            "total_volume": 0,
            "total_trades": 0,
            "average_trade_size": 0,
            "highest_sale": 0,
            "volume_by_business_type": {},
            "price_trends": [],
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    # Network activity statistics
    async def get_network_activity(self, hours: int = 24) -> Dict[str, Any]:
        """Get network activity statistics."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            cache_key = self.key_builder.build("network_activity", hours)
            cached_activity = await self.cache_service.get(cache_key)
            
            if cached_activity:
                logger.debug(f"Cache hit for network activity: {hours}h")
                return cached_activity
            
            # Calculate network activity
            activity = await self._calculate_network_activity(hours)
            
            # Cache with real-time TTL
            ttl = self._get_ttl_for_stats_type(StatsType.NETWORK_ACTIVITY)
            await self.cache_service.set(cache_key, activity, ttl=ttl, cache_type="stats")
            
            return activity
            
        except Exception as e:
            logger.error("Failed to get network activity", error=str(e))
            return {}
    
    async def _calculate_network_activity(self, hours: int) -> Dict[str, Any]:
        """Calculate network activity statistics."""
        # This would calculate real network activity
        return {
            "time_period_hours": hours,
            "total_transactions": 0,
            "unique_players": 0,
            "transaction_types": {},
            "average_gas_cost": 0,
            "success_rate": 100.0,
            "peak_activity_hour": 0,
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    # Game progression statistics
    async def get_game_progression(self) -> Dict[str, Any]:
        """Get game progression statistics."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            cache_key = self.key_builder.build("game_progression")
            cached_progression = await self.cache_service.get(cache_key)
            
            if cached_progression:
                logger.debug("Cache hit for game progression")
                return cached_progression
            
            # Calculate game progression
            progression = await self._calculate_game_progression()
            
            # Cache with slow TTL (1 hour)
            ttl = self._get_ttl_for_stats_type(StatsType.GAME_PROGRESSION)
            await self.cache_service.set(cache_key, progression, ttl=ttl, cache_type="stats")
            
            return progression
            
        except Exception as e:
            logger.error("Failed to get game progression", error=str(e))
            return {}
    
    async def _calculate_game_progression(self) -> Dict[str, Any]:
        """Calculate game progression statistics."""
        # This would calculate real game progression data
        return {
            "player_distribution_by_level": {},
            "business_distribution_by_level": {},
            "average_time_to_first_business": 0,
            "average_upgrade_time": 0,
            "retention_rates": {},
            "progression_bottlenecks": [],
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    # Cache management methods
    async def warm_stats_cache(self) -> Dict[str, Any]:
        """Warm all statistics caches."""
        logger.info("Starting stats cache warming")
        
        warming_tasks = []
        
        # Warm global overview
        warming_tasks.append(self.get_global_overview())
        
        # Warm popular leaderboards
        leaderboard_metrics = ["net_worth", "businesses_count", "earnings_total"]
        for metric in leaderboard_metrics:
            warming_tasks.append(self.get_leaderboard(metric, 10))
            warming_tasks.append(self.get_leaderboard(metric, 25))
        
        # Warm business metrics
        warming_tasks.append(self.get_business_metrics())
        for business_type in range(5):  # Common business types
            warming_tasks.append(self.get_business_metrics(business_type))
        
        # Warm time-based stats
        warming_tasks.append(self.get_earnings_stats("24h"))
        warming_tasks.append(self.get_earnings_stats("7d"))
        warming_tasks.append(self.get_trading_volume("24h"))
        warming_tasks.append(self.get_network_activity(24))
        warming_tasks.append(self.get_game_progression())
        
        try:
            # Execute all warming tasks concurrently
            import asyncio
            results = await asyncio.gather(*warming_tasks, return_exceptions=True)
            
            successful = sum(1 for result in results if not isinstance(result, Exception))
            
            logger.info(
                "Stats cache warming completed",
                total_tasks=len(warming_tasks),
                successful=successful,
                failed=len(warming_tasks) - successful
            )
            
            return {
                "success": True,
                "total_tasks": len(warming_tasks),
                "successful": successful,
                "failed": len(warming_tasks) - successful
            }
            
        except Exception as e:
            logger.error("Stats cache warming failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    async def get_cache_health(self) -> Dict[str, Any]:
        """Get health status of stats cache."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            # Check cache availability
            cache_stats = await self.cache_service.get_cache_stats()
            
            # Check specific stats cache keys
            test_keys = [
                self.key_builder.global_stats_key(),
                self.key_builder.leaderboard_key("net_worth", 10),
                self.key_builder.build("business_metrics", "all")
            ]
            
            key_statuses = {}
            for key in test_keys:
                exists = await self.cache_service.exists(key)
                ttl = await self.cache_service.ttl(key) if exists else -1
                key_statuses[key] = {"exists": bool(exists), "ttl": ttl}
            
            return {
                "healthy": True,
                "cache_stats": cache_stats,
                "key_statuses": key_statuses,
                "ttl_config": self.ttl_config,
                "stats_cache_levels": {k.value: v.value for k, v in self.stats_cache_levels.items()}
            }
            
        except Exception as e:
            logger.error("Failed to get cache health", error=str(e))
            return {"healthy": False, "error": str(e)}


# Global stats cache manager instance
_stats_cache_manager: Optional[GlobalStatsCacheManager] = None


async def get_stats_cache_manager() -> GlobalStatsCacheManager:
    """Get global stats cache manager instance."""
    global _stats_cache_manager
    
    if _stats_cache_manager is None:
        _stats_cache_manager = GlobalStatsCacheManager()
        await _stats_cache_manager.initialize()
    
    return _stats_cache_manager


# Convenience functions for common operations
async def get_cached_global_overview() -> Dict[str, Any]:
    """Get cached global overview statistics."""
    manager = await get_stats_cache_manager()
    return await manager.get_global_overview()


async def get_cached_leaderboard(metric: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Get cached leaderboard."""
    manager = await get_stats_cache_manager()
    return await manager.get_leaderboard(metric, limit)


async def warm_all_stats() -> Dict[str, Any]:
    """Warm all statistics caches."""
    manager = await get_stats_cache_manager()
    return await manager.warm_stats_cache()
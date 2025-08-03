"""
High-level caching service with automatic serialization and invalidation.
"""

import json
import pickle
import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Callable, Type
from dataclasses import dataclass, asdict
from enum import Enum

from .redis_client import RedisClient, get_redis_client
from .cache_keys import CacheKeyBuilder, get_cache_key_builder

import structlog

logger = structlog.get_logger(__name__)


class SerializationMethod(str, Enum):
    """Serialization methods for cache data."""
    JSON = "json"
    PICKLE = "pickle"
    STRING = "string"


@dataclass
class CacheConfig:
    """Cache configuration for different data types."""
    ttl_seconds: int = 3600  # 1 hour default
    serialization: SerializationMethod = SerializationMethod.JSON
    compress: bool = False
    namespace: Optional[str] = None


class CacheService:
    """High-level caching service with automatic serialization."""
    
    def __init__(self, redis_client: RedisClient, key_builder: CacheKeyBuilder):
        self.redis = redis_client
        self.keys = key_builder
        
        # Default cache configurations
        self.default_configs = {
            "player": CacheConfig(ttl_seconds=1800),  # 30 minutes
            "business": CacheConfig(ttl_seconds=3600),  # 1 hour
            "stats": CacheConfig(ttl_seconds=300),     # 5 minutes
            "events": CacheConfig(ttl_seconds=600),    # 10 minutes
            "api_response": CacheConfig(ttl_seconds=900),  # 15 minutes
            "metrics": CacheConfig(ttl_seconds=60),    # 1 minute
            "search": CacheConfig(ttl_seconds=1800),   # 30 minutes
        }
    
    def _get_config(self, cache_type: str) -> CacheConfig:
        """Get cache configuration for type."""
        return self.default_configs.get(cache_type, CacheConfig())
    
    def _serialize(self, data: Any, method: SerializationMethod) -> str:
        """Serialize data based on method."""
        try:
            if method == SerializationMethod.JSON:
                return json.dumps(data, default=str, ensure_ascii=False)
            elif method == SerializationMethod.PICKLE:
                return pickle.dumps(data).hex()
            else:  # STRING
                return str(data)
        except Exception as e:
            logger.error("Serialization failed", method=method.value, error=str(e))
            raise
    
    def _deserialize(self, data: str, method: SerializationMethod) -> Any:
        """Deserialize data based on method."""
        try:
            if method == SerializationMethod.JSON:
                return json.loads(data)
            elif method == SerializationMethod.PICKLE:
                return pickle.loads(bytes.fromhex(data))
            else:  # STRING
                return data
        except Exception as e:
            logger.error("Deserialization failed", method=method.value, error=str(e))
            return None
    
    async def set(
        self,
        key: str,
        data: Any,
        ttl: Optional[int] = None,
        cache_type: str = "default"
    ) -> bool:
        """Set cache data with automatic serialization."""
        try:
            config = self._get_config(cache_type)
            ttl = ttl or config.ttl_seconds
            
            serialized_data = self._serialize(data, config.serialization)
            
            # Store with metadata
            cache_entry = {
                "data": serialized_data,
                "method": config.serialization.value,
                "cached_at": datetime.utcnow().isoformat(),
                "ttl": ttl
            }
            
            cache_value = json.dumps(cache_entry)
            success = await self.redis.set(key, cache_value, ex=ttl)
            
            if success:
                logger.debug(
                    "Cache set successful",
                    key=key,
                    cache_type=cache_type,
                    ttl=ttl,
                    size=len(cache_value)
                )
            
            return success
            
        except Exception as e:
            logger.error("Cache set failed", key=key, error=str(e))
            return False
    
    async def get(self, key: str) -> Any:
        """Get cache data with automatic deserialization."""
        try:
            cached_value = await self.redis.get(key)
            if not cached_value:
                return None
            
            try:
                cache_entry = json.loads(cached_value)
                method = SerializationMethod(cache_entry["method"])
                data = self._deserialize(cache_entry["data"], method)
                
                logger.debug(
                    "Cache get successful",
                    key=key,
                    cached_at=cache_entry.get("cached_at"),
                    method=method.value
                )
                
                return data
                
            except (json.JSONDecodeError, KeyError):
                # Fallback for simple string values
                return cached_value
                
        except Exception as e:
            logger.error("Cache get failed", key=key, error=str(e))
            return None
    
    async def delete(self, *keys: str) -> int:
        """Delete cache keys."""
        try:
            deleted = await self.redis.delete(*keys)
            logger.debug("Cache delete successful", keys=keys, deleted=deleted)
            return deleted
        except Exception as e:
            logger.error("Cache delete failed", keys=keys, error=str(e))
            return 0
    
    async def exists(self, *keys: str) -> int:
        """Check if cache keys exist."""
        return await self.redis.exists(*keys)
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for cache key."""
        return await self.redis.expire(key, seconds)
    
    async def ttl(self, key: str) -> int:
        """Get time to live for cache key."""
        return await self.redis.ttl(key)
    
    # Player caching methods
    async def cache_player(self, wallet: str, player_data: Dict[str, Any]) -> bool:
        """Cache player data."""
        key = self.keys.player_key(wallet)
        return await self.set(key, player_data, cache_type="player")
    
    async def get_cached_player(self, wallet: str) -> Optional[Dict[str, Any]]:
        """Get cached player data."""
        key = self.keys.player_key(wallet)
        return await self.get(key)
    
    async def cache_player_stats(self, wallet: str, stats_data: Dict[str, Any]) -> bool:
        """Cache player statistics."""
        key = self.keys.player_stats_key(wallet)
        return await self.set(key, stats_data, cache_type="stats")
    
    async def get_cached_player_stats(self, wallet: str) -> Optional[Dict[str, Any]]:
        """Get cached player statistics."""
        key = self.keys.player_stats_key(wallet)
        return await self.get(key)
    
    async def cache_player_businesses(self, wallet: str, businesses_data: List[Dict[str, Any]]) -> bool:
        """Cache player businesses."""
        key = self.keys.player_businesses_key(wallet)
        return await self.set(key, businesses_data, cache_type="business")
    
    async def get_cached_player_businesses(self, wallet: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached player businesses."""
        key = self.keys.player_businesses_key(wallet)
        return await self.get(key)
    
    async def cache_player_earnings(self, wallet: str, earnings_data: Dict[str, Any]) -> bool:
        """Cache player earnings."""
        key = self.keys.player_earnings_key(wallet)
        return await self.set(key, earnings_data, cache_type="player")
    
    async def get_cached_player_earnings(self, wallet: str) -> Optional[Dict[str, Any]]:
        """Get cached player earnings."""
        key = self.keys.player_earnings_key(wallet)
        return await self.get(key)
    
    # Business caching methods
    async def cache_business(self, business_id: str, business_data: Dict[str, Any]) -> bool:
        """Cache business data."""
        key = self.keys.business_key(business_id)
        return await self.set(key, business_data, cache_type="business")
    
    async def get_cached_business(self, business_id: str) -> Optional[Dict[str, Any]]:
        """Get cached business data."""
        key = self.keys.business_key(business_id)
        return await self.get(key)
    
    # Statistics caching methods
    async def cache_global_stats(self, stats_data: Dict[str, Any]) -> bool:
        """Cache global statistics."""
        key = self.keys.global_stats_key()
        return await self.set(key, stats_data, cache_type="stats")
    
    async def get_cached_global_stats(self) -> Optional[Dict[str, Any]]:
        """Get cached global statistics."""
        key = self.keys.global_stats_key()
        return await self.get(key)
    
    async def cache_leaderboard(self, metric: str, limit: int, leaderboard_data: List[Dict[str, Any]]) -> bool:
        """Cache leaderboard data."""
        key = self.keys.leaderboard_key(metric, limit)
        return await self.set(key, leaderboard_data, cache_type="stats")
    
    async def get_cached_leaderboard(self, metric: str, limit: int) -> Optional[List[Dict[str, Any]]]:
        """Get cached leaderboard data."""
        key = self.keys.leaderboard_key(metric, limit)
        return await self.get(key)
    
    # Events caching methods
    async def cache_recent_events(self, limit: int, event_type: Optional[str], events_data: List[Dict[str, Any]]) -> bool:
        """Cache recent events."""
        key = self.keys.recent_events_key(limit, event_type)
        return await self.set(key, events_data, cache_type="events")
    
    async def get_cached_recent_events(self, limit: int, event_type: Optional[str]) -> Optional[List[Dict[str, Any]]]:
        """Get cached recent events."""
        key = self.keys.recent_events_key(limit, event_type)
        return await self.get(key)
    
    # API response caching methods
    async def cache_api_response(self, endpoint: str, params: Dict[str, Any], response_data: Any) -> bool:
        """Cache API response."""
        key = self.keys.api_response_key(endpoint, params)
        return await self.set(key, response_data, cache_type="api_response")
    
    async def get_cached_api_response(self, endpoint: str, params: Dict[str, Any]) -> Any:
        """Get cached API response."""
        key = self.keys.api_response_key(endpoint, params)
        return await self.get(key)
    
    # Metrics caching methods
    async def cache_system_metrics(self, metrics_data: Dict[str, Any]) -> bool:
        """Cache system metrics."""
        key = self.keys.system_metrics_key()
        return await self.set(key, metrics_data, cache_type="metrics")
    
    async def get_cached_system_metrics(self) -> Optional[Dict[str, Any]]:
        """Get cached system metrics."""
        key = self.keys.system_metrics_key()
        return await self.get(key)
    
    async def cache_websocket_stats(self, stats_data: Dict[str, Any]) -> bool:
        """Cache WebSocket statistics."""
        key = self.keys.websocket_stats_key()
        return await self.set(key, stats_data, cache_type="metrics")
    
    async def get_cached_websocket_stats(self) -> Optional[Dict[str, Any]]:
        """Get cached WebSocket statistics."""
        key = self.keys.websocket_stats_key()
        return await self.get(key)
    
    # Bulk operations
    async def invalidate_player_cache(self, wallet: str) -> int:
        """Invalidate all cache entries for a player."""
        pattern = self.keys.player_pattern(wallet)
        keys_to_delete = await self.redis.keys(pattern)
        
        if keys_to_delete:
            deleted = await self.delete(*keys_to_delete)
            logger.info("Player cache invalidated", wallet=wallet, keys_deleted=deleted)
            return deleted
        
        return 0
    
    async def invalidate_business_cache(self, business_id: str) -> int:
        """Invalidate all cache entries for a business."""
        pattern = self.keys.business_pattern(business_id)
        keys_to_delete = await self.redis.keys(pattern)
        
        if keys_to_delete:
            deleted = await self.delete(*keys_to_delete)
            logger.info("Business cache invalidated", business_id=business_id, keys_deleted=deleted)
            return deleted
        
        return 0
    
    async def invalidate_stats_cache(self) -> int:
        """Invalidate all statistics cache."""
        patterns = [
            self.keys.global_stats_key(),
            self.keys.build("leaderboard", "*"),
            self.keys.build("top_players", "*"),
            self.keys.build("stats", "*")
        ]
        
        total_deleted = 0
        for pattern in patterns:
            if "*" in pattern:
                keys_to_delete = await self.redis.keys(pattern)
                if keys_to_delete:
                    deleted = await self.delete(*keys_to_delete)
                    total_deleted += deleted
            else:
                deleted = await self.delete(pattern)
                total_deleted += deleted
        
        logger.info("Statistics cache invalidated", keys_deleted=total_deleted)
        return total_deleted
    
    async def warm_cache(self, cache_warming_tasks: List[Callable]) -> None:
        """Warm cache with predefined tasks."""
        try:
            logger.info("Starting cache warming", tasks=len(cache_warming_tasks))
            
            # Run warming tasks concurrently
            tasks = [asyncio.create_task(task()) for task in cache_warming_tasks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful = sum(1 for result in results if not isinstance(result, Exception))
            logger.info("Cache warming completed", successful=successful, total=len(tasks))
            
        except Exception as e:
            logger.error("Cache warming failed", error=str(e))
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache usage statistics."""
        try:
            # Get Redis info
            info = await self.redis.client.info()
            
            # Count keys by type
            all_keys = await self.redis.keys(f"{self.keys.prefix}*")
            key_counts = {}
            
            for key in all_keys:
                key_parts = key.split(self.keys.separator)
                if len(key_parts) >= 2:
                    key_type = key_parts[1] if len(key_parts) > 1 else "unknown"
                    key_counts[key_type] = key_counts.get(key_type, 0) + 1
            
            return {
                "total_keys": len(all_keys),
                "keys_by_type": key_counts,
                "memory_usage": info.get("used_memory_human", "0B"),
                "connected_clients": info.get("connected_clients", 0),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": round(
                    info.get("keyspace_hits", 0) / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1) * 100, 2
                )
            }
            
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {}


# Global cache service instance
_cache_service: Optional[CacheService] = None


async def get_cache_service() -> CacheService:
    """Get global cache service instance."""
    global _cache_service
    
    if _cache_service is None:
        redis_client = await get_redis_client()
        key_builder = get_cache_key_builder()
        _cache_service = CacheService(redis_client, key_builder)
    
    return _cache_service
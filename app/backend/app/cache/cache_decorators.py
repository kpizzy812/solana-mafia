"""
Cache decorators for automatic caching of function results.
"""

import asyncio
import functools
from typing import Any, Callable, Optional, Dict, List, Union
from datetime import datetime

from .cache_service import get_cache_service
from .cache_keys import get_cache_key_builder

import structlog

logger = structlog.get_logger(__name__)


def cached(
    ttl: int = 3600,
    cache_type: str = "default",
    key_prefix: Optional[str] = None,
    skip_cache: bool = False,
    invalidate_on_error: bool = False
):
    """
    Decorator for caching function results.
    
    Args:
        ttl: Time to live in seconds
        cache_type: Cache configuration type
        key_prefix: Custom key prefix
        skip_cache: Skip cache and always execute function
        invalidate_on_error: Invalidate cache if function raises error
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            if skip_cache:
                return await func(*args, **kwargs)
            
            try:
                cache_service = await get_cache_service()
                key_builder = get_cache_key_builder()
                
                # Build cache key
                func_name = func.__name__
                if key_prefix:
                    cache_key = key_builder.build(key_prefix, func_name, args, kwargs)
                else:
                    cache_key = key_builder.build("func", func_name, args, kwargs)
                
                # Try to get from cache
                cached_result = await cache_service.get(cache_key)
                if cached_result is not None:
                    logger.debug(
                        "Cache hit",
                        function=func_name,
                        key=cache_key,
                        cache_type=cache_type
                    )
                    return cached_result
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Cache result
                await cache_service.set(cache_key, result, ttl=ttl, cache_type=cache_type)
                
                logger.debug(
                    "Function result cached",
                    function=func_name,
                    key=cache_key,
                    ttl=ttl
                )
                
                return result
                
            except Exception as e:
                logger.error(
                    "Cache operation failed",
                    function=func_name,
                    error=str(e)
                )
                
                if invalidate_on_error:
                    try:
                        await cache_service.delete(cache_key)
                    except:
                        pass
                
                # Execute function anyway
                return await func(*args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            if skip_cache:
                return func(*args, **kwargs)
            
            # For sync functions, we don't implement caching
            # as it would require async operations
            logger.warning(
                "Sync function caching not implemented",
                function=func.__name__
            )
            return func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def invalidate_cache(*cache_keys: str, pattern: Optional[str] = None):
    """
    Decorator for invalidating cache after function execution.
    
    Args:
        cache_keys: Specific cache keys to invalidate
        pattern: Pattern for bulk invalidation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            try:
                result = await func(*args, **kwargs)
                
                # Invalidate cache after successful execution
                cache_service = await get_cache_service()
                
                if cache_keys:
                    deleted = await cache_service.delete(*cache_keys)
                    logger.debug(
                        "Cache invalidated",
                        function=func.__name__,
                        keys=cache_keys,
                        deleted=deleted
                    )
                
                if pattern:
                    keys_to_delete = await cache_service.redis.keys(pattern)
                    if keys_to_delete:
                        deleted = await cache_service.delete(*keys_to_delete)
                        logger.debug(
                            "Cache pattern invalidated",
                            function=func.__name__,
                            pattern=pattern,
                            deleted=deleted
                        )
                
                return result
                
            except Exception as e:
                logger.error(
                    "Function execution failed, skipping cache invalidation",
                    function=func.__name__,
                    error=str(e)
                )
                raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            # For sync functions, we don't implement cache invalidation
            logger.warning(
                "Sync function cache invalidation not implemented",
                function=func.__name__
            )
            return func(*args, **kwargs)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def cache_player_data(ttl: int = 1800):
    """Decorator for caching player-related data."""
    return cached(ttl=ttl, cache_type="player", key_prefix="player_data")


def cache_business_data(ttl: int = 3600):
    """Decorator for caching business-related data."""
    return cached(ttl=ttl, cache_type="business", key_prefix="business_data")


def cache_stats_data(ttl: int = 300):
    """Decorator for caching statistics data."""
    return cached(ttl=ttl, cache_type="stats", key_prefix="stats_data")


def cache_api_response(ttl: int = 900):
    """Decorator for caching API responses."""
    return cached(ttl=ttl, cache_type="api_response", key_prefix="api_response")


def invalidate_player_cache(wallet: str):
    """Decorator for invalidating player-related cache."""
    key_builder = get_cache_key_builder()
    pattern = key_builder.player_pattern(wallet)
    return invalidate_cache(pattern=pattern)


def invalidate_business_cache(business_id: str):
    """Decorator for invalidating business-related cache."""
    key_builder = get_cache_key_builder()
    pattern = key_builder.business_pattern(business_id)
    return invalidate_cache(pattern=pattern)


def invalidate_stats_cache():
    """Decorator for invalidating statistics cache."""
    key_builder = get_cache_key_builder()
    patterns = [
        key_builder.build("stats", "*"),
        key_builder.build("leaderboard", "*"),
        key_builder.build("top_players", "*")
    ]
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            result = await func(*args, **kwargs)
            
            cache_service = await get_cache_service()
            total_deleted = 0
            
            for pattern in patterns:
                keys_to_delete = await cache_service.redis.keys(pattern)
                if keys_to_delete:
                    deleted = await cache_service.delete(*keys_to_delete)
                    total_deleted += deleted
            
            logger.debug(
                "Statistics cache invalidated",
                function=func.__name__,
                keys_deleted=total_deleted
            )
            
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return func
    
    return decorator


class CacheManager:
    """Context manager for cache operations."""
    
    def __init__(self):
        self.cache_service = None
        self.operations = []
    
    async def __aenter__(self):
        self.cache_service = await get_cache_service()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            # Execute pending operations on success
            await self._execute_operations()
        else:
            # Clear operations on error
            self.operations.clear()
    
    def invalidate(self, *keys: str):
        """Queue cache invalidation."""
        self.operations.append(("invalidate", keys))
    
    def invalidate_pattern(self, pattern: str):
        """Queue pattern-based cache invalidation."""
        self.operations.append(("invalidate_pattern", pattern))
    
    async def _execute_operations(self):
        """Execute queued cache operations."""
        for operation, args in self.operations:
            try:
                if operation == "invalidate":
                    await self.cache_service.delete(*args)
                elif operation == "invalidate_pattern":
                    keys = await self.cache_service.redis.keys(args)
                    if keys:
                        await self.cache_service.delete(*keys)
            except Exception as e:
                logger.error(
                    "Cache operation failed",
                    operation=operation,
                    args=args,
                    error=str(e)
                )
        
        self.operations.clear()


def with_cache_invalidation(*invalidation_keys: str, patterns: Optional[List[str]] = None):
    """
    Decorator that uses CacheManager for complex invalidation logic.
    
    Args:
        invalidation_keys: Keys to invalidate
        patterns: Patterns for bulk invalidation
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            async with CacheManager() as cache_manager:
                result = await func(*args, **kwargs)
                
                # Queue invalidations
                if invalidation_keys:
                    cache_manager.invalidate(*invalidation_keys)
                
                if patterns:
                    for pattern in patterns:
                        cache_manager.invalidate_pattern(pattern)
                
                return result
        
        if asyncio.iscoroutinefunction(func):
            return wrapper
        else:
            return func
    
    return decorator
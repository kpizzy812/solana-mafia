"""
Redis client configuration and connection management.
"""

import asyncio
from typing import Optional, Any, Dict, List, Union
import redis.asyncio as redis
from redis.asyncio import Redis
from contextlib import asynccontextmanager

from app.core.config import settings

import structlog

logger = structlog.get_logger(__name__)


class RedisClient:
    """Async Redis client wrapper with connection management."""
    
    def __init__(self, url: Optional[str] = None):
        self.url = url or self._build_redis_url()
        self._client: Optional[Redis] = None
        self._pool: Optional[redis.ConnectionPool] = None
        
    def _build_redis_url(self) -> str:
        """Build Redis URL from settings."""
        # First try to use redis_url from settings (for Docker environments)
        if hasattr(settings, 'redis_url') and settings.redis_url:
            return settings.redis_url
            
        # Fallback to building URL from components
        redis_host = getattr(settings, 'redis_host', 'localhost')
        redis_port = getattr(settings, 'redis_port', 6379)
        redis_db = getattr(settings, 'redis_db', 0)
        redis_password = getattr(settings, 'redis_password', None)
        
        if redis_password:
            return f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
        else:
            return f"redis://{redis_host}:{redis_port}/{redis_db}"
    
    async def connect(self) -> None:
        """Establish Redis connection."""
        try:
            if self._client is None:
                self._pool = redis.ConnectionPool.from_url(
                    self.url,
                    decode_responses=True,
                    max_connections=20,
                    retry_on_timeout=True,
                    socket_keepalive=True,
                    socket_keepalive_options={}
                )
                self._client = Redis(connection_pool=self._pool)
                
                # Test connection
                await self._client.ping()
                logger.info("Redis connection established", url=self.url)
                
        except Exception as e:
            logger.error("Failed to connect to Redis", url=self.url, error=str(e))
            raise
    
    async def disconnect(self) -> None:
        """Close Redis connection."""
        try:
            if self._client:
                await self._client.aclose()
                self._client = None
                logger.info("Redis connection closed")
        except Exception as e:
            logger.error("Error closing Redis connection", error=str(e))
    
    @property
    def client(self) -> Redis:
        """Get Redis client instance."""
        if self._client is None:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis connection health."""
        try:
            if self._client is None:
                return {"status": "disconnected", "error": "No connection"}
            
            start_time = asyncio.get_event_loop().time()
            result = await self._client.ping()
            ping_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            info = await self._client.info()
            
            return {
                "status": "healthy" if result else "unhealthy",
                "ping_ms": round(ping_time, 2),
                "connected_clients": info.get("connected_clients", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "redis_version": info.get("redis_version", "unknown"),
                "uptime_in_seconds": info.get("uptime_in_seconds", 0)
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    # Core Redis operations
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.error("Redis GET failed", key=key, error=str(e))
            return None
    
    async def set(
        self, 
        key: str, 
        value: Union[str, bytes, int, float], 
        ex: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """Set key-value with optional expiration."""
        try:
            return await self.client.set(key, value, ex=ex, nx=nx)
        except Exception as e:
            logger.error("Redis SET failed", key=key, error=str(e))
            return False
    
    async def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        try:
            return await self.client.delete(*keys)
        except Exception as e:
            logger.error("Redis DELETE failed", keys=keys, error=str(e))
            return 0
    
    async def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        try:
            return await self.client.exists(*keys)
        except Exception as e:
            logger.error("Redis EXISTS failed", keys=keys, error=str(e))
            return 0
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for key."""
        try:
            return await self.client.expire(key, seconds)
        except Exception as e:
            logger.error("Redis EXPIRE failed", key=key, error=str(e))
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for key."""
        try:
            return await self.client.ttl(key)
        except Exception as e:
            logger.error("Redis TTL failed", key=key, error=str(e))
            return -1
    
    # Hash operations
    async def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value."""
        try:
            return await self.client.hget(name, key)
        except Exception as e:
            logger.error("Redis HGET failed", name=name, key=key, error=str(e))
            return None
    
    async def hset(self, name: str, key: str, value: Union[str, bytes, int, float]) -> bool:
        """Set hash field value."""
        try:
            return await self.client.hset(name, key, value)
        except Exception as e:
            logger.error("Redis HSET failed", name=name, key=key, error=str(e))
            return False
    
    async def hgetall(self, name: str) -> Dict[str, str]:
        """Get all hash fields and values."""
        try:
            return await self.client.hgetall(name)
        except Exception as e:
            logger.error("Redis HGETALL failed", name=name, error=str(e))
            return {}
    
    async def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        try:
            return await self.client.hdel(name, *keys)
        except Exception as e:
            logger.error("Redis HDEL failed", name=name, keys=keys, error=str(e))
            return 0
    
    # Set operations
    async def sadd(self, name: str, *values: Union[str, bytes, int, float]) -> int:
        """Add values to set."""
        try:
            return await self.client.sadd(name, *values)
        except Exception as e:
            logger.error("Redis SADD failed", name=name, error=str(e))
            return 0
    
    async def srem(self, name: str, *values: Union[str, bytes, int, float]) -> int:
        """Remove values from set."""
        try:
            return await self.client.srem(name, *values)
        except Exception as e:
            logger.error("Redis SREM failed", name=name, error=str(e))
            return 0
    
    async def smembers(self, name: str) -> set:
        """Get all set members."""
        try:
            return await self.client.smembers(name)
        except Exception as e:
            logger.error("Redis SMEMBERS failed", name=name, error=str(e))
            return set()
    
    # List operations
    async def lpush(self, name: str, *values: Union[str, bytes, int, float]) -> int:
        """Push values to left of list."""
        try:
            return await self.client.lpush(name, *values)
        except Exception as e:
            logger.error("Redis LPUSH failed", name=name, error=str(e))
            return 0
    
    async def rpop(self, name: str) -> Optional[str]:
        """Pop value from right of list."""
        try:
            return await self.client.rpop(name)
        except Exception as e:
            logger.error("Redis RPOP failed", name=name, error=str(e))
            return None
    
    async def lrange(self, name: str, start: int, end: int) -> List[str]:
        """Get list range."""
        try:
            return await self.client.lrange(name, start, end)
        except Exception as e:
            logger.error("Redis LRANGE failed", name=name, error=str(e))
            return []
    
    # Pattern operations
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        try:
            return await self.client.keys(pattern)
        except Exception as e:
            logger.error("Redis KEYS failed", pattern=pattern, error=str(e))
            return []
    
    async def scan(self, cursor: int = 0, match: Optional[str] = None, count: Optional[int] = None):
        """Scan keys with cursor."""
        try:
            return await self.client.scan(cursor=cursor, match=match, count=count)
        except Exception as e:
            logger.error("Redis SCAN failed", error=str(e))
            return (0, [])
    
    # Pipeline operations
    @asynccontextmanager
    async def pipeline(self):
        """Create Redis pipeline for batch operations."""
        pipe = self.client.pipeline()
        try:
            yield pipe
            await pipe.execute()
        except Exception as e:
            logger.error("Redis pipeline failed", error=str(e))
            raise
        finally:
            await pipe.reset()


# Global Redis client instance
_redis_client: Optional[RedisClient] = None


async def get_redis_client() -> RedisClient:
    """Get global Redis client instance."""
    global _redis_client
    
    if _redis_client is None:
        _redis_client = RedisClient()
        await _redis_client.connect()
    
    return _redis_client


async def close_redis_client() -> None:
    """Close global Redis client."""
    global _redis_client
    
    if _redis_client is not None:
        await _redis_client.disconnect()
        _redis_client = None
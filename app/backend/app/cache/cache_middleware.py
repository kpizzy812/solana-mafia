"""
Cache middleware for automatic API response caching.
"""

import asyncio
import json
from typing import Any, Dict, List, Optional, Set, Callable
from datetime import datetime, timedelta

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

from .cache_service import get_cache_service
from .cache_keys import get_cache_key_builder

import structlog

logger = structlog.get_logger(__name__)


class CacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware for automatic caching of API responses.
    """
    
    def __init__(
        self,
        app,
        cache_enabled: bool = True,
        default_ttl: int = 900,  # 15 minutes
        cache_get_only: bool = True,
        skip_paths: Optional[List[str]] = None,
        skip_headers: Optional[List[str]] = None,
        cache_status_codes: Optional[Set[int]] = None
    ):
        super().__init__(app)
        self.cache_enabled = cache_enabled
        self.default_ttl = default_ttl
        self.cache_get_only = cache_get_only
        self.skip_paths = set(skip_paths or [
            "/docs", "/redoc", "/openapi.json", "/health",
            "/admin", "/metrics", "/ws"
        ])
        self.skip_headers = set(skip_headers or [
            "authorization", "x-auth-token", "cookie"
        ])
        self.cache_status_codes = cache_status_codes or {200, 201, 202}
        
    def _should_cache_request(self, request: Request) -> bool:
        """Determine if request should be cached."""
        if not self.cache_enabled:
            return False
            
        # Skip non-GET requests if configured
        if self.cache_get_only and request.method != "GET":
            return False
            
        # Skip paths in skip list
        path = str(request.url.path)
        if any(skip_path in path for skip_path in self.skip_paths):
            return False
            
        # Skip requests with sensitive headers
        headers = {k.lower(): v for k, v in request.headers.items()}
        if any(header in headers for header in self.skip_headers):
            return False
            
        # Skip if cache-control no-cache is present
        cache_control = headers.get("cache-control", "")
        if "no-cache" in cache_control.lower():
            return False
            
        return True
    
    def _should_cache_response(self, response: Response) -> bool:
        """Determine if response should be cached."""
        return response.status_code in self.cache_status_codes
    
    def _build_cache_key(self, request: Request) -> str:
        """Build cache key for request."""
        key_builder = get_cache_key_builder()
        
        # Include method, path, and query parameters
        params = dict(request.query_params)
        
        # Include relevant headers (except sensitive ones)
        relevant_headers = {}
        for key, value in request.headers.items():
            if key.lower() not in self.skip_headers:
                # Only include headers that affect response content
                if key.lower() in ["accept", "accept-language", "content-type"]:
                    relevant_headers[key.lower()] = value
        
        return key_builder.api_response_key(
            endpoint=f"{request.method}:{request.url.path}",
            params={**params, **relevant_headers}
        )
    
    def _serialize_response(self, response: Response) -> Dict[str, Any]:
        """Serialize response for caching."""
        try:
            # Get response body
            body = response.body
            if isinstance(body, bytes):
                try:
                    # Try to decode as UTF-8 text
                    body_str = body.decode('utf-8')
                    # Try to parse as JSON
                    try:
                        body_data = json.loads(body_str)
                    except json.JSONDecodeError:
                        body_data = body_str
                except UnicodeDecodeError:
                    # Binary data, encode as base64
                    import base64
                    body_data = base64.b64encode(body).decode('ascii')
                    body_str = f"__BINARY_DATA__:{body_data}"
                    body_data = body_str
            else:
                body_data = body
            
            # Serialize response
            response_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": body_data,
                "media_type": getattr(response, 'media_type', 'application/json'),
                "cached_at": datetime.utcnow().isoformat()
            }
            
            return response_data
            
        except Exception as e:
            logger.error("Failed to serialize response for caching", error=str(e))
            return None
    
    def _deserialize_response(self, cached_data: Dict[str, Any]) -> Optional[Response]:
        """Deserialize cached response."""
        try:
            body = cached_data["body"]
            
            # Handle binary data
            if isinstance(body, str) and body.startswith("__BINARY_DATA__:"):
                import base64
                binary_data = base64.b64decode(body[16:])  # Remove prefix
                body = binary_data
            elif isinstance(body, (dict, list)):
                # JSON data
                body = json.dumps(body, ensure_ascii=False)
            
            # Create response
            response = StarletteResponse(
                content=body,
                status_code=cached_data["status_code"],
                headers=cached_data["headers"],
                media_type=cached_data.get("media_type", "application/json")
            )
            
            # Add cache headers
            response.headers["X-Cache"] = "HIT"
            response.headers["X-Cache-Date"] = cached_data.get("cached_at", "")
            
            return response
            
        except Exception as e:
            logger.error("Failed to deserialize cached response", error=str(e))
            return None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Main middleware logic."""
        start_time = asyncio.get_event_loop().time()
        
        # Check if we should cache this request
        should_cache = self._should_cache_request(request)
        
        if should_cache:
            try:
                cache_service = await get_cache_service()
                cache_key = self._build_cache_key(request)
                
                # Try to get from cache
                cached_data = await cache_service.get(cache_key)
                if cached_data:
                    response = self._deserialize_response(cached_data)
                    if response:
                        process_time = (asyncio.get_event_loop().time() - start_time) * 1000
                        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
                        
                        logger.debug(
                            "Cache hit",
                            method=request.method,
                            path=str(request.url.path),
                            key=cache_key,
                            process_time_ms=f"{process_time:.2f}"
                        )
                        
                        return response
                
            except Exception as e:
                logger.error("Cache retrieval failed", error=str(e))
                # Continue with normal processing
        
        # Execute the request
        response = await call_next(request)
        
        # Cache the response if appropriate
        if should_cache and self._should_cache_response(response):
            try:
                cache_service = await get_cache_service()
                cache_key = self._build_cache_key(request)
                
                # Serialize and cache response
                response_data = self._serialize_response(response)
                if response_data:
                    # Determine TTL based on endpoint
                    ttl = self._get_ttl_for_endpoint(request)
                    await cache_service.set(cache_key, response_data, ttl=ttl, cache_type="api_response")
                    
                    # Add cache headers
                    response.headers["X-Cache"] = "MISS"
                    
                    logger.debug(
                        "Response cached",
                        method=request.method,
                        path=str(request.url.path),
                        key=cache_key,
                        ttl=ttl
                    )
                
            except Exception as e:
                logger.error("Cache storage failed", error=str(e))
        
        # Add process time header
        process_time = (asyncio.get_event_loop().time() - start_time) * 1000
        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
        
        return response
    
    def _get_ttl_for_endpoint(self, request: Request) -> int:
        """Get TTL based on endpoint type."""
        path = str(request.url.path)
        
        # Different TTLs for different endpoint types
        if "/api/v1/stats" in path or "/api/v1/leaderboard" in path:
            return 300  # 5 minutes for stats
        elif "/api/v1/player" in path:
            return 600  # 10 minutes for player data
        elif "/api/v1/business" in path:
            return 1800  # 30 minutes for business data
        elif "/api/v1/events" in path:
            return 180  # 3 minutes for events
        else:
            return self.default_ttl


class CacheControlMiddleware(BaseHTTPMiddleware):
    """
    Middleware for setting cache control headers on responses.
    """
    
    def __init__(
        self,
        app,
        default_max_age: int = 300,
        static_max_age: int = 3600,
        dynamic_max_age: int = 60
    ):
        super().__init__(app)
        self.default_max_age = default_max_age
        self.static_max_age = static_max_age
        self.dynamic_max_age = dynamic_max_age
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add cache control headers to responses."""
        response = await call_next(request)
        
        # Skip if cache control already set
        if "cache-control" in response.headers:
            return response
        
        path = str(request.url.path)
        
        # Set cache control based on endpoint type
        if any(static_path in path for static_path in ["/static", "/assets", "/images"]):
            # Static files - long cache
            response.headers["Cache-Control"] = f"public, max-age={self.static_max_age}"
        elif any(api_path in path for api_path in ["/api/v1/stats", "/api/v1/leaderboard"]):
            # Statistics - short cache
            response.headers["Cache-Control"] = f"public, max-age={self.dynamic_max_age}"
        elif "/api/v1" in path:
            # API endpoints - moderate cache
            response.headers["Cache-Control"] = f"public, max-age={self.default_max_age}"
        else:
            # Default - no cache for dynamic content
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        
        return response


class ConditionalCacheMiddleware(BaseHTTPMiddleware):
    """
    Middleware for conditional caching using ETags and Last-Modified headers.
    """
    
    def __init__(self, app):
        super().__init__(app)
    
    def _generate_etag(self, content: bytes) -> str:
        """Generate ETag for content."""
        import hashlib
        return f'"{hashlib.md5(content).hexdigest()}"'
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle conditional caching."""
        response = await call_next(request)
        
        # Only handle GET requests
        if request.method != "GET":
            return response
        
        # Generate ETag for response
        if hasattr(response, 'body') and response.body:
            etag = self._generate_etag(response.body)
            response.headers["ETag"] = etag
            
            # Check if client has matching ETag
            if_none_match = request.headers.get("if-none-match")
            if if_none_match and etag in if_none_match:
                # Return 304 Not Modified
                return StarletteResponse(status_code=304, headers={"ETag": etag})
        
        # Add Last-Modified header
        response.headers["Last-Modified"] = datetime.utcnow().strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
        
        return response


async def cache_warming_task():
    """Background task for cache warming."""
    try:
        cache_service = await get_cache_service()
        logger.info("Starting cache warming task")
        
        # Define warming tasks
        warming_tasks = [
            lambda: cache_service.cache_global_stats({"total_players": 0, "total_businesses": 0}),
            lambda: cache_service.cache_leaderboard("net_worth", 10, []),
            lambda: cache_service.cache_recent_events(50, None, []),
        ]
        
        await cache_service.warm_cache(warming_tasks)
        
    except Exception as e:
        logger.error("Cache warming task failed", error=str(e))


def setup_cache_middleware(app, cache_config: Optional[Dict[str, Any]] = None):
    """Setup cache middleware with configuration."""
    config = cache_config or {}
    
    # Add conditional cache middleware (ETags)
    if config.get("etag_enabled", True):
        app.add_middleware(ConditionalCacheMiddleware)
    
    # Add cache control middleware
    if config.get("cache_control_enabled", True):
        app.add_middleware(
            CacheControlMiddleware,
            default_max_age=config.get("default_max_age", 300),
            static_max_age=config.get("static_max_age", 3600),
            dynamic_max_age=config.get("dynamic_max_age", 60)
        )
    
    # Add main cache middleware
    if config.get("response_caching_enabled", True):
        app.add_middleware(
            CacheMiddleware,
            cache_enabled=config.get("cache_enabled", True),
            default_ttl=config.get("default_ttl", 900),
            cache_get_only=config.get("cache_get_only", True),
            skip_paths=config.get("skip_paths"),
            skip_headers=config.get("skip_headers"),
            cache_status_codes=config.get("cache_status_codes")
        )
    
    logger.info("Cache middleware configured", config=config)
"""
Custom middleware for the FastAPI application.
Provides authentication, rate limiting, logging, and security features.
"""

import time
import json
from typing import Callable, Dict, Any, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.responses import JSONResponse

import structlog

from app.core.config import settings
from app.core.exceptions import RateLimitError
from app.utils.validation import validate_wallet_address
from app.auth.tma_auth import parse_auth_header, AuthType, TelegramMiniAppAuth
from app.auth.wallet_auth import WalletAuth


logger = structlog.get_logger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for request/response logging."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        start_time = time.perf_counter()
        
        # Log request
        logger.info(
            "Request started",
            method=request.method,
            url=str(request.url),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.perf_counter() - start_time
            
            # Add process time header
            response.headers["X-Process-Time"] = str(process_time)
            
            # Log response
            logger.info(
                "Request completed",
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                process_time=process_time,
            )
            
            return response
            
        except Exception as e:
            process_time = time.perf_counter() - start_time
            
            logger.error(
                "Request failed",
                method=request.method,
                url=str(request.url),
                error=str(e),
                process_time=process_time,
            )
            
            # Return error response
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )


class RateLimitingMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware using in-memory storage."""
    
    def __init__(self, app: FastAPI, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, list] = {}
        
    def _get_client_key(self, request: Request) -> str:
        """Get client identifier for rate limiting."""
        # Try to get wallet from Authorization header
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]
            if validate_wallet_address(token):
                return f"wallet:{token}"
        
        # Fallback to IP address
        client_ip = request.client.host if request.client else "unknown"
        return f"ip:{client_ip}"
    
    def _is_rate_limited(self, client_key: str) -> bool:
        """Check if client is rate limited."""
        now = time.time()
        window_start = now - self.window_seconds
        
        # Clean old requests
        if client_key in self.requests:
            self.requests[client_key] = [
                req_time for req_time in self.requests[client_key]
                if req_time > window_start
            ]
        else:
            self.requests[client_key] = []
        
        # Check rate limit
        return len(self.requests[client_key]) >= self.max_requests
    
    def _add_request(self, client_key: str):
        """Add request to tracking."""
        now = time.time()
        if client_key not in self.requests:
            self.requests[client_key] = []
        self.requests[client_key].append(now)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting."""
        if not settings.rate_limit_enabled:
            return await call_next(request)
        
        client_key = self._get_client_key(request)
        
        if self._is_rate_limited(client_key):
            logger.warning(
                "Rate limit exceeded",
                client_key=client_key,
                url=str(request.url),
                method=request.method
            )
            
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": f"Rate limit exceeded. Max {self.max_requests} requests per {self.window_seconds} seconds",
                    "timestamp": datetime.utcnow().isoformat()
                },
                headers={
                    "X-RateLimit-Limit": str(self.max_requests),
                    "X-RateLimit-Window": str(self.window_seconds),
                    "Retry-After": str(self.window_seconds)
                }
            )
        
        self._add_request(client_key)
        response = await call_next(request)
        
        # Add rate limit headers
        remaining = self.max_requests - len(self.requests.get(client_key, []))
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))
        response.headers["X-RateLimit-Window"] = str(self.window_seconds)
        
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Add API version header
        response.headers["X-API-Version"] = settings.app_version
        
        return response


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for Telegram Mini Apps and wallet authentication."""
    
    def __init__(self, app: FastAPI):
        super().__init__(app)
        self.public_paths = {
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
        }
        self.wallet_auth = WalletAuth()
        self.tma_auth = TelegramMiniAppAuth(
            bot_token=settings.telegram_bot_token,
            max_age_hours=settings.telegram_auth_max_age_hours
        ) if settings.telegram_bot_token else None
    
    def _is_public_path(self, path: str) -> bool:
        """Check if path is public."""
        return (
            path in self.public_paths or
            path.startswith("/docs") or
            path.startswith("/redoc") or
            path.startswith("/openapi") or
            path.startswith("/static")
        )
    
    def _extract_auth_data(self, request: Request) -> tuple[Optional[str], Optional[dict]]:
        """
        Extract authentication data from request.
        
        Returns:
            tuple: (wallet_address, tma_data)
        """
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return None, None
        
        try:
            auth_type, auth_data = parse_auth_header(auth_header)
            
            if auth_type == AuthType.WALLET:
                # Handle Bearer token (wallet address)
                wallet = self.wallet_auth.extract_wallet_from_bearer_token(auth_data)
                return wallet, None
                
            elif auth_type == AuthType.TMA:
                # Handle TMA init data
                if not self.tma_auth:
                    logger.warning("TMA authentication attempted but bot token not configured")
                    return None, None
                
                try:
                    tma_data = self.tma_auth.validate_init_data(auth_data)
                    return None, {
                        'init_data': tma_data,
                        'telegram_user_id': tma_data.telegram_user_id,
                        'username': tma_data.user.username if tma_data.user else None,
                        'first_name': tma_data.user.first_name if tma_data.user else None,
                        'last_name': tma_data.user.last_name if tma_data.user else None,
                        'is_premium': tma_data.user.is_premium if tma_data.user else None,
                        'start_param': tma_data.start_param  # For referral tracking
                    }
                except Exception as e:
                    logger.warning("TMA authentication failed", error=str(e))
                    return None, None
            
        except Exception as e:
            logger.warning("Auth header parsing failed", error=str(e))
            return None, None
        
        return None, None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with authentication."""
        path = request.url.path
        
        # Skip authentication for public paths
        if self._is_public_path(path):
            return await call_next(request)
        
        # Extract authentication data
        wallet, tma_data = self._extract_auth_data(request)
        
        # Add auth data to request state for use in endpoints
        request.state.wallet = wallet
        request.state.tma_data = tma_data
        request.state.auth_type = AuthType.WALLET if wallet else (AuthType.TMA if tma_data else None)
        
        # For protected endpoints that require authentication,
        # the dependency injection will handle the validation
        
        return await call_next(request)


def add_middleware(app: FastAPI) -> None:
    """Add all middleware to the FastAPI app."""
    
    # CORS middleware (first to handle preflight requests)
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Trusted host middleware
    if not settings.is_development:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[settings.site_domain, "localhost", "127.0.0.1"]
        )
    
    # GZip compression
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Custom middleware (order matters - last added is executed first)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Rate limiting
    if settings.rate_limit_enabled:
        app.add_middleware(
            RateLimitingMiddleware,
            max_requests=settings.rate_limit_requests,
            window_seconds=settings.rate_limit_window
        )
    
    # Authentication (TMA + Wallet)
    app.add_middleware(AuthMiddleware)
    
    # Logging (should be last to capture all processing)
    app.add_middleware(LoggingMiddleware)
    
    logger.info("Middleware configured successfully")


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Middleware for centralized error handling."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Handle errors and return consistent error responses."""
        try:
            return await call_next(request)
            
        except HTTPException as e:
            # FastAPI HTTPExceptions are already handled properly
            raise
            
        except RateLimitError as e:
            logger.warning("Rate limit error", error=str(e))
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "success": False,
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            
        except Exception as e:
            logger.error("Unhandled error", error=str(e), exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "error": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
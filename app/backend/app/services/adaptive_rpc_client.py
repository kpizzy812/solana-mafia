"""
Adaptive RPC Client with fault tolerance and intelligent load balancing.

This service provides:
- Multi-endpoint load balancing across RPC providers
- Adaptive rate limiting based on real-time feedback 
- Automatic fallback to backup endpoints
- Plan detection and optimization (free/paid/enterprise)
- Comprehensive error handling and recovery
"""

import os
import time
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import json
import hashlib
import structlog
from datetime import datetime, timedelta

from solana.rpc.async_api import AsyncClient
from solana.rpc.core import RPCException
from solders.pubkey import Pubkey
from typing import Any


logger = structlog.get_logger(__name__)


class RpcPlanType(Enum):
    FREE = "free"
    PAID = "paid"
    ENTERPRISE = "enterprise"


@dataclass
class RpcEndpoint:
    """Configuration for a single RPC endpoint."""
    url: str
    rate_limit: int  # requests per second
    priority: int    # lower = higher priority
    is_backup: bool = False
    error_count: int = 0
    last_error_time: Optional[datetime] = None
    success_count: int = 0
    current_rate: int = 0  # adaptive rate limit


@dataclass
class RpcStats:
    """Statistics for RPC performance tracking."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    errors_by_type: Dict[str, int] = None
    
    def __post_init__(self):
        if self.errors_by_type is None:
            self.errors_by_type = {}
    
    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def average_response_time(self) -> float:
        if self.successful_requests == 0:
            return 0.0
        return self.total_response_time / self.successful_requests


class RateLimitError(Exception):
    """Raised when RPC rate limit is exceeded."""
    pass


class AdaptiveRpcClient:
    """
    Intelligent RPC client with automatic failover and load balancing.
    
    Features:
    - Automatic endpoint selection based on performance
    - Adaptive rate limiting with real-time adjustment
    - Exponential backoff for failed requests
    - Plan type detection and optimization
    - Comprehensive monitoring and statistics
    """
    
    def __init__(self):
        self.logger = logger.bind(service="adaptive_rpc_client")
        
        # Load configuration
        self._load_config()
        
        # Initialize endpoints
        self._setup_endpoints()
        
        # Initialize clients
        self._clients: Dict[str, AsyncClient] = {}
        self._setup_clients()
        
        # State management
        self._current_endpoint_index = 0
        self._request_times: List[float] = []  # Sliding window for rate limiting
        self._last_cleanup = time.time()
        
        # Statistics
        self.stats_by_endpoint: Dict[str, RpcStats] = {
            endpoint.url: RpcStats() for endpoint in self.endpoints
        }
        self.global_stats = RpcStats()
        
    def _load_config(self):
        """Load configuration from environment variables."""
        self.plan_type = RpcPlanType(os.getenv('RPC_PLAN_TYPE', 'free'))
        self.primary_rpc_url = os.getenv('SOLANA_RPC_URL', 'https://api.devnet.solana.com')
        self.rate_limit = int(os.getenv('RPC_RATE_LIMIT', '10'))
        self.burst_limit = int(os.getenv('RPC_BURST_LIMIT', '20'))
        self.timeout = int(os.getenv('RPC_TIMEOUT', '30'))
        self.max_retries = int(os.getenv('RPC_MAX_RETRIES', '3'))
        self.enable_multiple_endpoints = os.getenv('ENABLE_MULTIPLE_ENDPOINTS', 'false').lower() == 'true'
        self.enable_adaptive_rate_limit = os.getenv('ENABLE_ADAPTIVE_RATE_LIMIT', 'true').lower() == 'true'
        
        # Parse backup endpoints
        backup_urls = os.getenv('BACKUP_RPC_URLS', '').strip()
        self.backup_rpc_urls = [url.strip() for url in backup_urls.split(',') if url.strip()] if backup_urls else []
        
        backup_limits = os.getenv('BACKUP_RPC_RATE_LIMITS', '').strip()
        self.backup_rate_limits = [int(x.strip()) for x in backup_limits.split(',') if x.strip()] if backup_limits else []
        
        # Ensure backup rate limits match backup URLs count
        while len(self.backup_rate_limits) < len(self.backup_rpc_urls):
            self.backup_rate_limits.append(5)  # Default rate limit
            
        self.logger.info(
            "RPC Configuration loaded",
            plan_type=self.plan_type.value,
            primary_url=self.primary_rpc_url,
            rate_limit=self.rate_limit,
            backup_count=len(self.backup_rpc_urls),
            adaptive_enabled=self.enable_adaptive_rate_limit
        )
    
    def _setup_endpoints(self):
        """Setup RPC endpoints with priorities."""
        self.endpoints: List[RpcEndpoint] = []
        
        # Primary endpoint
        self.endpoints.append(RpcEndpoint(
            url=self.primary_rpc_url,
            rate_limit=self.rate_limit,
            priority=1,
            is_backup=False,
            current_rate=self.rate_limit
        ))
        
        # Backup endpoints (if enabled)
        if self.enable_multiple_endpoints and self.backup_rpc_urls:
            for i, backup_url in enumerate(self.backup_rpc_urls):
                backup_rate = self.backup_rate_limits[i] if i < len(self.backup_rate_limits) else 5
                self.endpoints.append(RpcEndpoint(
                    url=backup_url,
                    rate_limit=backup_rate,
                    priority=10 + i,  # Lower priority than primary
                    is_backup=True,
                    current_rate=backup_rate
                ))
        
        # Sort by priority
        self.endpoints.sort(key=lambda x: x.priority)
        
        self.logger.info(
            "RPC Endpoints configured",
            total_endpoints=len(self.endpoints),
            primary_url=self.endpoints[0].url,
            backup_count=len([ep for ep in self.endpoints if ep.is_backup])
        )
    
    def _setup_clients(self):
        """Initialize AsyncClient instances for each endpoint."""
        for endpoint in self.endpoints:
            try:
                self._clients[endpoint.url] = AsyncClient(
                    endpoint.url,
                    timeout=self.timeout
                )
            except Exception as e:
                self.logger.error(
                    "Failed to setup client",
                    endpoint=endpoint.url,
                    error=str(e)
                )
    
    async def close(self):
        """Clean up all client connections."""
        for client in self._clients.values():
            try:
                await client.close()
            except Exception as e:
                self.logger.warning("Error closing RPC client", error=str(e))
        
        self.logger.info("All RPC clients closed")
    
    def _cleanup_request_times(self):
        """Remove old request times from sliding window."""
        current_time = time.time()
        if current_time - self._last_cleanup > 1.0:  # Cleanup every second
            cutoff_time = current_time - 1.0
            self._request_times = [t for t in self._request_times if t > cutoff_time]
            self._last_cleanup = current_time
    
    def _can_make_request(self, endpoint: RpcEndpoint) -> bool:
        """Check if we can make a request without hitting rate limits."""
        self._cleanup_request_times()
        
        # Use adaptive rate limit if enabled
        current_rate = endpoint.current_rate if self.enable_adaptive_rate_limit else endpoint.rate_limit
        
        # Check if we're within rate limit
        recent_requests = len(self._request_times)
        return recent_requests < current_rate
    
    async def _wait_for_rate_limit(self, endpoint: RpcEndpoint):
        """Wait until we can make a request within rate limits."""
        while not self._can_make_request(endpoint):
            await asyncio.sleep(0.1)
    
    def _record_request(self):
        """Record a request in the sliding window."""
        self._request_times.append(time.time())
    
    def _select_best_endpoint(self) -> RpcEndpoint:
        """Select the best available endpoint based on performance."""
        # Filter out endpoints with recent errors
        current_time = datetime.utcnow()
        available_endpoints = []
        
        for endpoint in self.endpoints:
            # Skip endpoints with recent errors (exponential backoff)
            if endpoint.last_error_time:
                backoff_duration = timedelta(seconds=2 ** min(endpoint.error_count, 6))
                if current_time - endpoint.last_error_time < backoff_duration:
                    continue
            
            available_endpoints.append(endpoint)
        
        if not available_endpoints:
            # All endpoints have errors, use primary anyway
            return self.endpoints[0]
        
        # Sort by success rate and priority
        available_endpoints.sort(key=lambda ep: (
            -self.stats_by_endpoint[ep.url].success_rate,  # Higher success rate first
            ep.priority,  # Lower priority number first
            ep.error_count  # Fewer errors first
        ))
        
        return available_endpoints[0]
    
    def _update_endpoint_stats(self, endpoint: RpcEndpoint, success: bool, response_time: float, error_type: str = None):
        """Update statistics for an endpoint."""
        stats = self.stats_by_endpoint[endpoint.url]
        
        stats.total_requests += 1
        stats.last_request_time = datetime.utcnow()
        
        if success:
            stats.successful_requests += 1
            stats.total_response_time += response_time
            endpoint.success_count += 1
            
            # Reduce error count on success (recovery)
            if endpoint.error_count > 0:
                endpoint.error_count = max(0, endpoint.error_count - 1)
            
            # Increase rate limit if adaptive mode enabled
            if self.enable_adaptive_rate_limit and endpoint.current_rate < endpoint.rate_limit:
                endpoint.current_rate = min(endpoint.rate_limit, endpoint.current_rate + 1)
                
        else:
            stats.failed_requests += 1
            endpoint.error_count += 1
            endpoint.last_error_time = datetime.utcnow()
            
            if error_type:
                stats.errors_by_type[error_type] = stats.errors_by_type.get(error_type, 0) + 1
            
            # Decrease rate limit if adaptive mode enabled
            if self.enable_adaptive_rate_limit:
                endpoint.current_rate = max(1, endpoint.current_rate - 2)
        
        # Update global stats
        self.global_stats.total_requests += 1
        if success:
            self.global_stats.successful_requests += 1
            self.global_stats.total_response_time += response_time
        else:
            self.global_stats.failed_requests += 1
    
    async def _make_request_to_endpoint(self, endpoint: RpcEndpoint, method: str, params: List[Any] = None) -> Any:
        """Make a request to a specific endpoint."""
        if endpoint.url not in self._clients:
            raise Exception(f"No client configured for endpoint: {endpoint.url}")
        
        client = self._clients[endpoint.url]
        
        # Wait for rate limit
        await self._wait_for_rate_limit(endpoint)
        
        # Record request
        self._record_request()
        
        start_time = time.time()
        try:
            # Make the actual RPC request
            if method == "get_multiple_accounts":
                result = await client.get_multiple_accounts(params[0], commitment=params[1] if len(params) > 1 else "confirmed")
            elif method == "get_account":
                result = await client.get_account(params[0], commitment=params[1] if len(params) > 1 else "confirmed")
            elif method == "get_slot":
                result = await client.get_slot()
            elif method == "send_transaction":
                result = await client.send_transaction(params[0])
            else:
                # Generic request
                result = await client._make_request(method, params or [])
            
            response_time = time.time() - start_time
            self._update_endpoint_stats(endpoint, True, response_time)
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            error_type = type(e).__name__
            
            self._update_endpoint_stats(endpoint, False, response_time, error_type)
            
            # Check if it's a rate limit error
            if "rate limit" in str(e).lower() or "too many requests" in str(e).lower():
                raise RateLimitError(f"Rate limit exceeded on {endpoint.url}: {e}")
            
            raise e
    
    async def make_request(self, method: str, params: List[Any] = None, max_retries: int = None) -> Any:
        """
        Make a resilient RPC request with automatic failover.
        
        Args:
            method: RPC method name
            params: Request parameters
            max_retries: Max retry attempts (uses config default if None)
        
        Returns:
            RPC response
            
        Raises:
            Exception: If all endpoints fail after retries
        """
        max_retries = max_retries or self.max_retries
        last_exception = None
        
        for attempt in range(max_retries):
            # Select best endpoint for this attempt
            endpoint = self._select_best_endpoint()
            
            try:
                result = await self._make_request_to_endpoint(endpoint, method, params)
                
                if attempt > 0:
                    self.logger.info(
                        "Request succeeded after retries",
                        method=method,
                        endpoint=endpoint.url,
                        attempt=attempt + 1
                    )
                
                return result
                
            except RateLimitError as e:
                self.logger.warning(
                    "Rate limit hit",
                    method=method,
                    endpoint=endpoint.url,
                    attempt=attempt + 1,
                    error=str(e)
                )
                last_exception = e
                
                # Wait longer for rate limit errors
                await asyncio.sleep(2 ** attempt)
                
            except Exception as e:
                self.logger.error(
                    "Request failed",
                    method=method,
                    endpoint=endpoint.url,
                    attempt=attempt + 1,
                    error=str(e)
                )
                last_exception = e
                
                # Shorter wait for other errors
                if attempt < max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
        
        # All attempts failed
        self.logger.error(
            "All RPC requests failed",
            method=method,
            max_retries=max_retries,
            last_error=str(last_exception)
        )
        
        raise last_exception or Exception("All RPC endpoints failed")
    
    # Convenience methods for common operations
    async def get_multiple_accounts(self, pubkeys: List[Pubkey], commitment: str = "confirmed") -> Any:
        """Get multiple account data with resilient retry."""
        return await self.make_request("get_multiple_accounts", [pubkeys, commitment])
    
    async def get_account(self, pubkey: Pubkey, commitment: str = "confirmed") -> Any:
        """Get single account data with resilient retry."""
        return await self.make_request("get_account", [pubkey, commitment])
    
    async def get_slot(self) -> Any:
        """Get current slot with resilient retry."""
        return await self.make_request("get_slot")
    
    async def send_transaction(self, transaction) -> Any:
        """Send transaction with resilient retry."""
        return await self.make_request("send_transaction", [transaction])
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics for all endpoints."""
        return {
            "global": asdict(self.global_stats),
            "endpoints": {
                endpoint.url: {
                    "stats": asdict(self.stats_by_endpoint[endpoint.url]),
                    "config": {
                        "rate_limit": endpoint.rate_limit,
                        "current_rate": endpoint.current_rate,
                        "priority": endpoint.priority,
                        "is_backup": endpoint.is_backup,
                        "error_count": endpoint.error_count,
                        "last_error": endpoint.last_error_time.isoformat() if endpoint.last_error_time else None
                    }
                }
                for endpoint in self.endpoints
            },
            "plan_type": self.plan_type.value,
            "adaptive_enabled": self.enable_adaptive_rate_limit
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on all endpoints."""
        health_results = {}
        
        for endpoint in self.endpoints:
            try:
                start_time = time.time()
                await self._make_request_to_endpoint(endpoint, "get_slot")
                response_time = time.time() - start_time
                
                health_results[endpoint.url] = {
                    "healthy": True,
                    "response_time": response_time,
                    "error": None
                }
                
            except Exception as e:
                health_results[endpoint.url] = {
                    "healthy": False,
                    "response_time": None,
                    "error": str(e)
                }
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "endpoints": health_results,
            "stats": self.get_stats()
        }


# Global instance
_adaptive_rpc_client: Optional[AdaptiveRpcClient] = None


async def get_adaptive_rpc_client() -> AdaptiveRpcClient:
    """Get or create global AdaptiveRpcClient instance."""
    global _adaptive_rpc_client
    if _adaptive_rpc_client is None:
        _adaptive_rpc_client = AdaptiveRpcClient()
    return _adaptive_rpc_client


async def close_adaptive_rpc_client():
    """Close the global AdaptiveRpcClient instance."""
    global _adaptive_rpc_client
    if _adaptive_rpc_client:
        await _adaptive_rpc_client.close()
        _adaptive_rpc_client = None
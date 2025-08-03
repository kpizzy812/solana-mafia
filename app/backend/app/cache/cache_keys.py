"""
Cache key building and management utilities.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
import hashlib
import json

from app.core.config import settings

import structlog

logger = structlog.get_logger(__name__)


class CacheKeyBuilder:
    """Utility for building consistent cache keys."""
    
    def __init__(self, prefix: str = "solana_mafia"):
        self.prefix = prefix
        self.separator = ":"
        
    def _normalize_value(self, value: Any) -> str:
        """Normalize value for use in cache key."""
        if isinstance(value, (dict, list)):
            # Sort dict keys for consistent hashing
            if isinstance(value, dict):
                value = {k: v for k, v in sorted(value.items())}
            return hashlib.md5(json.dumps(value, sort_keys=True).encode()).hexdigest()[:8]
        elif isinstance(value, (datetime, date)):
            return value.isoformat()
        elif value is None:
            return "null"
        else:
            return str(value)
    
    def build(self, *parts: Any) -> str:
        """Build cache key from parts."""
        normalized_parts = []
        
        # Add prefix
        if self.prefix:
            normalized_parts.append(self.prefix)
        
        # Add environment if not production
        if settings.environment != "production":
            normalized_parts.append(settings.environment)
        
        # Normalize and add parts
        for part in parts:
            if part is not None:
                normalized_parts.append(self._normalize_value(part))
        
        return self.separator.join(normalized_parts)
    
    # Player-related keys
    def player_key(self, wallet: str) -> str:
        """Build player cache key."""
        return self.build("player", wallet)
    
    def player_stats_key(self, wallet: str) -> str:
        """Build player statistics cache key."""
        return self.build("player_stats", wallet)
    
    def player_businesses_key(self, wallet: str) -> str:
        """Build player businesses cache key."""
        return self.build("player_businesses", wallet)
    
    def player_earnings_key(self, wallet: str) -> str:
        """Build player earnings cache key."""
        return self.build("player_earnings", wallet)
    
    def player_activity_key(self, wallet: str, limit: int = 50) -> str:
        """Build player activity cache key."""
        return self.build("player_activity", wallet, limit)
    
    # Business-related keys
    def business_key(self, business_id: str) -> str:
        """Build business cache key."""
        return self.build("business", business_id)
    
    def businesses_list_key(self, filters: Optional[Dict[str, Any]] = None) -> str:
        """Build businesses list cache key."""
        return self.build("businesses_list", filters or {})
    
    def business_nft_key(self, nft_id: str) -> str:
        """Build business NFT cache key."""
        return self.build("business_nft", nft_id)
    
    # Statistics keys
    def global_stats_key(self) -> str:
        """Build global statistics cache key."""
        return self.build("global_stats")
    
    def leaderboard_key(self, metric: str, limit: int = 10) -> str:
        """Build leaderboard cache key."""
        return self.build("leaderboard", metric, limit)
    
    def top_players_key(self, metric: str, limit: int = 10) -> str:
        """Build top players cache key."""
        return self.build("top_players", metric, limit)
    
    # Event-related keys
    def recent_events_key(self, limit: int = 50, event_type: Optional[str] = None) -> str:
        """Build recent events cache key."""
        return self.build("recent_events", limit, event_type)
    
    def events_by_type_key(self, hours: int = 24) -> str:
        """Build events by type cache key."""
        return self.build("events_by_type", hours)
    
    # API response keys
    def api_response_key(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Build API response cache key."""
        return self.build("api_response", endpoint, params or {})
    
    def paginated_response_key(
        self, 
        endpoint: str, 
        page: int = 1, 
        limit: int = 20, 
        filters: Optional[Dict[str, Any]] = None
    ) -> str:
        """Build paginated API response cache key."""
        return self.build("paginated", endpoint, page, limit, filters or {})
    
    # System metrics keys
    def system_metrics_key(self) -> str:
        """Build system metrics cache key."""
        return self.build("system_metrics")
    
    def database_metrics_key(self) -> str:
        """Build database metrics cache key."""
        return self.build("database_metrics")
    
    def application_metrics_key(self) -> str:
        """Build application metrics cache key."""
        return self.build("application_metrics")
    
    def websocket_stats_key(self) -> str:
        """Build WebSocket statistics cache key."""
        return self.build("websocket_stats")
    
    def indexer_stats_key(self) -> str:
        """Build indexer statistics cache key."""
        return self.build("indexer_stats")
    
    def scheduler_stats_key(self) -> str:
        """Build scheduler statistics cache key."""
        return self.build("scheduler_stats")
    
    # Session and authentication keys
    def session_key(self, session_id: str) -> str:
        """Build session cache key."""
        return self.build("session", session_id)
    
    def auth_token_key(self, token_hash: str) -> str:
        """Build authentication token cache key."""
        return self.build("auth_token", token_hash)
    
    def rate_limit_key(self, identifier: str, window: str) -> str:
        """Build rate limiting cache key."""
        return self.build("rate_limit", identifier, window)
    
    # Search and filter keys
    def search_results_key(self, query: str, filters: Optional[Dict[str, Any]] = None) -> str:
        """Build search results cache key."""
        return self.build("search", query, filters or {})
    
    def filter_results_key(self, model: str, filters: Dict[str, Any]) -> str:
        """Build filter results cache key."""
        return self.build("filter", model, filters)
    
    # Pattern keys for bulk operations
    def player_pattern(self, wallet_pattern: str = "*") -> str:
        """Build player pattern for bulk operations."""
        return self.build("player", wallet_pattern)
    
    def business_pattern(self, business_pattern: str = "*") -> str:
        """Build business pattern for bulk operations."""
        return self.build("business", business_pattern)
    
    def api_response_pattern(self, endpoint_pattern: str = "*") -> str:
        """Build API response pattern for bulk operations."""
        return self.build("api_response", endpoint_pattern)
    
    # Temporary keys
    def temp_key(self, identifier: str, purpose: str) -> str:
        """Build temporary cache key."""
        return self.build("temp", purpose, identifier)
    
    def lock_key(self, resource: str) -> str:
        """Build lock cache key."""
        return self.build("lock", resource)
    
    def processing_key(self, task_id: str) -> str:
        """Build processing task cache key."""
        return self.build("processing", task_id)


# Global cache key builder instance
cache_keys = CacheKeyBuilder()


def get_cache_key_builder() -> CacheKeyBuilder:
    """Get global cache key builder instance."""
    return cache_keys
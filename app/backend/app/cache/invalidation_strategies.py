"""
Cache invalidation strategies for real-time updates.
Provides smart invalidation patterns based on game events and data changes.
"""

import asyncio
from typing import Dict, Any, List, Optional, Set, Callable
from datetime import datetime, timedelta
from enum import Enum

from .cache_service import get_cache_service
from .cache_keys import get_cache_key_builder
from .business_cache import get_business_cache_manager

import structlog

logger = structlog.get_logger(__name__)


class InvalidationTrigger(str, Enum):
    """Types of events that trigger cache invalidation."""
    BUSINESS_CREATED = "business_created"
    BUSINESS_UPGRADED = "business_upgraded"
    BUSINESS_SOLD = "business_sold"
    BUSINESS_TRANSFERRED = "business_transferred"
    EARNINGS_UPDATED = "earnings_updated"
    EARNINGS_CLAIMED = "earnings_claimed"
    PLAYER_CREATED = "player_created"
    NFT_MINTED = "nft_minted"
    NFT_BURNED = "nft_burned"
    NFT_TRANSFERRED = "nft_transferred"
    GLOBAL_STATS_CHANGED = "global_stats_changed"


class InvalidationScope(str, Enum):
    """Scope of cache invalidation."""
    SINGLE_ITEM = "single_item"      # Invalidate specific item only
    OWNER_RELATED = "owner_related"  # Invalidate all owner-related data
    TYPE_RELATED = "type_related"    # Invalidate type-related aggregations
    GLOBAL = "global"                # Invalidate global statistics
    CASCADE = "cascade"              # Cascade invalidation to related items


class CacheInvalidationStrategy:
    """Manages intelligent cache invalidation based on events."""
    
    def __init__(self):
        self.cache_service = None
        self.key_builder = None
        self.business_cache = None
        self.nft_cache = None
        
        # Define invalidation patterns
        self.invalidation_patterns = {
            InvalidationTrigger.BUSINESS_CREATED: self._invalidate_business_created,
            InvalidationTrigger.BUSINESS_UPGRADED: self._invalidate_business_upgraded,
            InvalidationTrigger.BUSINESS_SOLD: self._invalidate_business_sold,
            InvalidationTrigger.BUSINESS_TRANSFERRED: self._invalidate_business_transferred,
            InvalidationTrigger.EARNINGS_UPDATED: self._invalidate_earnings_updated,
            InvalidationTrigger.EARNINGS_CLAIMED: self._invalidate_earnings_claimed,
            InvalidationTrigger.PLAYER_CREATED: self._invalidate_player_created,
            InvalidationTrigger.NFT_MINTED: self._invalidate_nft_minted,
            InvalidationTrigger.NFT_BURNED: self._invalidate_nft_burned,
            InvalidationTrigger.NFT_TRANSFERRED: self._invalidate_nft_transferred,
            InvalidationTrigger.GLOBAL_STATS_CHANGED: self._invalidate_global_stats,
        }
        
        # Track invalidation metrics
        self.invalidation_metrics = {
            "total_invalidations": 0,
            "invalidations_by_trigger": {},
            "keys_invalidated": 0,
            "last_invalidation": None
        }
    
    async def initialize(self):
        """Initialize invalidation strategy."""
        self.cache_service = await get_cache_service()
        self.key_builder = get_cache_key_builder()
        self.business_cache = await get_business_cache_manager()
        # self.nft_cache = await get_nft_cache_manager()  # NFT functionality removed
        
        logger.info("Cache invalidation strategy initialized")
    
    async def invalidate(
        self, 
        trigger: InvalidationTrigger, 
        event_data: Dict[str, Any],
        scope: InvalidationScope = InvalidationScope.CASCADE
    ) -> Dict[str, Any]:
        """
        Execute cache invalidation based on trigger and data.
        
        Args:
            trigger: Type of event triggering invalidation
            event_data: Event data containing relevant identifiers
            scope: Scope of invalidation
            
        Returns:
            Dictionary with invalidation results
        """
        if not self.cache_service:
            await self.initialize()
        
        start_time = datetime.utcnow()
        
        try:
            # Get invalidation handler
            handler = self.invalidation_patterns.get(trigger)
            if not handler:
                logger.warning(f"No invalidation pattern for trigger: {trigger}")
                return {"success": False, "error": "Unknown trigger"}
            
            # Execute invalidation
            result = await handler(event_data, scope)
            
            # Update metrics
            self._update_metrics(trigger, result)
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info(
                "Cache invalidation completed",
                trigger=trigger.value,
                scope=scope.value,
                keys_invalidated=result.get("keys_invalidated", 0),
                duration=duration
            )
            
            return {
                "success": True,
                "trigger": trigger.value,
                "scope": scope.value,
                "keys_invalidated": result.get("keys_invalidated", 0),
                "duration": duration,
                "details": result
            }
            
        except Exception as e:
            logger.error(
                "Cache invalidation failed",
                trigger=trigger.value,
                error=str(e)
            )
            return {
                "success": False,
                "trigger": trigger.value,
                "error": str(e)
            }
    
    def _update_metrics(self, trigger: InvalidationTrigger, result: Dict[str, Any]):
        """Update invalidation metrics."""
        self.invalidation_metrics["total_invalidations"] += 1
        self.invalidation_metrics["last_invalidation"] = datetime.utcnow().isoformat()
        
        trigger_key = trigger.value
        if trigger_key not in self.invalidation_metrics["invalidations_by_trigger"]:
            self.invalidation_metrics["invalidations_by_trigger"][trigger_key] = 0
        self.invalidation_metrics["invalidations_by_trigger"][trigger_key] += 1
        
        self.invalidation_metrics["keys_invalidated"] += result.get("keys_invalidated", 0)
    
    # Invalidation handlers for different event types
    
    async def _invalidate_business_created(
        self, 
        event_data: Dict[str, Any], 
        scope: InvalidationScope
    ) -> Dict[str, Any]:
        """Handle business creation invalidation."""
        keys_invalidated = 0
        
        business_id = event_data.get("business_id")
        owner = event_data.get("owner")
        business_type = event_data.get("business_type")
        
        if scope in [InvalidationScope.OWNER_RELATED, InvalidationScope.CASCADE]:
            if owner:
                # Invalidate owner's business list
                owner_key = self.key_builder.build("businesses_by_owner", owner)
                await self.cache_service.delete(owner_key)
                keys_invalidated += 1
                
                # Invalidate player statistics
                player_stats_key = self.key_builder.player_stats_key(owner)
                await self.cache_service.delete(player_stats_key)
                keys_invalidated += 1
        
        if scope in [InvalidationScope.TYPE_RELATED, InvalidationScope.CASCADE]:
            if business_type is not None:
                # Invalidate business type listings
                type_pattern = self.key_builder.build("businesses_by_type", business_type, "*")
                type_keys = await self.cache_service.redis.keys(type_pattern)
                if type_keys:
                    await self.cache_service.delete(*type_keys)
                    keys_invalidated += len(type_keys)
        
        if scope in [InvalidationScope.GLOBAL, InvalidationScope.CASCADE]:
            # Invalidate global statistics
            await self._invalidate_global_statistics_cache()
            keys_invalidated += 3  # Approximate global stats keys
        
        return {"keys_invalidated": keys_invalidated, "business_id": business_id}
    
    async def _invalidate_business_upgraded(
        self, 
        event_data: Dict[str, Any], 
        scope: InvalidationScope
    ) -> Dict[str, Any]:
        """Handle business upgrade invalidation."""
        keys_invalidated = 0
        
        business_id = event_data.get("business_id")
        owner = event_data.get("owner")
        nft_mint = event_data.get("nft_mint")
        
        if business_id:
            # Always invalidate the business itself
            await self.business_cache.invalidate_business_cache(business_id, owner)
            keys_invalidated += 2  # Business + owner relation
            
            # Invalidate business projections and market value
            projection_key = self.key_builder.build("business_earnings_projection", business_id, "*")
            market_value_key = self.key_builder.build("business_market_value", business_id)
            
            projection_keys = await self.cache_service.redis.keys(projection_key)
            if projection_keys:
                await self.cache_service.delete(*projection_keys)
                keys_invalidated += len(projection_keys)
            
            await self.cache_service.delete(market_value_key)
            keys_invalidated += 1
        
        if scope in [InvalidationScope.OWNER_RELATED, InvalidationScope.CASCADE]:
            if owner:
                # Invalidate owner's earnings
                earnings_key = self.key_builder.player_earnings_key(owner)
                await self.cache_service.delete(earnings_key)
                keys_invalidated += 1
        
        if nft_mint and scope in [InvalidationScope.CASCADE]:
            # Invalidate NFT metadata - DISABLED: NFT functionality removed
            # await self.nft_cache.invalidate_nft_cache(nft_mint)
            # keys_invalidated += 2  # NFT metadata + ownership
            pass
        
        return {"keys_invalidated": keys_invalidated, "business_id": business_id}
    
    async def _invalidate_business_sold(
        self, 
        event_data: Dict[str, Any], 
        scope: InvalidationScope
    ) -> Dict[str, Any]:
        """Handle business sale invalidation."""
        keys_invalidated = 0
        
        business_id = event_data.get("business_id")
        seller = event_data.get("seller")
        buyer = event_data.get("buyer")
        nft_mint = event_data.get("nft_mint")
        
        # Invalidate business data
        if business_id:
            await self.business_cache.invalidate_business_cache(business_id, seller)
            keys_invalidated += 2
        
        if scope in [InvalidationScope.OWNER_RELATED, InvalidationScope.CASCADE]:
            # Invalidate both seller and buyer data
            for wallet in [seller, buyer]:
                if wallet:
                    # Player businesses
                    businesses_key = self.key_builder.build("businesses_by_owner", wallet)
                    await self.cache_service.delete(businesses_key)
                    keys_invalidated += 1
                    
                    # Player stats and earnings
                    player_stats_key = self.key_builder.player_stats_key(wallet)
                    earnings_key = self.key_builder.player_earnings_key(wallet)
                    await self.cache_service.delete(player_stats_key, earnings_key)
                    keys_invalidated += 2
        
        if nft_mint and scope in [InvalidationScope.CASCADE]:
            # Update NFT ownership
            if buyer:
                # await self.nft_cache.cache_nft_ownership(nft_mint, buyer, business_id)  # NFT functionality removed
            else:
                # await self.nft_cache.invalidate_nft_cache(nft_mint)  # NFT functionality removed
            keys_invalidated += 1
        
        if scope in [InvalidationScope.GLOBAL, InvalidationScope.CASCADE]:
            await self._invalidate_global_statistics_cache()
            keys_invalidated += 3
        
        return {"keys_invalidated": keys_invalidated, "business_id": business_id}
    
    async def _invalidate_business_transferred(
        self, 
        event_data: Dict[str, Any], 
        scope: InvalidationScope
    ) -> Dict[str, Any]:
        """Handle business transfer invalidation."""
        # Similar to business sold but without sale-specific data
        return await self._invalidate_business_sold(event_data, scope)
    
    async def _invalidate_earnings_updated(
        self, 
        event_data: Dict[str, Any], 
        scope: InvalidationScope
    ) -> Dict[str, Any]:
        """Handle earnings update invalidation."""
        keys_invalidated = 0
        
        wallet = event_data.get("wallet")
        
        if wallet:
            # Invalidate player earnings
            earnings_key = self.key_builder.player_earnings_key(wallet)
            await self.cache_service.delete(earnings_key)
            keys_invalidated += 1
            
            if scope in [InvalidationScope.OWNER_RELATED, InvalidationScope.CASCADE]:
                # Invalidate player stats
                player_stats_key = self.key_builder.player_stats_key(wallet)
                await self.cache_service.delete(player_stats_key)
                keys_invalidated += 1
        
        if scope in [InvalidationScope.GLOBAL, InvalidationScope.CASCADE]:
            # Only invalidate earnings-related global stats
            global_stats_key = self.key_builder.global_stats_key()
            await self.cache_service.delete(global_stats_key)
            keys_invalidated += 1
        
        return {"keys_invalidated": keys_invalidated, "wallet": wallet}
    
    async def _invalidate_earnings_claimed(
        self, 
        event_data: Dict[str, Any], 
        scope: InvalidationScope
    ) -> Dict[str, Any]:
        """Handle earnings claim invalidation."""
        # Similar to earnings updated but more comprehensive
        result = await self._invalidate_earnings_updated(event_data, scope)
        
        wallet = event_data.get("wallet")
        if wallet and scope in [InvalidationScope.CASCADE]:
            # Also invalidate recent activity
            activity_key = self.key_builder.player_activity_key(wallet)
            await self.cache_service.delete(activity_key)
            result["keys_invalidated"] += 1
        
        return result
    
    async def _invalidate_player_created(
        self, 
        event_data: Dict[str, Any], 
        scope: InvalidationScope
    ) -> Dict[str, Any]:
        """Handle player creation invalidation."""
        keys_invalidated = 0
        
        if scope in [InvalidationScope.GLOBAL, InvalidationScope.CASCADE]:
            await self._invalidate_global_statistics_cache()
            keys_invalidated += 3
            
            # Invalidate leaderboards
            leaderboard_pattern = self.key_builder.build("leaderboard", "*")
            leaderboard_keys = await self.cache_service.redis.keys(leaderboard_pattern)
            if leaderboard_keys:
                await self.cache_service.delete(*leaderboard_keys)
                keys_invalidated += len(leaderboard_keys)
        
        return {"keys_invalidated": keys_invalidated}
    
    async def _invalidate_nft_minted(
        self, 
        event_data: Dict[str, Any], 
        scope: InvalidationScope
    ) -> Dict[str, Any]:
        """Handle NFT minting invalidation."""
        keys_invalidated = 0
        
        nft_mint = event_data.get("nft_mint")
        owner = event_data.get("owner")
        business_id = event_data.get("business_id")
        
        if nft_mint and owner:
            # Cache new NFT ownership
            await self.nft_cache.cache_nft_ownership(nft_mint, owner, business_id)
            keys_invalidated += 1
        
        return {"keys_invalidated": keys_invalidated, "nft_mint": nft_mint}
    
    async def _invalidate_nft_burned(
        self, 
        event_data: Dict[str, Any], 
        scope: InvalidationScope
    ) -> Dict[str, Any]:
        """Handle NFT burning invalidation."""
        keys_invalidated = 0
        
        nft_mint = event_data.get("nft_mint")
        
        if nft_mint:
            await self.nft_cache.invalidate_nft_cache(nft_mint)
            keys_invalidated += 2  # Metadata + ownership
        
        return {"keys_invalidated": keys_invalidated, "nft_mint": nft_mint}
    
    async def _invalidate_nft_transferred(
        self, 
        event_data: Dict[str, Any], 
        scope: InvalidationScope
    ) -> Dict[str, Any]:
        """Handle NFT transfer invalidation."""
        keys_invalidated = 0
        
        nft_mint = event_data.get("nft_mint")
        new_owner = event_data.get("new_owner")
        business_id = event_data.get("business_id")
        
        if nft_mint:
            # Invalidate old ownership
            await self.nft_cache.invalidate_nft_cache(nft_mint)
            keys_invalidated += 2
            
            # Cache new ownership
            if new_owner:
                await self.nft_cache.cache_nft_ownership(nft_mint, new_owner, business_id)
                keys_invalidated += 1
        
        return {"keys_invalidated": keys_invalidated, "nft_mint": nft_mint}
    
    async def _invalidate_global_stats(
        self, 
        event_data: Dict[str, Any], 
        scope: InvalidationScope
    ) -> Dict[str, Any]:
        """Handle global statistics invalidation."""
        await self._invalidate_global_statistics_cache()
        return {"keys_invalidated": 3}
    
    async def _invalidate_global_statistics_cache(self):
        """Invalidate all global statistics cache entries."""
        patterns = [
            self.key_builder.global_stats_key(),
            self.key_builder.build("leaderboard", "*"),
            self.key_builder.build("top_players", "*"),
            self.key_builder.build("global_metrics", "*")
        ]
        
        for pattern in patterns:
            if "*" in pattern:
                keys = await self.cache_service.redis.keys(pattern)
                if keys:
                    await self.cache_service.delete(*keys)
            else:
                await self.cache_service.delete(pattern)
    
    async def get_invalidation_metrics(self) -> Dict[str, Any]:
        """Get invalidation metrics."""
        return {
            **self.invalidation_metrics,
            "cache_stats": await self.cache_service.get_cache_stats()
        }
    
    async def bulk_invalidate(
        self, 
        invalidations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute multiple invalidations efficiently."""
        results = []
        total_keys = 0
        
        start_time = datetime.utcnow()
        
        for invalidation in invalidations:
            trigger = InvalidationTrigger(invalidation["trigger"])
            event_data = invalidation["event_data"]
            scope = InvalidationScope(invalidation.get("scope", InvalidationScope.CASCADE.value))
            
            result = await self.invalidate(trigger, event_data, scope)
            results.append(result)
            total_keys += result.get("keys_invalidated", 0)
        
        duration = (datetime.utcnow() - start_time).total_seconds()
        
        return {
            "total_invalidations": len(invalidations),
            "total_keys_invalidated": total_keys,
            "duration": duration,
            "results": results
        }


# Global invalidation strategy instance
_invalidation_strategy: Optional[CacheInvalidationStrategy] = None


async def get_invalidation_strategy() -> CacheInvalidationStrategy:
    """Get global cache invalidation strategy instance."""
    global _invalidation_strategy
    
    if _invalidation_strategy is None:
        _invalidation_strategy = CacheInvalidationStrategy()
        await _invalidation_strategy.initialize()
    
    return _invalidation_strategy


# Convenience functions for common invalidation patterns
async def invalidate_business_data(business_id: str, event_type: str, **kwargs):
    """Convenience function to invalidate business-related cache data."""
    strategy = await get_invalidation_strategy()
    
    event_data = {"business_id": business_id, **kwargs}
    
    if event_type in ["created", "upgraded", "sold", "transferred"]:
        trigger = InvalidationTrigger(f"business_{event_type}")
        await strategy.invalidate(trigger, event_data)


async def invalidate_player_data(wallet: str, event_type: str, **kwargs):
    """Convenience function to invalidate player-related cache data."""
    strategy = await get_invalidation_strategy()
    
    event_data = {"wallet": wallet, **kwargs}
    
    if event_type in ["earnings_updated", "earnings_claimed"]:
        trigger = InvalidationTrigger(event_type)
        await strategy.invalidate(trigger, event_data)


async def invalidate_global_data():
    """Convenience function to invalidate global statistics."""
    strategy = await get_invalidation_strategy()
    await strategy.invalidate(InvalidationTrigger.GLOBAL_STATS_CHANGED, {})
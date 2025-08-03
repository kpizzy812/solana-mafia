"""
Business and NFT data caching strategies.
Provides optimized caching for game business logic and NFT operations.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta

from .cache_service import get_cache_service
from .cache_keys import get_cache_key_builder
from .cache_decorators import cached, invalidate_cache, cache_business_data

import structlog

logger = structlog.get_logger(__name__)


class BusinessCacheManager:
    """Manages caching for business-related data."""
    
    def __init__(self):
        self.cache_service = None
        self.key_builder = None
    
    async def initialize(self):
        """Initialize cache manager."""
        self.cache_service = await get_cache_service()
        self.key_builder = get_cache_key_builder()
    
    # Business data caching
    @cached(ttl=3600, cache_type="business", key_prefix="business_full")
    async def get_business_with_details(self, business_id: str) -> Optional[Dict[str, Any]]:
        """Get complete business data with owner and NFT details."""
        # This would typically query the database
        # For now, return None to indicate cache miss
        return None
    
    async def cache_business_with_details(
        self, 
        business_id: str, 
        business_data: Dict[str, Any]
    ) -> bool:
        """Cache complete business data."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            # Cache main business data
            key = self.key_builder.business_key(business_id)
            await self.cache_service.set(key, business_data, cache_type="business")
            
            # Cache by owner for quick lookups
            if "owner" in business_data:
                owner_key = self.key_builder.build("business_by_owner", business_data["owner"], business_id)
                await self.cache_service.set(
                    owner_key, 
                    {"business_id": business_id, "cached_at": datetime.utcnow().isoformat()},
                    cache_type="business"
                )
            
            # Cache by type for filtering
            if "business_type" in business_data:
                type_key = self.key_builder.build("business_by_type", business_data["business_type"], business_id)
                await self.cache_service.set(
                    type_key,
                    {"business_id": business_id, "cached_at": datetime.utcnow().isoformat()},
                    cache_type="business"
                )
            
            logger.debug("Business data cached", business_id=business_id)
            return True
            
        except Exception as e:
            logger.error("Failed to cache business data", business_id=business_id, error=str(e))
            return False
    
    async def get_businesses_by_owner(self, wallet: str) -> List[Dict[str, Any]]:
        """Get all businesses owned by a wallet (cached)."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            # Try to get from cache first
            cache_key = self.key_builder.build("businesses_by_owner", wallet)
            cached_businesses = await self.cache_service.get(cache_key)
            
            if cached_businesses:
                logger.debug("Cache hit for businesses by owner", wallet=wallet)
                return cached_businesses
            
            # Cache miss - would query database here
            # For now, return empty list
            return []
            
        except Exception as e:
            logger.error("Failed to get businesses by owner", wallet=wallet, error=str(e))
            return []
    
    async def cache_businesses_by_owner(self, wallet: str, businesses: List[Dict[str, Any]]) -> bool:
        """Cache all businesses for a specific owner."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            cache_key = self.key_builder.build("businesses_by_owner", wallet)
            await self.cache_service.set(cache_key, businesses, cache_type="business")
            
            # Also cache individual businesses
            for business in businesses:
                if "business_id" in business:
                    await self.cache_business_with_details(business["business_id"], business)
            
            logger.debug("Businesses by owner cached", wallet=wallet, count=len(businesses))
            return True
            
        except Exception as e:
            logger.error("Failed to cache businesses by owner", wallet=wallet, error=str(e))
            return False
    
    async def get_businesses_by_type(self, business_type: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get businesses by type (cached)."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            cache_key = self.key_builder.build("businesses_by_type", business_type, limit)
            cached_businesses = await self.cache_service.get(cache_key)
            
            if cached_businesses:
                logger.debug("Cache hit for businesses by type", business_type=business_type)
                return cached_businesses
            
            # Cache miss - would query database here
            return []
            
        except Exception as e:
            logger.error("Failed to get businesses by type", business_type=business_type, error=str(e))
            return []
    
    async def invalidate_business_cache(self, business_id: str, owner: Optional[str] = None) -> bool:
        """Invalidate all cache entries for a business."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            # Get business data to find related cache keys
            business_key = self.key_builder.business_key(business_id)
            business_data = await self.cache_service.get(business_key)
            
            keys_to_invalidate = [business_key]
            
            if business_data:
                # Add owner-related keys
                if "owner" in business_data:
                    owner_pattern = self.key_builder.build("business_by_owner", business_data["owner"], "*")
                    owner_businesses_key = self.key_builder.build("businesses_by_owner", business_data["owner"])
                    keys_to_invalidate.extend([owner_businesses_key])
                
                # Add type-related keys
                if "business_type" in business_data:
                    type_pattern = self.key_builder.build("business_by_type", business_data["business_type"], "*")
                    # We'd need to get all keys matching this pattern
            
            # Also handle passed owner parameter
            if owner:
                owner_businesses_key = self.key_builder.build("businesses_by_owner", owner)
                keys_to_invalidate.append(owner_businesses_key)
            
            # Invalidate all keys
            deleted = await self.cache_service.delete(*keys_to_invalidate)
            
            logger.info("Business cache invalidated", business_id=business_id, keys_deleted=deleted)
            return True
            
        except Exception as e:
            logger.error("Failed to invalidate business cache", business_id=business_id, error=str(e))
            return False


class NFTCacheManager:
    """Manages caching for NFT-related data."""
    
    def __init__(self):
        self.cache_service = None
        self.key_builder = None
    
    async def initialize(self):
        """Initialize NFT cache manager."""
        self.cache_service = await get_cache_service()
        self.key_builder = get_cache_key_builder()
    
    async def cache_nft_metadata(self, mint: str, metadata: Dict[str, Any]) -> bool:
        """Cache NFT metadata."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            key = self.key_builder.business_nft_key(mint)
            await self.cache_service.set(key, metadata, cache_type="business", ttl=7200)  # 2 hours
            
            logger.debug("NFT metadata cached", mint=mint)
            return True
            
        except Exception as e:
            logger.error("Failed to cache NFT metadata", mint=mint, error=str(e))
            return False
    
    async def get_nft_metadata(self, mint: str) -> Optional[Dict[str, Any]]:
        """Get cached NFT metadata."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            key = self.key_builder.business_nft_key(mint)
            return await self.cache_service.get(key)
            
        except Exception as e:
            logger.error("Failed to get NFT metadata", mint=mint, error=str(e))
            return None
    
    async def cache_nft_ownership(self, mint: str, owner: str, business_id: Optional[str] = None) -> bool:
        """Cache NFT ownership information."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            ownership_data = {
                "mint": mint,
                "owner": owner,
                "business_id": business_id,
                "cached_at": datetime.utcnow().isoformat()
            }
            
            # Cache by mint
            mint_key = self.key_builder.build("nft_ownership", mint)
            await self.cache_service.set(mint_key, ownership_data, cache_type="business")
            
            # Cache by owner for quick lookups
            owner_key = self.key_builder.build("nft_by_owner", owner, mint)
            await self.cache_service.set(owner_key, ownership_data, cache_type="business")
            
            logger.debug("NFT ownership cached", mint=mint, owner=owner)
            return True
            
        except Exception as e:
            logger.error("Failed to cache NFT ownership", mint=mint, error=str(e))
            return False
    
    async def get_nfts_by_owner(self, owner: str) -> List[Dict[str, Any]]:
        """Get all NFTs owned by a wallet."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            # Get all NFT ownership keys for this owner
            pattern = self.key_builder.build("nft_by_owner", owner, "*")
            keys = await self.cache_service.redis.keys(pattern)
            
            if not keys:
                return []
            
            # Get all ownership data
            nft_data = []
            for key in keys:
                data = await self.cache_service.get(key)
                if data:
                    nft_data.append(data)
            
            logger.debug("NFTs by owner retrieved", owner=owner, count=len(nft_data))
            return nft_data
            
        except Exception as e:
            logger.error("Failed to get NFTs by owner", owner=owner, error=str(e))
            return []
    
    async def invalidate_nft_cache(self, mint: str) -> bool:
        """Invalidate all cache entries for an NFT."""
        if not self.cache_service:
            await self.initialize()
        
        try:
            # Get ownership data to find related keys
            mint_key = self.key_builder.build("nft_ownership", mint)
            ownership_data = await self.cache_service.get(mint_key)
            
            keys_to_invalidate = [
                self.key_builder.business_nft_key(mint),
                mint_key
            ]
            
            if ownership_data and "owner" in ownership_data:
                owner_key = self.key_builder.build("nft_by_owner", ownership_data["owner"], mint)
                keys_to_invalidate.append(owner_key)
            
            deleted = await self.cache_service.delete(*keys_to_invalidate)
            
            logger.info("NFT cache invalidated", mint=mint, keys_deleted=deleted)
            return True
            
        except Exception as e:
            logger.error("Failed to invalidate NFT cache", mint=mint, error=str(e))
            return False


# Global cache managers
_business_cache_manager: Optional[BusinessCacheManager] = None
_nft_cache_manager: Optional[NFTCacheManager] = None


async def get_business_cache_manager() -> BusinessCacheManager:
    """Get global business cache manager instance."""
    global _business_cache_manager
    
    if _business_cache_manager is None:
        _business_cache_manager = BusinessCacheManager()
        await _business_cache_manager.initialize()
    
    return _business_cache_manager


async def get_nft_cache_manager() -> NFTCacheManager:
    """Get global NFT cache manager instance."""
    global _nft_cache_manager
    
    if _nft_cache_manager is None:
        _nft_cache_manager = NFTCacheManager()
        await _nft_cache_manager.initialize()
    
    return _nft_cache_manager


# Convenience functions for decorators
@cache_business_data(ttl=1800)
async def get_business_earnings_projection(business_id: str, days: int = 7) -> Dict[str, Any]:
    """Get earnings projection for a business (cached)."""
    # This would calculate earnings projection
    return {
        "business_id": business_id,
        "projection_days": days,
        "estimated_earnings": 0,
        "calculated_at": datetime.utcnow().isoformat()
    }


@cache_business_data(ttl=3600)
async def get_business_market_value(business_id: str) -> Dict[str, Any]:
    """Get current market value for a business (cached)."""
    # This would calculate market value based on recent sales
    return {
        "business_id": business_id,
        "market_value": 0,
        "confidence": "low",
        "calculated_at": datetime.utcnow().isoformat()
    }


@cache_business_data(ttl=600)
async def get_business_activity_summary(business_id: str) -> Dict[str, Any]:
    """Get recent activity summary for a business (cached)."""
    # This would aggregate recent transactions and events
    return {
        "business_id": business_id,
        "recent_transactions": [],
        "last_upgrade": None,
        "earnings_claimed": 0,
        "summary_period": "24h",
        "calculated_at": datetime.utcnow().isoformat()
    }
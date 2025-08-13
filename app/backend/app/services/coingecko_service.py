"""
CoinGecko service for fetching real-time SOL price
"""
import asyncio
import aiohttp
import logging
from typing import Optional
import time

logger = logging.getLogger(__name__)

class CoinGeckoService:
    """Service for fetching SOL price from CoinGecko API"""
    
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.cache_duration = 60  # Cache for 1 minute
        self._cached_price = None
        self._cache_timestamp = 0
        
    async def get_sol_price_usd(self) -> Optional[float]:
        """Get current SOL price in USD"""
        try:
            # Check cache first
            current_time = time.time()
            if (self._cached_price is not None and 
                current_time - self._cache_timestamp < self.cache_duration):
                return self._cached_price
                
            # Fetch from API
            async with aiohttp.ClientSession() as session:
                url = f"{self.base_url}/simple/price"
                params = {
                    'ids': 'solana',
                    'vs_currencies': 'usd'
                }
                
                async with session.get(url, params=params, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        price = data.get('solana', {}).get('usd')
                        
                        if price:
                            # Update cache
                            self._cached_price = float(price)
                            self._cache_timestamp = current_time
                            logger.info(f"SOL price updated: ${price}")
                            return self._cached_price
                            
        except asyncio.TimeoutError:
            logger.warning("CoinGecko API timeout")
        except Exception as e:
            logger.error(f"Error fetching SOL price: {e}")
            
        return None
    
    async def get_sol_price_cents(self) -> Optional[int]:
        """Get SOL price in cents (for smart contract)"""
        price_usd = await self.get_sol_price_usd()
        if price_usd:
            return int(price_usd * 100)  # Convert to cents
        return None

# Global instance
coingecko_service = CoinGeckoService()
"""
Resilient Earnings Processor with fault-tolerant batch processing.

This service provides:
- Fault-tolerant daily earnings processing at 00:00 UTC
- Blockchain-as-source-of-truth architecture 
- Intelligent batch reading with progressive fallback
- Permissionless earnings updates (no admin privileges)
- Comprehensive error recovery and retry logic
- 1:1 consistency between database and blockchain state

REFACTORED: This file now uses modular architecture with components in:
- app.services.earnings.core - Main processor logic and types
- app.services.earnings.blockchain - Blockchain operations
- app.services.earnings.database - Database operations  
- app.services.earnings.transactions - Transaction processing
"""

from typing import Optional

# Import from new modular structure
from .earnings.core import ResilientEarningsProcessor, ProcessorStatus, ProcessorStats

# Re-export for backwards compatibility
__all__ = [
    "ResilientEarningsProcessor",
    "ProcessorStatus", 
    "ProcessorStats"
]

# Global instance for backwards compatibility
_resilient_earnings_processor: Optional[ResilientEarningsProcessor] = None


async def get_resilient_earnings_processor() -> ResilientEarningsProcessor:
    """Get or create global ResilientEarningsProcessor instance."""
    global _resilient_earnings_processor
    if _resilient_earnings_processor is None:
        _resilient_earnings_processor = ResilientEarningsProcessor()
        await _resilient_earnings_processor.initialize()
    return _resilient_earnings_processor


async def run_daily_earnings() -> ProcessorStats:
    """
    Convenience function to run daily earnings process.
    
    Returns:
        ProcessorStats with processing results
    """
    processor = await get_resilient_earnings_processor()
    return await processor.run_daily_earnings_process()
"""
Event indexer service for real-time processing of Solana Mafia program events.
Provides continuous monitoring and processing of blockchain events with database updates.

REFACTORED: This file now uses modular architecture with components in:
- app.indexer.core - Main indexer logic and types
- app.indexer.handlers - Event-specific handlers  
- app.indexer.monitoring - Real-time monitoring
- app.indexer.notifications - Notification services
"""

# Import from new modular structure
from .core import EventIndexer, IndexerStatus, ProcessingStats

# Re-export for backwards compatibility
__all__ = [
    "EventIndexer", 
    "IndexerStatus", 
    "ProcessingStats"
]

# Global indexer instance for backwards compatibility
_event_indexer = None


async def get_event_indexer() -> EventIndexer:
    """Get or create a global event indexer instance."""
    global _event_indexer
    if _event_indexer is None:
        _event_indexer = EventIndexer()
        await _event_indexer.initialize()
    return _event_indexer


async def shutdown_event_indexer():
    """Shutdown the global event indexer instance."""
    global _event_indexer
    if _event_indexer:
        await _event_indexer.shutdown()
        _event_indexer = None
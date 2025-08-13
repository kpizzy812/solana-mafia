"""
Core types for event indexing.
"""

from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class IndexerStatus(Enum):
    """Status of the event indexer."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"


@dataclass
class ProcessingStats:
    """Statistics for event processing."""
    events_processed: int = 0
    players_created: int = 0
    businesses_created: int = 0
    businesses_upgraded: int = 0
    businesses_sold: int = 0
    earnings_updated: int = 0
    earnings_claimed: int = 0
    nfts_minted: int = 0
    nfts_burned: int = 0
    errors: int = 0
    last_processed_slot: Optional[int] = None
    start_time: Optional[datetime] = None
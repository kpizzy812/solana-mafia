"""
Types for earnings processing.
"""

from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List

from solders.pubkey import Pubkey


class ProcessorStatus(Enum):
    """Status of the earnings processor."""
    IDLE = "idle"
    RUNNING = "running" 
    FAILED = "failed"
    COMPLETED = "completed"


@dataclass
class ProcessorStats:
    """Statistics for processor operations."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_players_found: int = 0
    players_needing_update: int = 0
    successful_updates: int = 0
    failed_updates: int = 0
    batch_reads_attempted: int = 0
    batch_reads_successful: int = 0
    individual_reads_fallback: int = 0
    database_sync_time: float = 0.0
    total_processing_time: float = 0.0
    # 🔥 НОВЫЕ ПОЛЯ: Business sync статистика
    business_sync_successful: int = 0
    business_sync_failed: int = 0
    business_sync_duration: float = 0.0
    businesses_synced_total: int = 0
    businesses_added_total: int = 0
    businesses_updated_total: int = 0
    portfolio_corrections_total: int = 0
    errors: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        if self.players_needing_update == 0:
            return 0.0
        return self.successful_updates / self.players_needing_update
    
    @property
    def business_sync_rate(self) -> float:
        """Business synchronization success rate."""
        total_sync_attempts = self.business_sync_successful + self.business_sync_failed
        if total_sync_attempts == 0:
            return 0.0
        return self.business_sync_successful / total_sync_attempts


@dataclass
class PlayerAccountData:
    """Parsed player account data from blockchain."""
    wallet: str
    pubkey: Pubkey
    pending_earnings: int
    next_earnings_time: int
    last_auto_update: int  
    businesses_count: int
    needs_update: bool
    raw_data: bytes
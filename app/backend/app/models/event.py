"""
Event model - stores indexed blockchain events.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

from sqlalchemy import (
    String, Integer, BigInteger, Text, Index, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import BaseModel, TimestampMixin


class EventType(Enum):
    """Event types matching the Solana program events."""
    
    # Player events
    PLAYER_CREATED = "player_created"
    
    # Business events
    BUSINESS_CREATED = "business_created"
    BUSINESS_UPGRADED = "business_upgraded" 
    BUSINESS_SOLD = "business_sold"
    
    # Earnings events
    EARNINGS_UPDATED = "earnings_updated"
    EARNINGS_CLAIMED = "earnings_claimed"
    
    # NFT events
    BUSINESS_NFT_MINTED = "business_nft_minted"
    BUSINESS_NFT_BURNED = "business_nft_burned"
    BUSINESS_NFT_UPGRADED = "business_nft_upgraded"
    BUSINESS_TRANSFERRED = "business_transferred"
    BUSINESS_DEACTIVATED = "business_deactivated"
    
    # Slot events
    SLOT_UNLOCKED = "slot_unlocked"
    PREMIUM_SLOT_PURCHASED = "premium_slot_purchased"
    BUSINESS_CREATED_IN_SLOT = "business_created_in_slot"
    BUSINESS_UPGRADED_IN_SLOT = "business_upgraded_in_slot"
    BUSINESS_SOLD_FROM_SLOT = "business_sold_from_slot"
    
    # Referral events
    REFERRAL_BONUS_ADDED = "referral_bonus_added"


class EventStatus(Enum):
    """Event processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    SKIPPED = "skipped"


class Event(BaseModel, TimestampMixin):
    """Event model for storing indexed blockchain events."""
    
    __tablename__ = "events"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Event identification
    event_type: Mapped[EventType] = mapped_column(
        SQLEnum(EventType),
        comment="Type of event"
    )
    
    transaction_signature: Mapped[str] = mapped_column(
        String(88),
        comment="Transaction signature"
    )
    
    instruction_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Instruction index within transaction"
    )
    
    event_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Event index within instruction"
    )
    
    # Blockchain data
    slot: Mapped[int] = mapped_column(
        BigInteger,
        comment="Blockchain slot number"
    )
    
    block_time: Mapped[datetime] = mapped_column(
        comment="Block timestamp"
    )
    
    # Event data
    raw_data: Mapped[Dict[str, Any]] = mapped_column(
        JSON,
        comment="Raw event data from blockchain"
    )
    
    parsed_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        comment="Parsed and structured event data"
    )
    
    # Related entities
    player_wallet: Mapped[Optional[str]] = mapped_column(
        String(44),
        comment="Related player wallet"
    )
    
    business_mint: Mapped[Optional[str]] = mapped_column(
        String(44),
        comment="Related business NFT mint"
    )
    
    # Processing status
    status: Mapped[EventStatus] = mapped_column(
        SQLEnum(EventStatus),
        default=EventStatus.PENDING,
        comment="Processing status"
    )
    
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        comment="When event was processed"
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Error message if processing failed"
    )
    
    retry_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of processing retries"
    )
    
    # Indexing metadata
    indexer_version: Mapped[str] = mapped_column(
        String(20),
        default="1.0",
        comment="Version of indexer that processed this event"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index("idx_event_type_slot", "event_type", "slot"),
        Index("idx_event_player_type", "player_wallet", "event_type"),
        Index("idx_event_signature_unique", "transaction_signature", "instruction_index", "event_index", unique=True),
        Index("idx_event_status_created", "status", "created_at"),
        Index("idx_event_block_time", "block_time"),
        Index("idx_event_business_mint", "business_mint"),
        Index("idx_event_pending_retry", "status", "retry_count"),
    )
    
    def __repr__(self) -> str:
        return f"<Event(id={self.id}, type={self.event_type.value}, signature={self.transaction_signature[:8]}...)>"
    
    @property
    def is_player_event(self) -> bool:
        """Check if this is a player-related event."""
        player_events = {
            EventType.PLAYER_CREATED,
            EventType.EARNINGS_UPDATED,
            EventType.EARNINGS_CLAIMED,
            EventType.SLOT_UNLOCKED,
            EventType.PREMIUM_SLOT_PURCHASED,
            EventType.REFERRAL_BONUS_ADDED,
        }
        return self.event_type in player_events
    
    @property
    def is_business_event(self) -> bool:
        """Check if this is a business-related event."""
        business_events = {
            EventType.BUSINESS_CREATED,
            EventType.BUSINESS_UPGRADED,
            EventType.BUSINESS_SOLD,
            EventType.BUSINESS_CREATED_IN_SLOT,
            EventType.BUSINESS_UPGRADED_IN_SLOT,
            EventType.BUSINESS_SOLD_FROM_SLOT,
        }
        return self.event_type in business_events
    
    @property
    def is_nft_event(self) -> bool:
        """Check if this is an NFT-related event."""
        nft_events = {
            EventType.BUSINESS_NFT_MINTED,
            EventType.BUSINESS_NFT_BURNED,
            EventType.BUSINESS_NFT_UPGRADED,
            EventType.BUSINESS_TRANSFERRED,
            EventType.BUSINESS_DEACTIVATED,
        }
        return self.event_type in nft_events
    
    def mark_as_processed(self) -> None:
        """Mark event as successfully processed."""
        self.status = EventStatus.PROCESSED
        self.processed_at = datetime.utcnow()
        self.error_message = None
    
    def mark_as_failed(self, error: str) -> None:
        """Mark event as failed with error message."""
        self.status = EventStatus.FAILED
        self.error_message = error
        self.retry_count += 1
    
    def mark_as_processing(self) -> None:
        """Mark event as currently being processed."""
        self.status = EventStatus.PROCESSING
    
    def can_retry(self, max_retries: int = 3) -> bool:
        """Check if event can be retried."""
        return self.status == EventStatus.FAILED and self.retry_count < max_retries
    
    def get_event_summary(self) -> str:
        """Get human-readable event summary."""
        summaries = {
            EventType.PLAYER_CREATED: f"Player {self.player_wallet} created",
            EventType.BUSINESS_CREATED: f"Business created by {self.player_wallet}",
            EventType.BUSINESS_UPGRADED: f"Business upgraded by {self.player_wallet}",
            EventType.BUSINESS_SOLD: f"Business sold by {self.player_wallet}",
            EventType.EARNINGS_UPDATED: f"Earnings updated for {self.player_wallet}",
            EventType.EARNINGS_CLAIMED: f"Earnings claimed by {self.player_wallet}",
            EventType.BUSINESS_NFT_MINTED: f"Business NFT {self.business_mint} minted",
            EventType.BUSINESS_NFT_BURNED: f"Business NFT {self.business_mint} burned",
        }
        
        return summaries.get(
            self.event_type,
            f"{self.event_type.value} event"
        )
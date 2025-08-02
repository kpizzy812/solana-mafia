"""
BusinessNFT model - tracks NFT ownership and metadata.
"""

from datetime import datetime
from typing import Optional, Dict, Any
import json

from sqlalchemy import (
    String, Integer, BigInteger, Boolean, Text, ForeignKey, Index, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel, TimestampMixin
from .business import BusinessType


class BusinessNFT(BaseModel, TimestampMixin):
    """Business NFT model for tracking NFT ownership and metadata."""
    
    __tablename__ = "business_nfts"
    
    # Primary key (NFT mint address)
    mint: Mapped[str] = mapped_column(
        String(44),
        primary_key=True,
        comment="NFT mint address"
    )
    
    # Current owner
    player_wallet: Mapped[str] = mapped_column(
        String(44),
        ForeignKey("players.wallet", ondelete="CASCADE"),
        comment="Current owner's wallet",
        index=True
    )
    
    # NFT metadata
    name: Mapped[str] = mapped_column(
        String(200),
        comment="NFT name"
    )
    
    symbol: Mapped[str] = mapped_column(
        String(10),
        comment="NFT symbol"
    )
    
    uri: Mapped[str] = mapped_column(
        Text,
        comment="Metadata URI"
    )
    
    # Business properties
    business_type: Mapped[BusinessType] = mapped_column(
        comment="Type of business this NFT represents"
    )
    
    level: Mapped[int] = mapped_column(
        Integer,
        default=1,
        comment="Business level"
    )
    
    serial_number: Mapped[int] = mapped_column(
        BigInteger,
        comment="Unique serial number for this business type"
    )
    
    # Investment tracking
    base_invested_amount: Mapped[int] = mapped_column(
        BigInteger,
        comment="Base investment amount in lamports"
    )
    
    total_invested_amount: Mapped[int] = mapped_column(
        BigInteger,
        comment="Total invested including upgrades in lamports"
    )
    
    daily_rate: Mapped[int] = mapped_column(
        Integer,
        comment="Daily rate in basis points"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        comment="Whether NFT is active"
    )
    
    is_burned: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether NFT has been burned"
    )
    
    # Timestamps
    minted_at: Mapped[datetime] = mapped_column(
        comment="When NFT was minted"
    )
    
    burned_at: Mapped[Optional[datetime]] = mapped_column(
        comment="When NFT was burned"
    )
    
    last_transfer_at: Mapped[Optional[datetime]] = mapped_column(
        comment="Last transfer timestamp"
    )
    
    # On-chain tracking
    mint_signature: Mapped[str] = mapped_column(
        String(88),
        comment="Transaction signature when NFT was minted"
    )
    
    burn_signature: Mapped[Optional[str]] = mapped_column(
        String(88),
        comment="Transaction signature when NFT was burned"
    )
    
    # Metadata cache
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        comment="Cached metadata JSON"
    )
    
    image_url: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="Direct image URL"
    )
    
    # Ownership history tracking
    previous_owner: Mapped[Optional[str]] = mapped_column(
        String(44),
        comment="Previous owner wallet"
    )
    
    transfer_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of times NFT has been transferred"
    )
    
    # Sync tracking
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        comment="Last sync with on-chain data"
    )
    
    ownership_verified_at: Mapped[Optional[datetime]] = mapped_column(
        comment="Last ownership verification timestamp"
    )
    
    # Relationships
    player: Mapped["Player"] = relationship(
        "Player",
        back_populates="nfts"
    )
    
    business: Mapped[Optional["Business"]] = relationship(
        "Business",
        back_populates="nft"
    )
    
    # Indexes
    __table_args__ = (
        Index("idx_nft_player_active", "player_wallet", "is_active"),
        Index("idx_nft_business_type", "business_type", "level"),
        Index("idx_nft_serial", "business_type", "serial_number"),
        Index("idx_nft_minted_at", "minted_at"),
        Index("idx_nft_burned", "is_burned"),
        Index("idx_nft_sync", "last_sync_at"),
    )
    
    def __repr__(self) -> str:
        return f"<BusinessNFT(mint={self.mint}, owner={self.player_wallet}, active={self.is_active})>"
    
    @property
    def display_name(self) -> str:
        """Get display name for the NFT."""
        business_names = {
            BusinessType.LEMONADE_STAND: "Lemonade Stand",
            BusinessType.CAR_WASH: "Car Wash", 
            BusinessType.RESTAURANT: "Restaurant",
            BusinessType.TECH_STARTUP: "Tech Startup",
            BusinessType.CRYPTO_EXCHANGE: "Crypto Exchange"
        }
        business_name = business_names.get(self.business_type, "Unknown")
        level_names = ["Basic", "Bronze", "Silver", "Gold", "Platinum", "Diamond"]
        level_name = level_names[min(self.level - 1, len(level_names) - 1)]
        
        return f"{level_name} {business_name} #{self.serial_number}"
    
    @property
    def estimated_value(self) -> int:
        """Get estimated current value of the NFT."""
        # Could implement more sophisticated valuation logic
        return self.total_invested_amount
    
    def update_metadata(self, metadata: Dict[str, Any]) -> None:
        """Update cached metadata."""
        self.metadata_json = metadata
        
        # Extract common fields
        if "name" in metadata:
            self.name = metadata["name"]
        if "symbol" in metadata:
            self.symbol = metadata["symbol"]
        if "image" in metadata:
            self.image_url = metadata["image"]
    
    def mark_as_burned(self, signature: str, burned_at: datetime) -> None:
        """Mark NFT as burned."""
        self.is_burned = True
        self.is_active = False
        self.burn_signature = signature
        self.burned_at = burned_at
    
    def transfer_to(self, new_owner: str, signature: str, transfer_time: datetime) -> None:
        """Record NFT transfer to new owner."""
        self.previous_owner = self.player_wallet
        self.player_wallet = new_owner
        self.transfer_count += 1
        self.last_transfer_at = transfer_time
    
    def verify_ownership(self) -> None:
        """Mark ownership as verified."""
        self.ownership_verified_at = datetime.utcnow()
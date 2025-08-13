"""
Business-related Pydantic schemas for API.
Defines data structures for business endpoints.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from uuid import UUID

from .common import (
    APIResponse,
    WalletField,
    BusinessNameField,
    LamportsField,
    BusinessType,
    SuccessResponse
)

import structlog


logger = structlog.get_logger(__name__)


class BusinessBase(BaseModel):
    """Base business model."""
    business_id: str = Field(description="Unique business identifier")
    owner: str = WalletField
    business_type: BusinessType
    name: str = BusinessNameField
    level: int = Field(ge=0, le=10, description="Business level (0-3, matches contract upgrade_level)")


class BusinessCreate(BaseModel):
    """Business creation request model."""
    business_type: BusinessType
    name: str = BusinessNameField
    slot_index: int = Field(ge=0, le=29, description="Slot index to place the business")


class BusinessUpgrade(BaseModel):
    """Business upgrade request model."""
    business_id: str = Field(description="Business ID to upgrade")


class BusinessSale(BaseModel):
    """Business sale request model."""
    business_id: str = Field(description="Business ID to sell")
    sale_price: Optional[int] = Field(default=None, description="Custom sale price in lamports")


class BusinessResponse(BusinessBase):
    """Business response model."""
    slot_index: int = Field(ge=0, le=29)
    cost: int = LamportsField
    earnings_per_hour: int = LamportsField
    # Убрано nft_mint поле - NFT больше не используются
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BusinessDetails(BusinessResponse):
    """Detailed business information."""
    total_earned: int = LamportsField
    last_earnings_update: datetime
    days_owned: int = Field(ge=0)
    upgrade_cost: Optional[int] = Field(default=None, description="Cost to upgrade to next level")
    sale_value: int = LamportsField
    penalty_amount: int = Field(ge=0, description="Early sale penalty")


class BusinessListResponse(BaseModel):
    """Business list response."""
    businesses: List[BusinessResponse]
    total_count: int = Field(ge=0)
    active_count: int = Field(ge=0)
    total_hourly_earnings: int = LamportsField


class BusinessMarketplace(BaseModel):
    """Business marketplace listing."""
    business_id: str
    seller: str = WalletField
    business_type: BusinessType
    name: str
    level: int = Field(ge=0, le=10)
    earnings_per_hour: int = LamportsField
    asking_price: int = LamportsField
    days_held: int = Field(ge=0)
    penalty_percentage: float = Field(ge=0.0, le=1.0)
    net_sale_price: int = LamportsField
    # Убрано nft_mint поле - NFT больше не используются
    listed_at: datetime


class BusinessMarketplaceResponse(BaseModel):
    """Business marketplace response."""
    listings: List[BusinessMarketplace]
    total_listings: int = Field(ge=0)
    price_range: dict = Field(
        description="Price statistics",
        example={"min": 1000000, "max": 10000000, "avg": 5000000}
    )


class BusinessStats(BaseModel):
    """Business statistics."""
    business_type: BusinessType
    total_created: int = Field(ge=0)
    total_active: int = Field(ge=0)
    average_level: float = Field(ge=0.0, le=10.0)
    total_earnings_generated: int = LamportsField
    average_price: int = LamportsField
    most_expensive_sale: int = LamportsField


class BusinessTypeStats(BaseModel):
    """Statistics for all business types."""
    stats_by_type: List[BusinessStats]
    total_businesses: int = Field(ge=0)
    total_active_businesses: int = Field(ge=0)
    most_popular_type: BusinessType
    highest_earning_type: BusinessType


class BusinessTransaction(BaseModel):
    """Business transaction record."""
    transaction_type: str = Field(description="Type: created, upgraded, sold, transferred")
    business_id: str
    from_wallet: Optional[str] = None
    to_wallet: Optional[str] = None
    amount: int = LamportsField
    level: Optional[int] = None
    timestamp: datetime
    transaction_signature: str
    block_slot: int = Field(ge=0)


class BusinessHistory(BaseModel):
    """Business transaction history."""
    business_id: str
    current_owner: str = WalletField
    creation_date: datetime
    transactions: List[BusinessTransaction]
    total_transactions: int = Field(ge=0)
    total_volume: int = LamportsField


class BusinessEarningsProjection(BaseModel):
    """Business earnings projection."""
    business_id: str
    current_level: int = Field(ge=0, le=10)
    current_earnings_per_hour: int = LamportsField
    projections: List[dict] = Field(
        description="Earnings projections for different time periods",
        example=[
            {"period": "1_hour", "earnings": 1000},
            {"period": "1_day", "earnings": 24000},
            {"period": "1_week", "earnings": 168000},
            {"period": "1_month", "earnings": 720000}
        ]
    )
    
    
class BusinessUpgradeInfo(BaseModel):
    """Business upgrade information."""
    business_id: str
    current_level: int = Field(ge=0, le=9)
    next_level: int = Field(ge=1, le=10)
    upgrade_cost: int = LamportsField
    current_earnings_per_hour: int = LamportsField
    upgraded_earnings_per_hour: int = LamportsField
    earnings_increase: int = LamportsField
    roi_hours: float = Field(ge=0.0, description="Hours to break even on upgrade cost")


class BusinessSaleInfo(BaseModel):
    """Business sale information."""
    business_id: str
    current_value: int = LamportsField
    days_held: int = Field(ge=0)
    penalty_rate: float = Field(ge=0.0, le=1.0)
    penalty_amount: int = LamportsField
    net_sale_value: int = LamportsField
    break_even_days: int = Field(ge=0, description="Days to hold for no penalty")


# Response wrappers
class BusinessResponseWrapper(SuccessResponse):
    """Single business response wrapper."""
    data: BusinessResponse


class BusinessListResponseWrapper(SuccessResponse):
    """Business list response wrapper."""
    data: BusinessListResponse


class BusinessDetailsResponseWrapper(SuccessResponse):
    """Business details response wrapper."""
    data: BusinessDetails
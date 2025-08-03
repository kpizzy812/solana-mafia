"""
Common Pydantic schemas for API responses and requests.
Provides base classes and common data structures.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum

import structlog


logger = structlog.get_logger(__name__)


class APIResponse(BaseModel):
    """Base API response model."""
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda dt: dt.isoformat(),
        },
        populate_by_name=True,
    )
    
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class SuccessResponse(APIResponse):
    """Success response model."""
    data: Optional[Any] = None


class ErrorResponse(APIResponse):
    """Error response model."""
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints."""
    limit: int = Field(default=50, ge=1, le=1000, description="Number of items per page")
    offset: int = Field(default=0, ge=0, description="Number of items to skip")
    

class PaginatedResponse(SuccessResponse):
    """Paginated response model."""
    data: List[Any]
    pagination: Dict[str, Any] = Field(
        description="Pagination metadata",
        example={
            "total": 100,
            "limit": 50,
            "offset": 0,
            "has_next": True,
            "has_previous": False
        }
    )


class SortOrder(str, Enum):
    """Sort order enumeration."""
    ASC = "asc"
    DESC = "desc"


class SortParams(BaseModel):
    """Sort parameters for list endpoints."""
    sort_by: Optional[str] = Field(default=None, description="Field to sort by")
    sort_order: SortOrder = Field(default=SortOrder.DESC, description="Sort order")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    services: Dict[str, str] = Field(
        default_factory=lambda: {
            "database": "healthy",
            "blockchain": "healthy",
            "cache": "healthy"
        }
    )


class WalletAddress(BaseModel):
    """Wallet address validation model."""
    address: str = Field(
        min_length=32,
        max_length=44,
        pattern=r"^[A-Za-z0-9]+$",
        description="Solana wallet address"
    )


class BusinessType(int, Enum):
    """Business type enumeration matching on-chain enum."""
    TOBACCO_SHOP = 0       # Lucky Strike Cigars
    FUNERAL_SERVICE = 1    # Eternal Rest Funeral  
    CAR_WORKSHOP = 2       # Midnight Motors Garage
    ITALIAN_RESTAURANT = 3 # Nonna's Secret Kitchen
    GENTLEMEN_CLUB = 4     # Velvet Shadows Club
    CHARITY_FUND = 5       # Angel's Mercy Foundation


class TransactionStatus(str, Enum):
    """Transaction status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class EventType(str, Enum):
    """Event type enumeration."""
    PLAYER_CREATED = "PlayerCreated"
    BUSINESS_CREATED = "BusinessCreated"
    BUSINESS_UPGRADED = "BusinessUpgraded"
    BUSINESS_SOLD = "BusinessSold"
    EARNINGS_UPDATED = "EarningsUpdated"
    EARNINGS_CLAIMED = "EarningsClaimed"
    NFT_MINTED = "BusinessNFTMinted"
    NFT_BURNED = "BusinessNFTBurned"
    NFT_UPGRADED = "BusinessNFTUpgraded"


class APIError(BaseModel):
    """API error details."""
    code: str
    message: str
    field: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ValidationErrorResponse(ErrorResponse):
    """Validation error response."""
    error_code: str = "VALIDATION_ERROR"
    errors: List[APIError] = Field(default_factory=list)


# Common field types
WalletField = Field(
    min_length=32,
    max_length=44,
    pattern=r"^[A-Za-z0-9]+$",
    description="Solana wallet address"
)

NFTMintField = Field(
    min_length=32,
    max_length=44,
    pattern=r"^[A-Za-z0-9]+$",
    description="NFT mint address"
)

BusinessNameField = Field(
    min_length=1,
    max_length=32,
    description="Business name"
)

LamportsField = Field(
    ge=0,
    description="Amount in lamports"
)


def create_success_response(data: Any = None, message: str = None) -> SuccessResponse:
    """Create a success response."""
    return SuccessResponse(data=data, message=message)


def create_error_response(
    message: str,
    error_code: str = None,
    details: Dict[str, Any] = None
) -> ErrorResponse:
    """Create an error response."""
    return ErrorResponse(
        message=message,
        error_code=error_code,
        details=details
    )


def create_paginated_response(
    data: List[Any],
    total: int,
    limit: int,
    offset: int
) -> PaginatedResponse:
    """Create a paginated response."""
    has_next = offset + limit < total
    has_previous = offset > 0
    
    return PaginatedResponse(
        data=data,
        pagination={
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_next": has_next,
            "has_previous": has_previous
        }
    )
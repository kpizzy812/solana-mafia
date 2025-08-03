"""
Business routes for the Solana Mafia API.
Handles business-related endpoints including creation, upgrades, and marketplace.
"""

from fastapi import APIRouter, HTTPException, status
from app.api.schemas.common import SuccessResponse, create_success_response

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "/",
    response_model=SuccessResponse,
    summary="List All Businesses",
    description="Retrieve a list of all businesses in the game"
)
async def list_businesses():
    """List all businesses (placeholder)."""
    return create_success_response(
        data={"message": "Business endpoints coming soon"},
        message="Business routes are under development"
    )


@router.get(
    "/{business_id}",
    response_model=SuccessResponse,
    summary="Get Business Details",
    description="Retrieve detailed information about a specific business"
)
async def get_business_details(business_id: str):
    """Get business details by ID (placeholder)."""
    return create_success_response(
        data={"business_id": business_id, "message": "Business details coming soon"},
        message="Business details endpoint is under development"
    )
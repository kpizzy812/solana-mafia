"""
Earnings routes for the Solana Mafia API.
Handles earnings-related endpoints including claiming and history.
"""

from fastapi import APIRouter, HTTPException, status
from app.api.schemas.common import SuccessResponse, create_success_response

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "/{wallet}",
    response_model=SuccessResponse,
    summary="Get Player Earnings",
    description="Retrieve current earnings information for a player"
)
async def get_player_earnings(wallet: str):
    """Get player earnings (placeholder)."""
    return create_success_response(
        data={"wallet": wallet, "message": "Earnings endpoints coming soon"},
        message="Earnings routes are under development"
    )


@router.post(
    "/{wallet}/claim",
    response_model=SuccessResponse,
    summary="Claim Earnings",
    description="Claim available earnings for a player"
)
async def claim_earnings(wallet: str):
    """Claim earnings (placeholder)."""
    return create_success_response(
        data={"wallet": wallet, "message": "Earnings claiming coming soon"},
        message="Earnings claiming endpoint is under development"
    )
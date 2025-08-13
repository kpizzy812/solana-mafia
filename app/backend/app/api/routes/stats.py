"""
Statistics routes for the Solana Mafia API.
Handles global statistics and leaderboards.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from app.api.dependencies import get_database
from app.api.schemas.common import SuccessResponse, create_success_response
from app.models.player import Player
from app.models.business import Business
from app.core.config import settings

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "/global",
    response_model=SuccessResponse,
    summary="Get Global Statistics",
    description="Retrieve global game statistics and metrics"
)
async def get_global_stats(db: AsyncSession = Depends(get_database)):
    """Get global statistics."""
    try:
        # Get total players count
        total_players_result = await db.execute(
            select(func.count(distinct(Player.wallet))).where(Player.is_active == True)
        )
        total_players = total_players_result.scalar() or 0
        
        # Get total businesses count
        total_businesses_result = await db.execute(
            select(func.count(Business.id)).where(Business.is_active == True)
        )
        total_businesses = total_businesses_result.scalar() or 0
        
        # Get total invested amount
        total_invested_result = await db.execute(
            select(func.sum(Player.total_invested))
        )
        total_invested = total_invested_result.scalar() or 0
        
        # Get total earnings
        total_earnings_result = await db.execute(
            select(func.sum(Player.total_earned))
        )
        total_earnings = total_earnings_result.scalar() or 0
        
        # Get current pricing info from dynamic pricing service
        try:
            from app.services.coingecko_service import coingecko_service
            from app.services.dynamic_pricing_service import dynamic_pricing_service
            
            sol_price = await coingecko_service.get_sol_price_usd()
            dynamic_fee_usd = dynamic_pricing_service.calculate_entry_fee_usd(total_players)
            current_fee = dynamic_pricing_service.last_entry_fee
            
            if not current_fee and sol_price:
                current_fee = dynamic_pricing_service.calculate_entry_fee_lamports(total_players, sol_price)
                
        except Exception as e:
            logger.warning("Could not get dynamic pricing info", error=str(e))
            sol_price = None
            dynamic_fee_usd = 2.0  # Default
            current_fee = 12_345_679  # Default
        
        global_stats = {
            "total_players": total_players,
            "total_businesses": total_businesses,
            "total_invested": total_invested,
            "total_earnings": total_earnings,
            "current_entry_fee": current_fee,
            "current_entry_fee_usd": dynamic_fee_usd,
            "sol_price_usd": sol_price,
            "pricing_enabled": getattr(settings, 'dynamic_pricing_enabled', False)
        }
        
        logger.info("Global statistics retrieved", stats=global_stats)
        return create_success_response(
            data=global_stats,
            message="Global statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error retrieving global statistics", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "GLOBAL_STATS_ERROR",
                "message": "Failed to retrieve global statistics"
            }
        )


@router.get(
    "/leaderboard",
    response_model=SuccessResponse,
    summary="Get Leaderboard",
    description="Retrieve player leaderboard rankings"
)
async def get_leaderboard():
    """Get leaderboard (placeholder)."""
    return create_success_response(
        data={"message": "Leaderboard coming soon"},
        message="Leaderboard endpoint is under development"
    )


@router.get(
    "/sol-price",
    response_model=SuccessResponse,
    summary="Get SOL Price",
    description="Get current SOL price in USD and entry fee information"
)
async def get_sol_price():
    """Get current SOL price and entry fee info."""
    try:
        from app.services.coingecko_service import coingecko_service
        from app.services.dynamic_pricing_service import dynamic_pricing_service
        
        # Get SOL price
        sol_price = await coingecko_service.get_sol_price_usd()
        
        # Get total players for dynamic fee calculation
        total_players = await dynamic_pricing_service.get_total_players()
        
        # Calculate dynamic fee
        dynamic_fee_usd = dynamic_pricing_service.calculate_entry_fee_usd(total_players)
        current_fee_lamports = dynamic_pricing_service.last_entry_fee
        
        if not current_fee_lamports and sol_price:
            current_fee_lamports = dynamic_pricing_service.calculate_entry_fee_lamports(total_players, sol_price)
        
        price_data = {
            "sol_price_usd": sol_price,
            "current_entry_fee_usd": dynamic_fee_usd,
            "current_entry_fee_lamports": current_fee_lamports,
            "current_entry_fee_sol": current_fee_lamports / 1_000_000_000 if current_fee_lamports else None,
            "total_players": total_players,
            "last_updated": "live" if sol_price else "cache"
        }
        
        return create_success_response(
            data=price_data,
            message="SOL price information retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error getting SOL price", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve SOL price information"
        )
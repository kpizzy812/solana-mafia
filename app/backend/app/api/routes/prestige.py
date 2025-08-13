"""
API routes for prestige system.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database
from app.services.prestige_service import get_prestige_service, PrestigeService
from app.models.prestige import ActionType
from app.api.schemas.prestige import (
    PrestigeInfo, PrestigeHistoryResponse, PrestigeLeaderboardResponse,
    PrestigeActionResponse, PrestigeRecalculateResponse, PrestigeLevelsResponse,
    PrestigeSystemStatus
)
from app.api.schemas.common import APIResponse, SuccessResponse

router = APIRouter(tags=["prestige"])


@router.get("/levels", response_model=SuccessResponse)
async def get_prestige_levels(
    db: AsyncSession = Depends(get_database)
):
    """Get all prestige levels and their requirements."""
    try:
        prestige_service = await get_prestige_service(db)
        
        # Get all levels
        from sqlalchemy import select
        from app.models.prestige import PrestigeLevel
        
        result = await db.execute(
            select(PrestigeLevel)
            .where(PrestigeLevel.is_active == True)
            .order_by(PrestigeLevel.order_rank)
        )
        levels = result.scalars().all()
        
        return SuccessResponse(
            success=True,
            data=PrestigeLevelsResponse(levels=levels)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get prestige levels: {str(e)}")


@router.get("/leaderboard", response_model=SuccessResponse)
async def get_prestige_leaderboard(
    period: str = Query("all", description="Period: all, weekly, monthly"),
    limit: int = Query(100, ge=1, le=1000, description="Number of entries to return"),
    db: AsyncSession = Depends(get_database)
):
    """Get prestige leaderboard."""
    try:
        prestige_service = await get_prestige_service(db)
        leaderboard = await prestige_service.get_prestige_leaderboard(
            limit=limit,
            period=period
        )
        
        return SuccessResponse(
            success=True,
            data=PrestigeLeaderboardResponse(
                period=period,
                total_players=len(leaderboard),
                entries=leaderboard
            )
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get leaderboard: {str(e)}")


@router.get("/status", response_model=SuccessResponse)
async def get_prestige_system_status(
    db: AsyncSession = Depends(get_database)
):
    """Get overall prestige system status and statistics."""
    try:
        from sqlalchemy import select, func
        from app.models.player import Player
        
        # Get system stats
        result = await db.execute(
            select(
                func.count(Player.wallet).label("total_players"),
                func.avg(Player.prestige_points).label("avg_points"),
                func.count().filter(Player.prestige_level == "boss").label("boss_count")
            ).where(Player.prestige_points > 0)
        )
        stats = result.first()
        
        # Get level distribution
        level_result = await db.execute(
            select(
                Player.prestige_level,
                func.count(Player.wallet).label("count")
            ).group_by(Player.prestige_level)
        )
        level_distribution = {level: count for level, count in level_result.all()}
        
        return SuccessResponse(
            success=True,
            data=PrestigeSystemStatus(
                is_enabled=True,
                total_players_with_prestige=stats.total_players or 0,
                average_points=float(stats.avg_points or 0),
                level_distribution=level_distribution,
                top_level_players=stats.boss_count or 0
            )
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")


# Player-specific prestige endpoints
@router.get("/players/{wallet}", response_model=SuccessResponse)
async def get_player_prestige(
    wallet: str = Path(..., description="Player wallet address"),
    db: AsyncSession = Depends(get_database)
):
    """Get comprehensive prestige information for a player."""
    try:
        prestige_service = await get_prestige_service(db)
        prestige_info = await prestige_service.get_player_prestige_info(wallet)
        
        if not prestige_info:
            raise HTTPException(status_code=404, detail="Player not found")
        
        return SuccessResponse(
            success=True,
            data=PrestigeInfo(**prestige_info)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get player prestige: {str(e)}")


@router.get("/players/{wallet}/history", response_model=SuccessResponse)
async def get_player_prestige_history(
    wallet: str = Path(..., description="Player wallet address"),
    limit: int = Query(50, ge=1, le=200, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    action_type: Optional[str] = Query(None, description="Filter by action type"),
    db: AsyncSession = Depends(get_database)
):
    """Get prestige history for a player."""
    try:
        prestige_service = await get_prestige_service(db)
        
        # Convert action_type string to enum if provided
        action_type_enum = None
        if action_type:
            try:
                action_type_enum = ActionType(action_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid action type: {action_type}")
        
        history = await prestige_service.get_prestige_history(
            player_wallet=wallet,
            limit=limit,
            offset=offset,
            action_type=action_type_enum
        )
        
        return SuccessResponse(
            success=True,
            data=PrestigeHistoryResponse(
                wallet=wallet,
                total_entries=len(history),
                entries=history
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get prestige history: {str(e)}")


@router.post("/players/{wallet}/recalculate", response_model=SuccessResponse)
async def recalculate_player_prestige(
    wallet: str = Path(..., description="Player wallet address"),
    db: AsyncSession = Depends(get_database)
):
    """Recalculate prestige for a player based on all their activities."""
    try:
        prestige_service = await get_prestige_service(db)
        result = await prestige_service.recalculate_player_prestige(wallet)
        
        await db.commit()
        
        return SuccessResponse(
            success=True,
            data=PrestigeRecalculateResponse(**result)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to recalculate prestige: {str(e)}")


@router.post("/initialize", response_model=SuccessResponse)
async def initialize_prestige_system(
    db: AsyncSession = Depends(get_database)
):
    """Initialize the prestige system with default levels and actions."""
    try:
        prestige_service = await get_prestige_service(db)
        await prestige_service.initialize_system()
        await db.commit()
        
        return SuccessResponse(
            success=True,
            data={
                "message": "Prestige system initialized successfully",
                "timestamp": datetime.utcnow()
            }
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to initialize prestige system: {str(e)}")


# Internal endpoints for awarding points (used by other services)
@router.post("/award/{wallet}/business-purchase", response_model=SuccessResponse)
async def award_business_purchase_points(
    wallet: str = Path(..., description="Player wallet address"),
    business_cost: int = Query(..., description="Business cost in lamports"),
    business_type: int = Query(..., description="Business type ID"),
    slot_index: int = Query(..., description="Slot index"),
    transaction_signature: Optional[str] = Query(None, description="Transaction signature"),
    db: AsyncSession = Depends(get_database)
):
    """Award prestige points for business purchase."""
    try:
        prestige_service = await get_prestige_service(db)
        points_awarded, level_up = await prestige_service.award_business_purchase_points(
            player_wallet=wallet,
            business_cost=business_cost,
            business_type=business_type,
            slot_index=slot_index,
            transaction_signature=transaction_signature
        )
        
        # Get updated player info
        from app.models.player import Player
        from sqlalchemy import select
        
        result = await db.execute(select(Player).where(Player.wallet == wallet))
        player = result.scalar_one_or_none()
        
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        await db.commit()
        
        return SuccessResponse(
            success=True,
            data=PrestigeActionResponse(
                success=True,
                points_awarded=points_awarded,
                level_up_occurred=level_up,
                new_total_points=player.prestige_points,
                new_level=player.prestige_level,
                message=f"Awarded {points_awarded} prestige points for business purchase"
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to award points: {str(e)}")


@router.post("/award/{wallet}/referral", response_model=SuccessResponse)
async def award_referral_points(
    wallet: str = Path(..., description="Referrer wallet address"),
    referee_wallet: str = Query(..., description="Referee wallet address"),
    referral_type: str = Query("invited", description="Type: invited, first_business, network_bonus"),
    db: AsyncSession = Depends(get_database)
):
    """Award prestige points for referral activities."""
    try:
        prestige_service = await get_prestige_service(db)
        points_awarded, level_up = await prestige_service.award_referral_points(
            referrer_wallet=wallet,
            referee_wallet=referee_wallet,
            referee_points=0,  # Will be calculated by service
            referral_type=referral_type
        )
        
        # Get updated player info
        from app.models.player import Player
        from sqlalchemy import select
        
        result = await db.execute(select(Player).where(Player.wallet == wallet))
        player = result.scalar_one_or_none()
        
        if not player:
            raise HTTPException(status_code=404, detail="Player not found")
        
        await db.commit()
        
        return SuccessResponse(
            success=True,
            data=PrestigeActionResponse(
                success=True,
                points_awarded=points_awarded,
                level_up_occurred=level_up,
                new_total_points=player.prestige_points,
                new_level=player.prestige_level,
                message=f"Awarded {points_awarded} prestige points for {referral_type}"
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to award referral points: {str(e)}")
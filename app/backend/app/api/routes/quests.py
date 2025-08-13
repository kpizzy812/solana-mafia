"""
API routes for quest system.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_database
from app.services.quest_service import get_quest_service, QuestService
from app.models.quest import QuestType, QuestDifficulty
from app.api.schemas.quest import (
    QuestListResponse, QuestWithProgress, QuestCategoryInfo, PlayerQuestStatsResponse,
    QuestClaimRequest, QuestClaimResponse, QuestProgressUpdateRequest, 
    QuestProgressUpdateResponse, QuestStartRequest, QuestStartResponse,
    QuestDetailedInfo, QuestSystemStatusResponse, QuestLeaderboardResponse,
    QuestValidationResponse, DailyQuestResponse, QuestBulkOperationRequest,
    QuestBulkOperationResponse, QuestTypeEnum, QuestDifficultyEnum
)
from app.api.schemas.common import APIResponse, SuccessResponse

router = APIRouter(tags=["quests"])


@router.get("/", response_model=SuccessResponse)
async def get_all_quests(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    quest_type: Optional[QuestTypeEnum] = Query(None, description="Filter by quest type"),
    difficulty: Optional[QuestDifficultyEnum] = Query(None, description="Filter by difficulty"),
    is_active: bool = Query(True, description="Filter by active status"),
    include_expired: bool = Query(False, description="Include expired quests"),
    db: AsyncSession = Depends(get_database)
):
    """Get all quests with optional filtering."""
    try:
        quest_service = await get_quest_service(db)
        
        # Convert enum to model enum if provided
        quest_type_model = QuestType(quest_type.value) if quest_type else None
        difficulty_model = QuestDifficulty(difficulty.value) if difficulty else None
        
        quests = await quest_service.get_all_quests(
            category_id=category_id,
            quest_type=quest_type_model,
            difficulty=difficulty_model,
            is_active=is_active,
            include_expired=include_expired
        )
        
        categories = await quest_service.get_quest_categories(is_active=True)
        
        quest_data = []
        for quest in quests:
            quest_data.append({
                "quest": quest,
                "progress": None,  # No progress for general quest list
                "category": quest.category
            })
        
        return SuccessResponse(
            success=True,
            data=QuestListResponse(
                quests=quest_data,
                categories=categories,
                total_quests=len(quests),
                completed_count=0,
                claimed_count=0,
                available_to_claim=0
            )
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get quests: {str(e)}")


@router.get("/categories", response_model=SuccessResponse)
async def get_quest_categories(
    is_active: bool = Query(True, description="Filter by active status"),
    db: AsyncSession = Depends(get_database)
):
    """Get all quest categories."""
    try:
        quest_service = await get_quest_service(db)
        categories = await quest_service.get_quest_categories(is_active=is_active)
        
        return SuccessResponse(
            success=True,
            data={"categories": categories}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get categories: {str(e)}")


@router.get("/players/{wallet}", response_model=SuccessResponse)
async def get_player_quests(
    wallet: str = Path(..., description="Player wallet address"),
    include_completed: bool = Query(True, description="Include completed quests"),
    include_claimed: bool = Query(True, description="Include claimed quests"),
    db: AsyncSession = Depends(get_database)
):
    """Get quests for a specific player with their progress."""
    try:
        quest_service = await get_quest_service(db)
        
        # Get quests with progress
        quests_with_progress = await quest_service.get_quests_for_player(
            player_wallet=wallet,
            include_completed=include_completed,
            include_claimed=include_claimed
        )
        
        # Get categories
        categories = await quest_service.get_quest_categories(is_active=True)
        
        # Calculate stats
        completed_count = sum(1 for q in quests_with_progress 
                            if q["progress"] and q["progress"].is_completed)
        claimed_count = sum(1 for q in quests_with_progress 
                          if q["progress"] and q["progress"].is_claimed)
        available_to_claim = sum(1 for q in quests_with_progress 
                               if q["progress"] and q["progress"].is_ready_to_claim)
        
        return SuccessResponse(
            success=True,
            data=QuestListResponse(
                quests=quests_with_progress,
                categories=categories,
                total_quests=len(quests_with_progress),
                completed_count=completed_count,
                claimed_count=claimed_count,
                available_to_claim=available_to_claim
            )
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get player quests: {str(e)}")


@router.get("/players/{wallet}/stats", response_model=SuccessResponse)
async def get_player_quest_stats(
    wallet: str = Path(..., description="Player wallet address"),
    db: AsyncSession = Depends(get_database)
):
    """Get quest statistics for a player."""
    try:
        quest_service = await get_quest_service(db)
        stats = await quest_service.get_player_quest_stats(wallet)
        
        return SuccessResponse(
            success=True,
            data=PlayerQuestStatsResponse(**stats)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get player stats: {str(e)}")


@router.post("/start", response_model=SuccessResponse)
async def start_quest(
    request: QuestStartRequest,
    db: AsyncSession = Depends(get_database)
):
    """Start a quest for a player."""
    try:
        quest_service = await get_quest_service(db)
        progress = await quest_service.start_quest(
            player_wallet=request.player_wallet,
            quest_id=request.quest_id
        )
        
        await db.commit()
        
        return SuccessResponse(
            success=True,
            data=QuestStartResponse(
                success=True,
                quest_progress=progress,
                message="Quest started successfully"
            )
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/progress/update", response_model=SuccessResponse)
async def update_quest_progress(
    request: QuestProgressUpdateRequest,
    db: AsyncSession = Depends(get_database)
):
    """Update quest progress for a player."""
    try:
        quest_service = await get_quest_service(db)
        
        quest_type_model = QuestType(request.quest_type.value) if request.quest_type else None
        
        updated_records = await quest_service.update_quest_progress(
            player_wallet=request.player_wallet,
            quest_type=quest_type_model,
            progress_value=request.progress_value,
            metadata=request.metadata
        )
        
        # Get newly completed quests
        newly_completed = []
        for progress in updated_records:
            if progress.is_completed:
                quest = await quest_service.get_quest_by_id(progress.quest_id)
                if quest:
                    newly_completed.append(quest)
        
        await db.commit()
        
        return SuccessResponse(
            success=True,
            data=QuestProgressUpdateResponse(
                success=True,
                updated_quests=updated_records,
                newly_completed=newly_completed,
                message=f"Updated {len(updated_records)} quest(s)"
            )
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{quest_id}/progress", response_model=SuccessResponse)
async def update_specific_quest_progress(
    quest_id: int = Path(..., description="Quest ID"),
    player_wallet: str = Query(..., description="Player wallet address"),
    progress_value: int = Query(..., description="Progress value to set"),
    db: AsyncSession = Depends(get_database)
):
    """Update progress for a specific quest."""
    try:
        quest_service = await get_quest_service(db)
        
        # Get the quest first
        quest = await quest_service.get_quest_by_id(quest_id)
        if not quest:
            raise HTTPException(status_code=404, detail="Quest not found")
        
        # Update progress for this specific quest type
        quest_type_enum = QuestType(quest.quest_type)
        updated_records = await quest_service.update_quest_progress(
            player_wallet=player_wallet,
            quest_type=quest_type_enum,
            progress_value=progress_value,
            metadata={"quest_id": quest_id}
        )
        
        await db.commit()
        
        return SuccessResponse(
            success=True,
            data={
                "success": True,
                "updated_quests": len(updated_records),
                "message": f"Progress updated for quest {quest_id}"
            }
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{quest_id}/claim", response_model=SuccessResponse)
async def claim_quest_reward(
    quest_id: int = Path(..., description="Quest ID"),
    request: QuestClaimRequest = ...,
    db: AsyncSession = Depends(get_database)
):
    """Claim reward for a completed quest."""
    print(f"🚨 API QUEST CLAIM CALLED: quest_id={quest_id}, wallet={request.player_wallet}")
    try:
        quest_service = await get_quest_service(db)
        print(f"🚨 quest_service obtained, about to call claim_quest_reward")
        result = await quest_service.claim_quest_reward(
            player_wallet=request.player_wallet,
            quest_id=quest_id
        )
        print(f"🚨 quest_service.claim_quest_reward returned: {result}")
        
        await db.commit()
        
        return SuccessResponse(
            success=True,
            data=QuestClaimResponse(
                success=True,
                quest_id=quest_id,
                prestige_points_awarded=result["prestige_points_awarded"],
                bonus_reward_awarded=result["bonus_reward_awarded"],
                new_total_prestige=result["new_total_prestige"],
                message="Quest reward claimed successfully",
                next_quest_unlocked=result.get("next_quest_unlocked")
            )
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/leaderboard", response_model=SuccessResponse)
async def get_quest_leaderboard(
    period: str = Query("all", description="Period: all, weekly, monthly"),
    limit: int = Query(50, ge=1, le=100, description="Number of entries"),
    db: AsyncSession = Depends(get_database)
):
    """Get quest completion leaderboard."""
    try:
        quest_service = await get_quest_service(db)
        leaderboard = await quest_service.get_quest_leaderboard(
            limit=limit,
            period=period
        )
        
        return SuccessResponse(
            success=True,
            data=QuestLeaderboardResponse(
                period=period,
                total_players=len(leaderboard),
                entries=leaderboard
            )
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get leaderboard: {str(e)}")


@router.get("/daily/{wallet}", response_model=SuccessResponse)
async def get_daily_quests(
    wallet: str = Path(..., description="Player wallet address"),
    db: AsyncSession = Depends(get_database)
):
    """Get daily quests for a player."""
    try:
        quest_service = await get_quest_service(db)
        
        # Get all quests for player, filter for daily ones
        all_quests = await quest_service.get_quests_for_player(wallet)
        daily_quests = [q for q in all_quests if q["quest"].is_daily]
        
        # Calculate streak (simplified - would need more complex logic)
        streak_count = 0
        
        # Next reset time (simplified - next midnight)
        from datetime import datetime, timedelta
        tomorrow = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        return SuccessResponse(
            success=True,
            data=DailyQuestResponse(
                daily_quests=daily_quests,
                streak_count=streak_count,
                last_completion=None,
                next_reset=tomorrow,
                bonus_multiplier=1.0 + (streak_count * 0.1)  # 10% per streak day
            )
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get daily quests: {str(e)}")


@router.get("/system/status", response_model=SuccessResponse)
async def get_quest_system_status(
    db: AsyncSession = Depends(get_database)
):
    """Get overall quest system status and statistics."""
    try:
        quest_service = await get_quest_service(db)
        
        # Get basic counts
        all_quests = await quest_service.get_all_quests(is_active=True)
        categories = await quest_service.get_quest_categories(is_active=True)
        
        # Get completion stats (simplified)
        from sqlalchemy import select, func
        from app.models.quest import PlayerQuestProgress
        
        result = await db.execute(
            select(func.count().distinct(PlayerQuestProgress.player_wallet))
            .select_from(PlayerQuestProgress)
        )
        total_players = result.scalar() or 0
        
        return SuccessResponse(
            success=True,
            data=QuestSystemStatusResponse(
                total_active_quests=len(all_quests),
                total_categories=len(categories),
                total_players_with_quests=total_players,
                most_popular_quest=None,  # Would need more complex query
                completion_rates={},      # Would need more complex analysis
                average_completion_time={} # Would need more complex analysis
            )
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {str(e)}")


# Integration endpoints for automatic progress tracking
@router.post("/track/business-purchase", response_model=SuccessResponse)
async def track_business_purchase(
    player_wallet: str = Query(..., description="Player wallet address"),
    business_cost: int = Query(..., description="Business cost in lamports"),
    db: AsyncSession = Depends(get_database)
):
    """Track business purchase for quest progress."""
    try:
        quest_service = await get_quest_service(db)
        await quest_service.track_business_purchase(player_wallet, business_cost)
        
        await db.commit()
        
        return SuccessResponse(
            success=True,
            data={"message": "Business purchase tracked for quests"}
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to track business purchase: {str(e)}")


@router.post("/track/business-upgrade", response_model=SuccessResponse)
async def track_business_upgrade(
    player_wallet: str = Query(..., description="Player wallet address"),
    upgrade_cost: int = Query(..., description="Upgrade cost in lamports"),
    db: AsyncSession = Depends(get_database)
):
    """Track business upgrade for quest progress."""
    try:
        quest_service = await get_quest_service(db)
        await quest_service.track_business_upgrade(player_wallet, upgrade_cost)
        
        await db.commit()
        
        return SuccessResponse(
            success=True,
            data={"message": "Business upgrade tracked for quests"}
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to track business upgrade: {str(e)}")


@router.post("/track/referral", response_model=SuccessResponse)
async def track_referral_invite(
    referrer_wallet: str = Query(..., description="Referrer wallet address"),
    referee_wallet: str = Query(..., description="Referee wallet address"),
    db: AsyncSession = Depends(get_database)
):
    """Track referral invite for quest progress."""
    try:
        quest_service = await get_quest_service(db)
        await quest_service.track_referral_invite(referrer_wallet, referee_wallet)
        
        await db.commit()
        
        return SuccessResponse(
            success=True,
            data={"message": "Referral invite tracked for quests"}
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to track referral: {str(e)}")


@router.post("/track/earnings-claim", response_model=SuccessResponse)
async def track_earnings_claim(
    player_wallet: str = Query(..., description="Player wallet address"),
    claim_amount: int = Query(..., description="Claim amount in lamports"),
    db: AsyncSession = Depends(get_database)
):
    """Track earnings claim for quest progress."""
    try:
        quest_service = await get_quest_service(db)
        await quest_service.track_earnings_claim(player_wallet, claim_amount)
        
        await db.commit()
        
        return SuccessResponse(
            success=True,
            data={"message": "Earnings claim tracked for quests"}
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to track earnings claim: {str(e)}")


@router.post("/track/daily-login", response_model=SuccessResponse)
async def track_daily_login(
    player_wallet: str = Query(..., description="Player wallet address"),
    db: AsyncSession = Depends(get_database)
):
    """Track daily login for quest progress."""
    try:
        quest_service = await get_quest_service(db)
        await quest_service.track_daily_login(player_wallet)
        
        await db.commit()
        
        return SuccessResponse(
            success=True,
            data={"message": "Daily login tracked for quests"}
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to track daily login: {str(e)}")


@router.post("/initialize", response_model=SuccessResponse)
async def initialize_quest_system(
    db: AsyncSession = Depends(get_database)
):
    """Initialize the quest system with default quests."""
    try:
        quest_service = await get_quest_service(db)
        await quest_service.initialize_default_quests()
        await db.commit()
        
        return SuccessResponse(
            success=True,
            data={
                "message": "Quest system initialized successfully",
                "timestamp": datetime.utcnow()
            }
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to initialize quest system: {str(e)}")
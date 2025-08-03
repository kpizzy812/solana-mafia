"""
Player routes for the Solana Mafia API.
Handles player-related endpoints including profile, businesses, and statistics.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from datetime import datetime, timedelta

import structlog

from app.api.dependencies import (
    get_database,
    validate_wallet_param,
    get_player_by_wallet,
    get_pagination_params,
    get_sort_params,
    get_date_range_filter,
    get_active_only_filter
)
from app.api.schemas.players import (
    PlayerResponse,
    PlayerStatsResponse,
    PlayerBusinessesResponse,
    PlayerBusinessSummary,
    PlayerEarningsHistory,
    PlayerEarningsPeriod,
    PlayerLeaderboardResponse,
    PlayerLeaderboardEntry,
    PlayerActivityResponse,
    PlayerActivityLog
)
from app.api.schemas.common import (
    SuccessResponse,
    PaginatedResponse,
    PaginationParams,
    SortParams,
    create_success_response,
    create_paginated_response
)
from app.models.player import Player
from app.models.business import Business
from app.models.nft import BusinessNFT
from app.models.event import Event


logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "/{wallet}",
    response_model=SuccessResponse,
    summary="Get Player Profile",
    description="Retrieve player profile information by wallet address"
)
async def get_player_profile(
    player: Player = Depends(get_player_by_wallet),
    db: AsyncSession = Depends(get_database)
):
    """Get player profile by wallet address."""
    try:
        # Convert to response model
        player_response = PlayerResponse.model_validate(player)
        
        logger.info("Player profile retrieved", wallet=player.wallet)
        return create_success_response(
            data=player_response,
            message="Player profile retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error retrieving player profile", wallet=player.wallet, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "PROFILE_RETRIEVAL_ERROR",
                "message": "Failed to retrieve player profile"
            }
        )


@router.get(
    "/{wallet}/stats",
    response_model=SuccessResponse,
    summary="Get Player Statistics",
    description="Retrieve comprehensive player statistics and performance metrics"
)
async def get_player_stats(
    player: Player = Depends(get_player_by_wallet),
    db: AsyncSession = Depends(get_database)
):
    """Get detailed player statistics."""
    try:
        # Get business statistics
        business_stats = await db.execute(
            select(
                func.count(Business.business_id).label("total_businesses"),
                func.count(Business.business_id).filter(Business.is_active == True).label("active_businesses"),
                func.sum(Business.earnings_per_hour).label("total_hourly_earnings"),
                func.array_agg(Business.business_type.distinct()).label("business_types")
            ).where(Business.owner == player.wallet)
        )
        stats = business_stats.first()
        
        # Calculate days active
        days_active = (datetime.utcnow() - player.created_at).days
        
        # Get last activity from events
        last_activity_result = await db.execute(
            select(Event.block_time)
            .where(Event.event_data["wallet"].astext == player.wallet)
            .order_by(desc(Event.block_time))
            .limit(1)
        )
        last_activity = last_activity_result.scalar_one_or_none()
        
        # Calculate slot utilization
        slot_utilization = (stats.active_businesses or 0) / player.slots_unlocked if player.slots_unlocked > 0 else 0
        
        # Calculate total claimed (total_earnings - earnings_balance)
        total_claimed = player.total_earnings - player.earnings_balance
        
        player_stats = PlayerStatsResponse(
            wallet=player.wallet,
            total_businesses=stats.total_businesses or 0,
            active_businesses=stats.active_businesses or 0,
            total_earnings=player.total_earnings,
            earnings_balance=player.earnings_balance,
            total_claimed=total_claimed,
            business_types_owned=stats.business_types or [],
            slot_utilization=slot_utilization,
            days_active=days_active,
            last_activity=last_activity
        )
        
        logger.info("Player statistics retrieved", wallet=player.wallet)
        return create_success_response(
            data=player_stats,
            message="Player statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error retrieving player statistics", wallet=player.wallet, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "STATS_RETRIEVAL_ERROR",
                "message": "Failed to retrieve player statistics"
            }
        )


@router.get(
    "/{wallet}/businesses",
    response_model=SuccessResponse,
    summary="Get Player Businesses",
    description="Retrieve all businesses owned by the player"
)
async def get_player_businesses(
    player: Player = Depends(get_player_by_wallet),
    db: AsyncSession = Depends(get_database),
    active_only: bool = Depends(get_active_only_filter),
    pagination: PaginationParams = Depends(get_pagination_params),
    sort_params: SortParams = Depends(get_sort_params)
):
    """Get player's businesses with pagination and filtering."""
    try:
        # Build query
        query = select(Business, BusinessNFT.mint).join(
            BusinessNFT, Business.business_id == BusinessNFT.business_id, isouter=True
        ).where(Business.owner == player.wallet)
        
        if active_only:
            query = query.where(Business.is_active == True)
        
        # Apply sorting
        if sort_params.sort_by:
            sort_column = getattr(Business, sort_params.sort_by, None)
            if sort_column:
                if sort_params.sort_order == "desc":
                    query = query.order_by(desc(sort_column))
                else:
                    query = query.order_by(sort_column)
        else:
            query = query.order_by(desc(Business.created_at))
        
        # Get total count
        count_query = select(func.count()).select_from(
            query.subquery()
        )
        total_count = await db.execute(count_query)
        total = total_count.scalar()
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        # Execute query
        result = await db.execute(query)
        businesses_data = result.fetchall()
        
        # Build response
        businesses = []
        total_hourly_earnings = 0
        active_count = 0
        
        for business, nft_mint in businesses_data:
            business_summary = PlayerBusinessSummary(
                business_id=business.business_id,
                business_type=business.business_type,
                name=business.name,
                level=business.level,
                earnings_per_hour=business.earnings_per_hour,
                slot_index=business.slot_index,
                is_active=business.is_active,
                nft_mint=nft_mint or "N/A",
                created_at=business.created_at
            )
            businesses.append(business_summary)
            
            if business.is_active:
                total_hourly_earnings += business.earnings_per_hour
                active_count += 1
        
        businesses_response = PlayerBusinessesResponse(
            wallet=player.wallet,
            businesses=businesses,
            total_businesses=len(businesses),
            active_businesses=active_count,
            total_hourly_earnings=total_hourly_earnings
        )
        
        logger.info(
            "Player businesses retrieved",
            wallet=player.wallet,
            count=len(businesses),
            active_count=active_count
        )
        
        if pagination.limit < total:
            return create_paginated_response(
                data=businesses_response.businesses,
                total=total,
                limit=pagination.limit,
                offset=pagination.offset
            )
        else:
            return create_success_response(
                data=businesses_response,
                message="Player businesses retrieved successfully"
            )
        
    except Exception as e:
        logger.error("Error retrieving player businesses", wallet=player.wallet, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "BUSINESSES_RETRIEVAL_ERROR",
                "message": "Failed to retrieve player businesses"
            }
        )


@router.get(
    "/{wallet}/earnings",
    response_model=SuccessResponse,
    summary="Get Player Earnings History",
    description="Retrieve player's earnings history with optional date filtering"
)
async def get_player_earnings_history(
    player: Player = Depends(get_player_by_wallet),
    db: AsyncSession = Depends(get_database),
    period: str = Query("daily", regex="^(daily|weekly|monthly)$", description="Aggregation period"),
    date_range: dict = Depends(get_date_range_filter),
    pagination: PaginationParams = Depends(get_pagination_params)
):
    """Get player's earnings history with aggregation."""
    try:
        # Build date filter
        date_filters = []
        if date_range["start_date"]:
            start_date = datetime.strptime(date_range["start_date"], "%Y-%m-%d")
            date_filters.append(Event.block_time >= start_date)
        if date_range["end_date"]:
            end_date = datetime.strptime(date_range["end_date"], "%Y-%m-%d") + timedelta(days=1)
            date_filters.append(Event.block_time < end_date)
        
        # Query earnings events
        query = select(Event).where(
            and_(
                Event.event_type.in_(["EarningsUpdated", "EarningsClaimed"]),
                Event.event_data["wallet"].astext == player.wallet,
                *date_filters
            )
        ).order_by(desc(Event.block_time))
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        result = await db.execute(query)
        events = result.scalars().all()
        
        # Process events into periods
        earnings_data = []
        total_period_earnings = 0
        
        for event in events:
            earnings_amount = event.event_data.get("earnings_amount", 0)
            if event.event_type == "EarningsUpdated":
                total_period_earnings += earnings_amount
            
            period_entry = PlayerEarningsPeriod(
                date=event.block_time,
                earnings_amount=earnings_amount,
                cumulative_earnings=event.event_data.get("total_earnings", 0)
            )
            earnings_data.append(period_entry)
        
        # Calculate average daily earnings
        days_in_period = len(set(event.block_time.date() for event in events)) or 1
        average_daily_earnings = total_period_earnings // days_in_period
        
        history_response = PlayerEarningsHistory(
            wallet=player.wallet,
            period=period,
            earnings_data=earnings_data,
            total_period_earnings=total_period_earnings,
            average_daily_earnings=average_daily_earnings
        )
        
        logger.info(
            "Player earnings history retrieved",
            wallet=player.wallet,
            period=period,
            events_count=len(events)
        )
        
        return create_success_response(
            data=history_response,
            message="Earnings history retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error retrieving earnings history", wallet=player.wallet, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "EARNINGS_HISTORY_ERROR",
                "message": "Failed to retrieve earnings history"
            }
        )


@router.get(
    "/{wallet}/activity",
    response_model=SuccessResponse,
    summary="Get Player Activity Log",
    description="Retrieve player's activity log from blockchain events"
)
async def get_player_activity(
    player: Player = Depends(get_player_by_wallet),
    db: AsyncSession = Depends(get_database),
    pagination: PaginationParams = Depends(get_pagination_params)
):
    """Get player's activity log."""
    try:
        # Query all events related to the player
        query = select(Event).where(
            Event.event_data["wallet"].astext == player.wallet
        ).order_by(desc(Event.block_time))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_count = await db.execute(count_query)
        total = total_count.scalar()
        
        # Apply pagination
        query = query.offset(pagination.offset).limit(pagination.limit)
        
        result = await db.execute(query)
        events = result.scalars().all()
        
        # Convert events to activity log entries
        activities = []
        for event in events:
            activity = PlayerActivityLog(
                timestamp=event.block_time,
                activity_type=event.event_type,
                description=f"{event.event_type} event",
                transaction_signature=event.signature,
                metadata=event.event_data
            )
            activities.append(activity)
        
        activity_response = PlayerActivityResponse(
            wallet=player.wallet,
            activities=activities,
            total_activities=total
        )
        
        logger.info(
            "Player activity retrieved",
            wallet=player.wallet,
            activities_count=len(activities)
        )
        
        return create_paginated_response(
            data=activities,
            total=total,
            limit=pagination.limit,
            offset=pagination.offset
        )
        
    except Exception as e:
        logger.error("Error retrieving player activity", wallet=player.wallet, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ACTIVITY_RETRIEVAL_ERROR",
                "message": "Failed to retrieve player activity"
            }
        )
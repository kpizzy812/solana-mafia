"""
Leaderboard API routes for the Solana Mafia game.
Handles all leaderboard endpoints including earnings, referrals, and prestige rankings.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, case, text, Float
from sqlalchemy.orm import aliased

import structlog

from app.api.dependencies import (
    get_database,
    validate_wallet_param,
    get_pagination_params,
    get_player_by_wallet_optional
)
from app.api.schemas.common import PaginationParams, SuccessResponse, create_success_response
from app.api.schemas.leaderboards import (
    LeaderboardType, LeaderboardPeriod,
    EarningsLeaderboardEntry, ReferralLeaderboardEntry, PrestigeLeaderboardEntry,
    PlayerPosition, LeaderboardStats,
    EarningsLeaderboardResponse, ReferralLeaderboardResponse, PrestigeLeaderboardResponse,
    PlayerPositionResponse, LeaderboardStatsResponse,
    LeaderboardRequest
)
from app.models.player import Player
from app.models.referral import ReferralStats
from app.models.prestige import PlayerPrestigeStats
# Кеширование временно отключено для решения проблем с Redis в Docker
# from app.cache.cache_decorators import cached

router = APIRouter(tags=["Leaderboards"])
logger = structlog.get_logger(__name__)


@router.get(
    "/earnings",
    response_model=EarningsLeaderboardResponse,
    summary="Get Earnings Leaderboard",
    description="Retrieve top players by total earnings with detailed ROI metrics"
)
async def get_earnings_leaderboard(
    limit: int = Query(100, ge=1, le=1000, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    period: LeaderboardPeriod = Query(LeaderboardPeriod.ALL_TIME, description="Time period"),
    db: AsyncSession = Depends(get_database)
):
    """
    Получить лидерборд по заработанной прибыли.
    
    Включает:
    - Общий заработок
    - ROI (возврат инвестиций)
    - Количество активных бизнесов
    - Последние клеймы
    """
    try:
        logger.info("Getting earnings leaderboard", limit=limit, offset=offset, period=period)
        
        # Base query for earnings leaderboard with business count subquery
        from app.models.business import Business
        
        # Subquery to count active businesses
        business_count_subquery = select(
            Business.player_wallet,
            func.count(Business.id).label("active_businesses_count")
        ).where(
            Business.is_active == True
        ).group_by(Business.player_wallet).subquery()
        
        query = select(
            Player.wallet,
            Player.total_earned,
            Player.total_invested,
            func.coalesce(business_count_subquery.c.active_businesses_count, 0).label("active_businesses_count"),
            Player.prestige_level,
            Player.prestige_points,
            Player.last_earnings_update,
            Player.pending_earnings,
            # Calculate ROI percentage
            case(
                (Player.total_invested > 0,
                 (Player.total_earned.cast(Float) / Player.total_invested) * 100),
                else_=0
            ).label("roi_percentage"),
            # Row number for ranking
            func.row_number().over(
                order_by=desc(Player.total_earned)
            ).label("rank")
        ).select_from(
            Player.__table__.outerjoin(
                business_count_subquery,
                Player.wallet == business_count_subquery.c.player_wallet
            )
        ).where(
            and_(
                Player.is_active == True,
                Player.total_earned > 0  # Only players with earnings
            )
        )
        
        # Apply time period filter if needed
        if period != LeaderboardPeriod.ALL_TIME:
            days_back = {
                LeaderboardPeriod.DAILY: 1,
                LeaderboardPeriod.WEEKLY: 7,
                LeaderboardPeriod.MONTHLY: 30
            }.get(period, 365)
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            query = query.where(Player.last_earnings_update >= cutoff_date)
        
        # Apply pagination
        paginated_query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(paginated_query)
        rows = result.all()
        
        # Build leaderboard entries
        leaderboard = []
        for row in rows:
            entry = EarningsLeaderboardEntry(
                rank=row.rank,
                wallet=row.wallet,
                prestige_level=row.prestige_level or "wannabe",
                prestige_points=row.prestige_points or 0,
                total_earned=row.total_earned,
                total_invested=row.total_invested,
                roi_percentage=float(row.roi_percentage or 0),
                active_businesses=row.active_businesses_count or 0,
                last_claim_amount=row.pending_earnings,
                last_claim_at=row.last_earnings_update
            )
            leaderboard.append(entry.model_dump())
        
        # Get total count
        count_query = select(func.count()).select_from(
            select(Player.wallet).where(
                and_(
                    Player.is_active == True,
                    Player.total_earned > 0
                )
            ).subquery()
        )
        total_result = await db.execute(count_query)
        total_entries = total_result.scalar() or 0
        
        # Get leaderboard stats
        stats_query = select(
            func.count(Player.wallet).label("total_players"),
            func.sum(Player.total_earned).label("total_earnings"),
            func.avg(Player.total_earned).label("avg_earnings"),
            func.max(Player.total_earned).label("max_earnings")
        ).where(
            and_(
                Player.is_active == True,
                Player.total_earned > 0
            )
        )
        stats_result = await db.execute(stats_query)
        stats_row = stats_result.first()
        
        # Get top earner info
        top_earner_query = select(
            Player.wallet,
            Player.total_earned
        ).where(
            and_(
                Player.is_active == True,
                Player.total_earned > 0
            )
        ).order_by(desc(Player.total_earned)).limit(1)
        
        top_earner_result = await db.execute(top_earner_query)
        top_earner = top_earner_result.first()
        
        stats = {
            "total_players": stats_row.total_players or 0,
            "total_earnings": stats_row.total_earnings or 0,
            "average_earnings": float(stats_row.avg_earnings or 0),
            "max_earnings": stats_row.max_earnings or 0,
            "top_earner_wallet": top_earner.wallet if top_earner else None,
            "top_earner_amount": top_earner.total_earned if top_earner else None
        }
        
        response_data = {
            "leaderboard": leaderboard,
            "period": period.value,
            "total_entries": total_entries,
            "stats": stats,
            "last_updated": datetime.utcnow().isoformat(),
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_entries,
                "has_next": offset + limit < total_entries,
                "has_previous": offset > 0
            }
        }
        
        logger.info("Earnings leaderboard retrieved", 
                   entries=len(leaderboard), 
                   total=total_entries,
                   period=period)
        
        return create_success_response(
            data=response_data,
            message="Earnings leaderboard retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error retrieving earnings leaderboard", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve earnings leaderboard"
        )


@router.get(
    "/referrals", 
    response_model=ReferralLeaderboardResponse,
    summary="Get Referrals Leaderboard",
    description="Retrieve top players by referral count and earnings"
)
async def get_referrals_leaderboard(
    limit: int = Query(100, ge=1, le=1000, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    period: LeaderboardPeriod = Query(LeaderboardPeriod.ALL_TIME, description="Time period"),
    db: AsyncSession = Depends(get_database)
):
    """
    Получить лидерборд по количеству рефералов.
    
    Включает:
    - Общее количество рефералов
    - Разбивку по уровням (1, 2, 3)
    - Заработок с рефералов
    """
    try:
        logger.info("Getting referrals leaderboard", limit=limit, offset=offset, period=period)
        
        # Query referral stats with player info
        query = select(
            ReferralStats.user_id.label("wallet"),
            ReferralStats.total_referrals,
            ReferralStats.total_referral_earnings,
            ReferralStats.level_1_referrals,
            ReferralStats.level_2_referrals,
            ReferralStats.level_3_referrals,
            ReferralStats.level_1_earnings,
            ReferralStats.level_2_earnings,
            ReferralStats.level_3_earnings,
            Player.prestige_level,
            Player.prestige_points,
            # Row number for ranking
            func.row_number().over(
                order_by=desc(ReferralStats.total_referrals)
            ).label("rank")
        ).select_from(
            ReferralStats.__table__.join(
                Player.__table__, 
                ReferralStats.user_id == Player.wallet
            )
        ).where(
            and_(
                ReferralStats.total_referrals > 0,
                Player.is_active == True
            )
        )
        
        # Apply time period filter if needed
        if period != LeaderboardPeriod.ALL_TIME:
            days_back = {
                LeaderboardPeriod.DAILY: 1,
                LeaderboardPeriod.WEEKLY: 7,
                LeaderboardPeriod.MONTHLY: 30
            }.get(period, 365)
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            query = query.where(ReferralStats.last_updated_at >= cutoff_date)
        
        # Apply pagination
        paginated_query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(paginated_query)
        rows = result.all()
        
        # Build leaderboard entries
        leaderboard = []
        for row in rows:
            entry = ReferralLeaderboardEntry(
                rank=row.rank,
                wallet=row.wallet,
                prestige_level=row.prestige_level or "wannabe",
                prestige_points=row.prestige_points or 0,
                total_referrals=row.total_referrals,
                total_referral_earnings=row.total_referral_earnings,
                level_1_referrals=row.level_1_referrals,
                level_2_referrals=row.level_2_referrals,
                level_3_referrals=row.level_3_referrals,
                level_1_earnings=row.level_1_earnings,
                level_2_earnings=row.level_2_earnings,
                level_3_earnings=row.level_3_earnings
            )
            leaderboard.append(entry.model_dump())
        
        # Get total count
        count_query = select(func.count()).select_from(
            ReferralStats.__table__.join(
                Player.__table__, 
                ReferralStats.user_id == Player.wallet
            )
        ).where(
            and_(
                ReferralStats.total_referrals > 0,
                Player.is_active == True
            )
        )
        total_result = await db.execute(count_query)
        total_entries = total_result.scalar() or 0
        
        # Get referral stats
        stats_query = select(
            func.count(ReferralStats.user_id).label("total_players"),
            func.sum(ReferralStats.total_referrals).label("total_referrals"),
            func.sum(ReferralStats.total_referral_earnings).label("total_earnings"),
            func.max(ReferralStats.total_referrals).label("max_referrals")
        ).select_from(
            ReferralStats.__table__.join(
                Player.__table__, 
                ReferralStats.user_id == Player.wallet
            )
        ).where(
            and_(
                ReferralStats.total_referrals > 0,
                Player.is_active == True
            )
        )
        
        stats_result = await db.execute(stats_query)
        stats_row = stats_result.first()
        
        # Get top referrer info
        top_referrer_query = select(
            ReferralStats.user_id,
            ReferralStats.total_referrals
        ).select_from(
            ReferralStats.__table__.join(
                Player.__table__, 
                ReferralStats.user_id == Player.wallet
            )
        ).where(
            and_(
                ReferralStats.total_referrals > 0,
                Player.is_active == True
            )
        ).order_by(desc(ReferralStats.total_referrals)).limit(1)
        
        top_referrer_result = await db.execute(top_referrer_query)
        top_referrer = top_referrer_result.first()
        
        stats = {
            "total_players": stats_row.total_players or 0,
            "total_referrals": stats_row.total_referrals or 0,
            "total_referral_earnings": stats_row.total_earnings or 0,
            "max_referrals": stats_row.max_referrals or 0,
            "top_referrer_wallet": top_referrer.user_id if top_referrer else None,
            "top_referrer_count": top_referrer.total_referrals if top_referrer else None
        }
        
        response_data = {
            "leaderboard": leaderboard,
            "period": period.value,
            "total_entries": total_entries,
            "stats": stats,
            "last_updated": datetime.utcnow().isoformat(),
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_entries,
                "has_next": offset + limit < total_entries,
                "has_previous": offset > 0
            }
        }
        
        logger.info("Referrals leaderboard retrieved", 
                   entries=len(leaderboard), 
                   total=total_entries,
                   period=period)
        
        return create_success_response(
            data=response_data,
            message="Referrals leaderboard retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error retrieving referrals leaderboard", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve referrals leaderboard"
        )


@router.get(
    "/prestige",
    response_model=PrestigeLeaderboardResponse,
    summary="Get Prestige Leaderboard", 
    description="Retrieve top players by prestige points and level"
)
async def get_prestige_leaderboard(
    limit: int = Query(100, ge=1, le=1000, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    period: LeaderboardPeriod = Query(LeaderboardPeriod.ALL_TIME, description="Time period"),
    db: AsyncSession = Depends(get_database)
):
    """
    Получить лидерборд по престижу.
    
    Включает:
    - Текущие очки престижа
    - Уровень престижа
    - Прогресс до следующего уровня
    """
    try:
        logger.info("Getting prestige leaderboard", limit=limit, offset=offset, period=period)
        
        # Use Player table as primary source (PlayerPrestigeStats may be outdated)
        logger.info("Using Player table for prestige data")
        query = select(
            Player.wallet,
            Player.prestige_points.label("current_points"),
            Player.prestige_level.label("current_level"),
            Player.total_prestige_earned.label("total_points_earned"),
            Player.prestige_level_up_count.label("level_up_count"),
            # Calculate points to next level and progress - simplified
            case(
                (Player.prestige_level == "wannabe", 50 - Player.prestige_points),
                (Player.prestige_level == "associate", 200 - Player.prestige_points),
                (Player.prestige_level == "soldier", 800 - Player.prestige_points),
                (Player.prestige_level == "capo", 3000 - Player.prestige_points),
                (Player.prestige_level == "underboss", 10000 - Player.prestige_points),
                else_=0
            ).label("points_to_next_level"),
            case(
                (Player.prestige_level == "wannabe", 
                 Player.prestige_points.cast(Float) / 50 * 100),
                (Player.prestige_level == "associate", 
                 (Player.prestige_points - 50).cast(Float) / 150 * 100),
                (Player.prestige_level == "soldier", 
                 (Player.prestige_points - 200).cast(Float) / 600 * 100),
                (Player.prestige_level == "capo", 
                 (Player.prestige_points - 800).cast(Float) / 2200 * 100),
                (Player.prestige_level == "underboss", 
                 (Player.prestige_points - 3000).cast(Float) / 7000 * 100),
                else_=100.0
            ).label("progress_percentage"),
            # Row number for ranking
            func.row_number().over(
                order_by=desc(Player.prestige_points)
            ).label("rank")
        ).where(
            and_(
                Player.is_active == True,
                Player.prestige_points > 0
            )
        )
        
        # Apply time period filter if needed
        if period != LeaderboardPeriod.ALL_TIME:
            days_back = {
                LeaderboardPeriod.DAILY: 1,
                LeaderboardPeriod.WEEKLY: 7,
                LeaderboardPeriod.MONTHLY: 30
            }.get(period, 365)
            
            cutoff_date = datetime.utcnow() - timedelta(days=days_back)
            query = query.where(Player.updated_at >= cutoff_date)
        
        # Apply pagination
        paginated_query = query.offset(offset).limit(limit)
        
        # Execute query
        result = await db.execute(paginated_query)
        rows = result.all()
        
        # Build leaderboard entries
        leaderboard = []
        for row in rows:
            entry = PrestigeLeaderboardEntry(
                rank=row.rank,
                wallet=row.wallet,
                prestige_level=row.current_level or "wannabe",
                prestige_points=row.current_points or 0,
                current_points=row.current_points or 0,
                total_points_earned=row.total_points_earned or 0,
                current_level=row.current_level or "wannabe",
                level_up_count=row.level_up_count or 0,
                points_to_next_level=max(0, row.points_to_next_level or 0),
                progress_percentage=min(100.0, max(0.0, float(row.progress_percentage or 0))),
                achievements_unlocked=0  # TODO: Implement achievements system
            )
            leaderboard.append(entry.model_dump())
        
        # Get total count - use simpler query for count
        count_query = select(func.count()).select_from(
            select(Player.wallet).where(
                and_(
                    Player.is_active == True,
                    Player.prestige_points > 0
                )
            ).subquery()
        )
        total_result = await db.execute(count_query)
        total_entries = total_result.scalar() or 0
        
        # Get prestige stats from Player table
        stats_query = select(
            func.count(Player.wallet).label("total_players"),
            func.avg(Player.prestige_points).label("avg_points"),
            func.max(Player.prestige_points).label("max_points"),
            func.count().filter(Player.prestige_level == "boss").label("boss_count")
        ).where(
            and_(
                Player.is_active == True,
                Player.prestige_points > 0
            )
        )
        
        stats_result = await db.execute(stats_query)
        stats_row = stats_result.first()
        
        # Get top prestige player info
        top_prestige_query = select(
            Player.wallet,
            Player.prestige_points
        ).where(
            and_(
                Player.is_active == True,
                Player.prestige_points > 0
            )
        ).order_by(desc(Player.prestige_points)).limit(1)
        
        top_prestige_result = await db.execute(top_prestige_query)
        top_prestige = top_prestige_result.first()
        
        stats = {
            "total_players": stats_row.total_players or 0,
            "average_prestige_points": float(stats_row.avg_points or 0),
            "max_prestige_points": stats_row.max_points or 0,
            "boss_level_players": stats_row.boss_count or 0,
            "top_prestige_wallet": top_prestige.wallet if top_prestige else None,
            "top_prestige_points": top_prestige.prestige_points if top_prestige else None
        }
        
        response_data = {
            "leaderboard": leaderboard,
            "period": period.value,
            "total_entries": total_entries,
            "stats": stats,
            "last_updated": datetime.utcnow().isoformat(),
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_entries,
                "has_next": offset + limit < total_entries,
                "has_previous": offset > 0
            }
        }
        
        logger.info("Prestige leaderboard retrieved", 
                   entries=len(leaderboard), 
                   total=total_entries,
                   period=period)
        
        return create_success_response(
            data=response_data,
            message="Prestige leaderboard retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error retrieving prestige leaderboard", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve prestige leaderboard"
        )


@router.get(
    "/{wallet}/position",
    response_model=PlayerPositionResponse,
    summary="Get Player Position", 
    description="Get player's rank across all leaderboards"
)
async def get_player_position(
    wallet: str = Depends(validate_wallet_param),
    db: AsyncSession = Depends(get_database)
):
    """
    Получить позицию игрока во всех лидербордах.
    
    Возвращает ранг и процентили игрока в каждом лидерборде.
    """
    try:
        logger.info("Getting player position", wallet=wallet)
        
        # Get earnings rank
        earnings_rank_query = text("""
            SELECT rank FROM (
                SELECT wallet, 
                       ROW_NUMBER() OVER (ORDER BY total_earned DESC) as rank
                FROM players 
                WHERE is_active = true AND total_earned > 0
            ) ranked WHERE wallet = :wallet
        """)
        
        earnings_result = await db.execute(earnings_rank_query, {"wallet": wallet})
        earnings_rank = earnings_result.scalar()
        
        # Get total players in earnings leaderboard
        earnings_total_query = select(func.count()).select_from(Player).where(
            and_(Player.is_active == True, Player.total_earned > 0)
        )
        earnings_total_result = await db.execute(earnings_total_query)
        total_players_earnings = earnings_total_result.scalar() or 0
        
        # Get referrals rank
        referrals_rank_query = text("""
            SELECT rank FROM (
                SELECT rs.user_id as wallet,
                       ROW_NUMBER() OVER (ORDER BY rs.total_referrals DESC) as rank
                FROM referral_stats rs
                JOIN players p ON rs.user_id = p.wallet
                WHERE p.is_active = true AND rs.total_referrals > 0
            ) ranked WHERE wallet = :wallet
        """)
        
        referrals_result = await db.execute(referrals_rank_query, {"wallet": wallet})
        referrals_rank = referrals_result.scalar()
        
        # Get total players in referrals leaderboard
        referrals_total_query = select(func.count()).select_from(
            ReferralStats.__table__.join(
                Player.__table__,
                ReferralStats.user_id == Player.wallet
            )
        ).where(
            and_(
                Player.is_active == True,
                ReferralStats.total_referrals > 0
            )
        )
        referrals_total_result = await db.execute(referrals_total_query)
        total_players_referrals = referrals_total_result.scalar() or 0
        
        # Get prestige rank
        prestige_rank_query = text("""
            SELECT rank FROM (
                SELECT wallet,
                       ROW_NUMBER() OVER (ORDER BY prestige_points DESC) as rank
                FROM players 
                WHERE is_active = true AND prestige_points > 0
            ) ranked WHERE wallet = :wallet
        """)
        
        prestige_result = await db.execute(prestige_rank_query, {"wallet": wallet})
        prestige_rank = prestige_result.scalar()
        
        # Get total players in prestige leaderboard
        prestige_total_query = select(func.count()).select_from(Player).where(
            and_(Player.is_active == True, Player.prestige_points > 0)
        )
        prestige_total_result = await db.execute(prestige_total_query)
        total_players_prestige = prestige_total_result.scalar() or 0
        
        # Calculate percentiles
        earnings_percentile = None
        if earnings_rank and total_players_earnings > 0:
            earnings_percentile = ((total_players_earnings - earnings_rank + 1) / total_players_earnings) * 100
            
        referrals_percentile = None
        if referrals_rank and total_players_referrals > 0:
            referrals_percentile = ((total_players_referrals - referrals_rank + 1) / total_players_referrals) * 100
            
        prestige_percentile = None
        if prestige_rank and total_players_prestige > 0:
            prestige_percentile = ((total_players_prestige - prestige_rank + 1) / total_players_prestige) * 100
        
        position = PlayerPosition(
            wallet=wallet,
            earnings_rank=earnings_rank,
            referrals_rank=referrals_rank,
            prestige_rank=prestige_rank,
            combined_rank=None,  # TODO: Implement combined ranking
            total_players_earnings=total_players_earnings,
            total_players_referrals=total_players_referrals,
            total_players_prestige=total_players_prestige,
            earnings_percentile=earnings_percentile,
            referrals_percentile=referrals_percentile,
            prestige_percentile=prestige_percentile
        )
        
        logger.info("Player position retrieved", 
                   wallet=wallet,
                   earnings_rank=earnings_rank,
                   referrals_rank=referrals_rank,
                   prestige_rank=prestige_rank)
        
        return create_success_response(
            data=position,
            message="Player position retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error retrieving player position", wallet=wallet, error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve player position"
        )


@router.get(
    "/stats",
    response_model=LeaderboardStatsResponse,
    summary="Get Leaderboard Statistics",
    description="Get overall statistics across all leaderboards"
)
async def get_leaderboard_stats(
    db: AsyncSession = Depends(get_database)
):
    """
    Получить общую статистику по всем лидербордам.
    """
    try:
        logger.info("Getting leaderboard statistics")
        
        # Get player stats
        player_stats_query = select(
            func.count(Player.wallet).label("total_players"),
            func.sum(Player.total_earned).label("total_earnings"),
            func.avg(Player.prestige_points).label("avg_prestige")
        ).where(Player.is_active == True)
        
        player_stats_result = await db.execute(player_stats_query)
        player_stats = player_stats_result.first()
        
        # Get referral stats
        referral_stats_query = select(
            func.sum(ReferralStats.total_referrals).label("total_referrals")
        )
        
        referral_stats_result = await db.execute(referral_stats_query)
        referral_stats = referral_stats_result.first()
        
        # Get top performers
        top_earner_query = select(
            Player.wallet,
            Player.total_earned
        ).where(
            and_(Player.is_active == True, Player.total_earned > 0)
        ).order_by(desc(Player.total_earned)).limit(1)
        
        top_earner_result = await db.execute(top_earner_query)
        top_earner = top_earner_result.first()
        
        # Get top referrer
        top_referrer_query = select(
            ReferralStats.user_id,
            ReferralStats.total_referrals
        ).order_by(desc(ReferralStats.total_referrals)).limit(1)
        
        top_referrer_result = await db.execute(top_referrer_query)
        top_referrer = top_referrer_result.first()
        
        # Get top prestige player
        top_prestige_query = select(
            Player.wallet,
            Player.prestige_points
        ).where(
            and_(Player.is_active == True, Player.prestige_points > 0)
        ).order_by(desc(Player.prestige_points)).limit(1)
        
        top_prestige_result = await db.execute(top_prestige_query)
        top_prestige = top_prestige_result.first()
        
        stats = LeaderboardStats(
            total_players=player_stats.total_players or 0,
            total_earnings=player_stats.total_earnings or 0,
            total_referrals=referral_stats.total_referrals or 0,
            average_prestige_points=float(player_stats.avg_prestige or 0),
            top_earner_wallet=top_earner.wallet if top_earner else None,
            top_earner_amount=top_earner.total_earned if top_earner else None,
            top_referrer_wallet=top_referrer.user_id if top_referrer else None,
            top_referrer_count=top_referrer.total_referrals if top_referrer else None,
            top_prestige_wallet=top_prestige.wallet if top_prestige else None,
            top_prestige_points=top_prestige.prestige_points if top_prestige else None
        )
        
        logger.info("Leaderboard statistics retrieved")
        
        return create_success_response(
            data=stats,
            message="Leaderboard statistics retrieved successfully"
        )
        
    except Exception as e:
        logger.error("Error retrieving leaderboard statistics", error=str(e))
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve leaderboard statistics"
        )
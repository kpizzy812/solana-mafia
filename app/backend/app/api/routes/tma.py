"""
Telegram Mini Apps API routes.
Handles TMA-specific authentication, user management, and referral system.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.core.database import get_async_session
from app.api.dependencies import (
    get_database, get_tma_auth, get_required_auth, get_user_identifier,
    get_pagination_params, get_sort_params
)
from app.api.schemas.common import PaginationParams, SortParams, BaseResponse
from app.api.schemas.tma import (
    TMAAuthResponse, TMAPlayerCreateRequest, TMAPlayerResponse,
    TMALinkWalletRequest, TMAGameStatsResponse, TMAReferralInfoResponse,
    TMALeaderboardResponse, TMAUserInfo
)
from app.auth.tma_auth import AuthType
from app.models.user import User, UserType
from app.services.referral_service import ReferralService
from app.auth.tma_auth import TMAInitData

router = APIRouter(prefix="/tma", tags=["Telegram Mini Apps"])
logger = structlog.get_logger(__name__)


@router.post("/auth", response_model=TMAAuthResponse)
async def authenticate_tma(
    auth_data: Dict[str, Any] = Depends(get_tma_auth),
    db: AsyncSession = Depends(get_database)
):
    """
    Authenticate via Telegram Mini Apps.
    Validates init data and returns user information.
    """
    tma_data = auth_data['tma_data']
    
    # Create TMA user info
    user_info = TMAUserInfo(
        id=tma_data['telegram_user_id'],
        first_name=tma_data['first_name'],
        last_name=tma_data.get('last_name'),
        username=tma_data.get('username'),
        is_premium=tma_data.get('is_premium')
    )
    
    # Get or create user
    referral_service = ReferralService(db)
    user_id = f"tg_{tma_data['telegram_user_id']}"
    
    user = await referral_service.get_or_create_user(
        user_id=user_id,
        user_type=UserType.TELEGRAM,
        telegram_user_id=tma_data['telegram_user_id'],
        first_name=tma_data['first_name'],
        last_name=tma_data.get('last_name'),
        username=tma_data.get('username'),
        language_code=tma_data.get('language_code'),
        is_premium=tma_data.get('is_premium')
    )
    
    # Update activity
    user.record_login()
    await db.commit()
    
    logger.info(
        "TMA authentication successful",
        user_id=user_id,
        telegram_user_id=tma_data['telegram_user_id'],
        username=tma_data.get('username')
    )
    
    return TMAAuthResponse(
        success=True,
        message="Authentication successful",
        data={
            "user_id": user.id,
            "referral_code": user.referral_code,
            "is_new_user": user.login_count == 1
        },
        user_info=user_info,
        auth_date=datetime.fromtimestamp(tma_data['init_data'].auth_date),
        start_param=tma_data.get('start_param')
    )


@router.post("/player/create", response_model=TMAPlayerResponse)
async def create_tma_player(
    request: TMAPlayerCreateRequest,
    auth_data: Dict[str, Any] = Depends(get_tma_auth),
    db: AsyncSession = Depends(get_database)
):
    """
    Create a new player via TMA with optional referral.
    """
    tma_data = auth_data['tma_data']
    user_id = f"tg_{tma_data['telegram_user_id']}"
    
    referral_service = ReferralService(db)
    
    # Get or create user
    user = await referral_service.get_or_create_user(
        user_id=user_id,
        user_type=UserType.TELEGRAM,
        telegram_user_id=tma_data['telegram_user_id'],
        first_name=tma_data['first_name'],
        last_name=tma_data.get('last_name'),
        username=tma_data.get('username'),
        language_code=tma_data.get('language_code'),
        is_premium=tma_data.get('is_premium')
    )
    
    # Process referral if provided
    if request.referrer_code and not user.referrer_id:
        await referral_service.process_referral(
            referral_code=request.referrer_code,
            referee_id=user_id,
            referee_type=UserType.TELEGRAM,
            telegram_user_id=tma_data['telegram_user_id'],
            first_name=tma_data['first_name'],
            last_name=tma_data.get('last_name'),
            username=tma_data.get('username'),
            language_code=tma_data.get('language_code'),
            is_premium=tma_data.get('is_premium')
        )
    
    # Get referral stats
    referral_stats = await referral_service.get_user_referral_stats(user_id)
    
    await db.commit()
    
    return TMAPlayerResponse(
        success=True,
        message="Player created successfully",
        player_id=user.id,
        telegram_user_id=user.telegram_user_id,
        username=user.telegram_username,
        first_name=user.first_name or "Unknown",
        last_name=user.last_name,
        wallet_address=user.wallet_address,
        total_businesses=0,  # TODO: Count from actual businesses
        total_earnings=user.total_earned,
        pending_earnings=user.pending_earnings,
        pending_referral_earnings=user.pending_referral_earnings,
        referrer_id=user.referrer_id,
        referral_count=referral_stats.total_referrals if referral_stats else 0,
        total_referral_earnings=referral_stats.total_referral_earnings if referral_stats else 0,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at or user.created_at
    )


@router.get("/player/me", response_model=TMAPlayerResponse)
async def get_my_tma_player(
    auth_data: Dict[str, Any] = Depends(get_tma_auth),
    db: AsyncSession = Depends(get_database)
):
    """
    Get current TMA player information.
    """
    tma_data = auth_data['tma_data']
    user_id = f"tg_{tma_data['telegram_user_id']}"
    
    referral_service = ReferralService(db)
    
    # Get user
    user = await referral_service._get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player not found"
        )
    
    # Get referral stats
    referral_stats = await referral_service.get_user_referral_stats(user_id)
    
    # Update activity
    user.update_activity()
    await db.commit()
    
    return TMAPlayerResponse(
        success=True,
        message="Player data retrieved",
        player_id=user.id,
        telegram_user_id=user.telegram_user_id,
        username=user.telegram_username,
        first_name=user.first_name or "Unknown",
        last_name=user.last_name,
        wallet_address=user.wallet_address,
        total_businesses=0,  # TODO: Count from actual businesses
        total_earnings=user.total_earned,
        pending_earnings=user.pending_earnings,
        pending_referral_earnings=user.pending_referral_earnings,
        referrer_id=user.referrer_id,
        referral_count=referral_stats.total_referrals if referral_stats else 0,
        total_referral_earnings=referral_stats.total_referral_earnings if referral_stats else 0,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at or user.created_at
    )


@router.post("/wallet/link", response_model=BaseResponse)
async def link_wallet_to_tma(
    request: TMALinkWalletRequest,
    auth_data: Dict[str, Any] = Depends(get_tma_auth),
    db: AsyncSession = Depends(get_database)
):
    """
    Link a Solana wallet to TMA account with signature verification.
    """
    from app.utils.wallet_verification import verify_linking_signature
    
    tma_data = auth_data['tma_data']
    user_id = f"tg_{tma_data['telegram_user_id']}"
    telegram_user_id = tma_data['telegram_user_id']
    
    referral_service = ReferralService(db)
    user = await referral_service._get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Verify wallet signature
    verification_result = verify_linking_signature(
        wallet_address=request.wallet_address,
        signature=request.signature,
        message=request.message,
        telegram_user_id=telegram_user_id
    )
    
    if not verification_result["valid"]:
        logger.warning(
            "Wallet linking signature verification failed",
            user_id=user_id,
            wallet_address=request.wallet_address,
            error=verification_result.get("error")
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Signature verification failed: {verification_result.get('error', 'Invalid signature')}"
        )
    
    # Check if wallet is already linked to another account
    existing_user = await referral_service._get_user_by_wallet(request.wallet_address)
    if existing_user and existing_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet is already linked to another account"
        )
    
    # Link the wallet
    user.link_wallet(request.wallet_address)
    
    await db.commit()
    
    logger.info(
        "Wallet linked to TMA account successfully",
        user_id=user_id,
        wallet_address=request.wallet_address,
        telegram_user_id=telegram_user_id
    )
    
    return BaseResponse(
        success=True,
        message="Wallet linked successfully"
    )


@router.get("/referrals/info", response_model=TMAReferralInfoResponse)
async def get_referral_info(
    auth_data: Dict[str, Any] = Depends(get_tma_auth),
    db: AsyncSession = Depends(get_database)
):
    """
    Get referral information for current user.
    """
    tma_data = auth_data['tma_data']
    user_id = f"tg_{tma_data['telegram_user_id']}"
    
    referral_service = ReferralService(db)
    
    # Get user
    user = await referral_service._get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get referral stats
    referral_stats = await referral_service.get_user_referral_stats(user_id)
    
    # Get referrals
    referrals = await referral_service.get_user_referrals(user_id, limit=100)
    
    return TMAReferralInfoResponse(
        success=True,
        message="Referral information retrieved",
        referral_code=user.referral_code or "N/A",
        referrals=referrals,
        referral_earnings={
            "level_1": referral_stats.level_1_earnings if referral_stats else 0,
            "level_2": referral_stats.level_2_earnings if referral_stats else 0,
            "level_3": referral_stats.level_3_earnings if referral_stats else 0
        },
        total_referral_earnings=referral_stats.total_referral_earnings if referral_stats else 0,
        level_1_count=referral_stats.level_1_referrals if referral_stats else 0,
        level_2_count=referral_stats.level_2_referrals if referral_stats else 0,
        level_3_count=referral_stats.level_3_referrals if referral_stats else 0
    )


@router.get("/referrals/leaderboard", response_model=TMALeaderboardResponse)
async def get_referral_leaderboard(
    period: str = Query("all", regex="^(daily|weekly|monthly|all)$"),
    pagination: PaginationParams = Depends(get_pagination_params),
    auth_data: Dict[str, Any] = Depends(get_tma_auth),
    db: AsyncSession = Depends(get_database)
):
    """
    Get referral leaderboard.
    """
    tma_data = auth_data['tma_data']
    user_id = f"tg_{tma_data['telegram_user_id']}"
    
    referral_service = ReferralService(db)
    
    # Get leaderboard
    leaderboard = await referral_service.get_referral_leaderboard(
        period=period,
        limit=pagination.limit
    )
    
    # Find current user's rank
    player_rank = None
    for i, entry in enumerate(leaderboard, 1):
        if entry["user_id"] == user_id:
            player_rank = i
            break
    
    return TMALeaderboardResponse(
        success=True,
        message="Leaderboard retrieved",
        leaderboard=leaderboard[pagination.offset:pagination.offset + pagination.limit],
        player_rank=player_rank,
        total_players=len(leaderboard)
    )


@router.get("/stats", response_model=TMAGameStatsResponse)
async def get_tma_game_stats(
    auth_data: Dict[str, Any] = Depends(get_tma_auth),
    db: AsyncSession = Depends(get_database)
):
    """
    Get TMA-specific game statistics.
    """
    from sqlalchemy import func, and_
    from datetime import datetime, timedelta
    from app.models.user import User, UserType
    from app.models.referral import ReferralRelation, ReferralStats, ReferralCommission
    
    try:
        # Calculate date ranges
        now = datetime.utcnow()
        day_ago = now - timedelta(days=1)
        week_ago = now - timedelta(weeks=1)
        month_ago = now - timedelta(days=30)
        
        # Count telegram players
        telegram_players_result = await db.execute(
            select(func.count(User.id)).where(User.user_type == UserType.TELEGRAM)
        )
        telegram_players = telegram_players_result.scalar() or 0
        
        # Count wallet players
        wallet_players_result = await db.execute(
            select(func.count(User.id)).where(User.user_type == UserType.WALLET)
        )
        wallet_players = wallet_players_result.scalar() or 0
        
        # Count linked accounts (Telegram users with wallets)
        linked_accounts_result = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.user_type == UserType.TELEGRAM,
                    User.is_linked == True,
                    User.wallet_address.isnot(None)
                )
            )
        )
        linked_accounts = linked_accounts_result.scalar() or 0
        
        # Count total referrals
        total_referrals_result = await db.execute(
            select(func.count(ReferralRelation.id))
        )
        total_referrals = total_referrals_result.scalar() or 0
        
        # Count active referral chains (users with at least one referral)
        active_chains_result = await db.execute(
            select(func.count(func.distinct(ReferralRelation.referrer_id)))
        )
        active_referral_chains = active_chains_result.scalar() or 0
        
        # Calculate total referral earnings distributed
        total_earnings_result = await db.execute(
            select(func.sum(ReferralCommission.commission_amount)).where(
                ReferralCommission.status == "paid"
            )
        )
        referral_earnings_distributed = total_earnings_result.scalar() or 0
        
        # Calculate active users (based on last activity)
        daily_active_result = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.user_type == UserType.TELEGRAM,
                    User.last_activity_at >= day_ago
                )
            )
        )
        daily_active_tma_users = daily_active_result.scalar() or 0
        
        weekly_active_result = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.user_type == UserType.TELEGRAM,
                    User.last_activity_at >= week_ago
                )
            )
        )
        weekly_active_tma_users = weekly_active_result.scalar() or 0
        
        monthly_active_result = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.user_type == UserType.TELEGRAM,
                    User.last_activity_at >= month_ago
                )
            )
        )
        monthly_active_tma_users = monthly_active_result.scalar() or 0
        
        return TMAGameStatsResponse(
            success=True,
            message="Game statistics retrieved",
            telegram_players=telegram_players,
            wallet_players=wallet_players,
            linked_accounts=linked_accounts,
            total_referrals=total_referrals,
            active_referral_chains=active_referral_chains,
            referral_earnings_distributed=referral_earnings_distributed,
            daily_active_tma_users=daily_active_tma_users,
            weekly_active_tma_users=weekly_active_tma_users,
            monthly_active_tma_users=monthly_active_tma_users
        )
        
    except Exception as e:
        logger.error("Failed to get TMA game stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve game statistics"
        )
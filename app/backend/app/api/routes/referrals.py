"""
Referral system API routes.
Handles referral codes, multi-level referrals, commissions, and statistics.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

import structlog

from app.core.database import get_async_session
from app.api.dependencies import (
    get_database, get_required_auth, get_user_identifier,
    get_pagination_params, get_sort_params, validate_wallet_param
)
from app.api.schemas.common import PaginationParams, SortParams, BaseResponse
from app.api.schemas.referrals import (
    ReferralCodeCreateRequest, ReferralCodeResponse, ReferralProcessRequest,
    ReferralStatsResponse, ReferralLeaderboardResponse, ReferralCommissionsResponse,
    ReferralInfoResponse, ReferralConfigResponse, WebReferralProcessRequest,
    WebReferralProcessResponse
)
from app.services.referral_service import ReferralService
from app.services.prestige_service import PrestigeService
from app.models.user import UserType
from app.models.prestige import ActionType
from app.cache.cache_decorators import cached
from app.websocket.notification_service import notification_service
from app.services.commission_withdrawal_service import process_withdrawals_now, withdrawal_service

router = APIRouter(tags=["Referrals"])
logger = structlog.get_logger(__name__)


@router.post("/codes", response_model=ReferralCodeResponse)
async def create_referral_code(
    request: ReferralCodeCreateRequest,
    user_id: str = Depends(get_user_identifier),
    db: AsyncSession = Depends(get_database)
):
    """
    Create a new referral code for the current user.
    """
    referral_service = ReferralService(db)
    
    try:
        referral_code = await referral_service.create_referral_code(user_id)
        await db.commit()
        
        return ReferralCodeResponse(
            success=True,
            message="Referral code created successfully",
            code=referral_code.code,
            owner_id=referral_code.owner_id,
            usage_count=referral_code.usage_count,
            is_active=referral_code.is_active,
            expires_at=referral_code.expires_at,
            created_at=referral_code.created_at
        )
    except Exception as e:
        logger.error("Failed to create referral code", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create referral code"
        )


@router.post("/process", response_model=BaseResponse)
async def process_referral(
    request: ReferralProcessRequest,
    user_id: str = Depends(get_user_identifier),
    db: AsyncSession = Depends(get_database)
):
    """
    Process a referral using a referral code.
    Creates multi-level referral relations.
    """
    referral_service = ReferralService(db)
    
    try:
        # Determine user type based on user_id format
        user_type = UserType.TELEGRAM if user_id.startswith('tg_') else UserType.WALLET
        
        relations = await referral_service.process_referral(
            referral_code=request.referral_code,
            referee_id=user_id,
            referee_type=user_type,
            **request.additional_data
        )
        
        if not relations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid referral code or referral already processed"
            )
        
        await db.commit()
        
        # Send WebSocket notifications after successful commit
        try:
            # Get referrer information (level 1)
            primary_relation = relations[0]  # Direct referrer
            referrer_wallet = primary_relation.referrer_id
            
            # 1. Notify referrer about new referral
            await notification_service.notify_new_referral(
                referrer_wallet=referrer_wallet,
                referral_data={
                    "referee_wallet": user_id,
                    "referral_code": request.referral_code,
                    "level": 1,
                    "commission_rate": float(primary_relation.commission_rate),
                    "relations_created": len(relations),
                    "referee_type": user_type.value
                }
            )
            
            # 2. Update referrer's referral stats
            updated_stats = await referral_service.get_user_referral_stats(referrer_wallet)
            if updated_stats:
                await notification_service.notify_referral_stats_update(
                    wallet=referrer_wallet,
                    stats_data={
                        "total_referrals": updated_stats.total_referrals,
                        "total_earnings": updated_stats.total_referral_earnings,
                        "pending_commission": updated_stats.pending_commission,
                        "level_1_referrals": updated_stats.level_1_referrals,
                        "level_2_referrals": updated_stats.level_2_referrals,
                        "level_3_referrals": updated_stats.level_3_referrals,
                        "updated_reason": "new_referral_telegram",
                        "new_referee": user_id
                    }
                )
            
            logger.info(
                "✅ WebSocket notifications sent for telegram referral",
                referrer=referrer_wallet,
                referee=user_id,
                referee_type=user_type.value
            )
            
        except Exception as notification_error:
            logger.error(
                "Failed to send WebSocket notifications for telegram referral",
                referrer=referrer_wallet if 'referrer_wallet' in locals() else "unknown",
                referee=user_id,
                error=str(notification_error)
            )
            # Don't fail the response if notifications fail
        
        return BaseResponse(
            success=True,
            message=f"Referral processed successfully. Created {len(relations)} referral relations."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process referral", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process referral"
        )


@router.post("/web/process", response_model=WebReferralProcessResponse)
async def process_web_referral(
    request: WebReferralProcessRequest,
    db: AsyncSession = Depends(get_database)
):
    """
    Process a web referral after business purchase.
    Creates referral relations and awards prestige points to referrers.
    """
    referral_service = ReferralService(db)
    prestige_service = PrestigeService(db)
    
    try:
        logger.info(
            "Processing web referral", 
            referral_code=request.referral_code,
            wallet=request.wallet_address
        )
        
        # Process referral using wallet as user_id
        relations = await referral_service.process_referral(
            referral_code=request.referral_code,
            referee_id=request.wallet_address,
            referee_type=UserType.WALLET,
            wallet_address=request.wallet_address
        )
        
        if not relations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid referral code, code already used, or self-referral attempt"
            )
        
        # Get referrer information (level 1)
        primary_relation = relations[0]  # Direct referrer
        referrer_wallet = primary_relation.referrer_id
        
        # Award prestige points to referrer for successful referral invitation
        prestige_points_awarded = 0
        referrer_level_up = False
        
        try:
            points, level_up = await prestige_service.calculate_and_award_points(
                player_wallet=referrer_wallet,
                action_type=ActionType.REFERRAL_INVITED,
                action_metadata={
                    "referee_wallet": request.wallet_address,
                    "referral_code": request.referral_code
                },
                related_transaction=None
            )
            prestige_points_awarded = points
            referrer_level_up = level_up
            
            logger.info(
                "Prestige points awarded to referrer",
                referrer=referrer_wallet,
                referee=request.wallet_address,
                points=points,
                level_up=level_up
            )
        except Exception as prestige_error:
            logger.error(
                "Failed to award prestige points to referrer",
                referrer=referrer_wallet,
                referee=request.wallet_address,
                error=str(prestige_error)
            )
            # Don't fail the referral process if prestige fails
        
        # Build commission rates information
        commission_rates = []
        for relation in relations:
            commission_rates.append({
                "level": relation.level,
                "referrer_wallet": relation.referrer_id,
                "rate": float(relation.commission_rate),
                "rate_percentage": f"{float(relation.commission_rate) * 100:.1f}%"
            })
        
        await db.commit()
        
        # Send WebSocket notifications after successful commit
        try:
            # 1. Notify referrer about new referral
            await notification_service.notify_new_referral(
                referrer_wallet=referrer_wallet,
                referral_data={
                    "referee_wallet": request.wallet_address,
                    "referral_code": request.referral_code,
                    "level": 1,
                    "commission_rate": float(primary_relation.commission_rate),
                    "prestige_awarded": prestige_points_awarded,
                    "relations_created": len(relations)
                }
            )
            
            # 2. Notify referrer about prestige level up if occurred
            if referrer_level_up:
                await notification_service.notify_prestige_level_up(
                    wallet=referrer_wallet,
                    prestige_data={
                        "points_awarded": prestige_points_awarded,
                        "reason": f"Successful referral invitation: {request.wallet_address[:8]}...{request.wallet_address[-4:]}",
                        "referral_related": True,
                        "referee_wallet": request.wallet_address
                    }
                )
            
            # 3. Update referrer's referral stats
            updated_stats = await referral_service.get_user_referral_stats(referrer_wallet)
            if updated_stats:
                await notification_service.notify_referral_stats_update(
                    wallet=referrer_wallet,
                    stats_data={
                        "total_referrals": updated_stats.total_referrals,
                        "total_earnings": updated_stats.total_referral_earnings,
                        "pending_commission": updated_stats.pending_commission,
                        "level_1_referrals": updated_stats.level_1_referrals,
                        "level_2_referrals": updated_stats.level_2_referrals,
                        "level_3_referrals": updated_stats.level_3_referrals,
                        "updated_reason": "new_referral",
                        "new_referee": request.wallet_address
                    }
                )
            
            logger.info(
                "✅ WebSocket notifications sent for web referral",
                referrer=referrer_wallet,
                referee=request.wallet_address,
                notifications_sent=3 if not referrer_level_up else 4
            )
            
        except Exception as notification_error:
            logger.error(
                "Failed to send WebSocket notifications for web referral",
                referrer=referrer_wallet,
                referee=request.wallet_address,
                error=str(notification_error)
            )
            # Don't fail the response if notifications fail
        
        response = WebReferralProcessResponse(
            success=True,
            message=f"Web referral processed successfully. {len(relations)} referral relations created.",
            referral_relations_created=len(relations),
            referrer_wallet=referrer_wallet,
            referee_wallet=request.wallet_address,
            prestige_awarded_to_referrer=prestige_points_awarded,
            referrer_level_up=referrer_level_up,
            commission_rates=commission_rates,
            processing_timestamp=datetime.utcnow(),
            next_earnings_will_generate_commissions=True
        )
        
        logger.info(
            "Web referral processed successfully",
            referral_code=request.referral_code,
            referee=request.wallet_address,
            referrer=referrer_wallet,
            relations_created=len(relations),
            prestige_awarded=prestige_points_awarded
        )
        
        return response
        
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            "Failed to process web referral", 
            error=str(e), 
            referral_code=request.referral_code,
            wallet=request.wallet_address
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process web referral: {str(e)}"
        )


@router.get("/{wallet}/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(
    wallet: str = Depends(validate_wallet_param),
    db: AsyncSession = Depends(get_database)
):
    """
    Get referral statistics for the specified wallet.
    """
    referral_service = ReferralService(db)
    
    try:
        stats = await referral_service.get_user_referral_stats(wallet)
        
        if not stats:
            return ReferralStatsResponse(
                success=True,
                message="No referral stats found",
                total_referrals=0,
                total_earnings=0,
                pending_commission=0,
                level_1_referrals=0,
                level_2_referrals=0,
                level_3_referrals=0,
                level_1_earnings=0,
                level_2_earnings=0,
                level_3_earnings=0,
                last_updated_at=None
            )
        
        return ReferralStatsResponse(
            success=True,
            message="Referral stats retrieved successfully",
            total_referrals=stats.total_referrals,
            total_earnings=stats.total_referral_earnings,
            pending_commission=stats.pending_commission,
            level_1_referrals=stats.level_1_referrals,
            level_2_referrals=stats.level_2_referrals,
            level_3_referrals=stats.level_3_referrals,
            level_1_earnings=stats.level_1_earnings,
            level_2_earnings=stats.level_2_earnings,
            level_3_earnings=stats.level_3_earnings,
            last_updated_at=stats.last_updated_at
        )
    except Exception as e:
        logger.error("Failed to get referral stats", error=str(e), wallet=wallet)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get referral stats"
        )


@router.get("/{wallet}/info", response_model=ReferralInfoResponse)
async def get_referral_info(
    wallet: str = Depends(validate_wallet_param),
    level: Optional[int] = Query(None, ge=1, le=3, description="Filter by referral level"),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_database)
):
    """
    Get detailed referral information including referral list.
    """
    referral_service = ReferralService(db)
    
    try:
        # Get user's referral code
        user = await referral_service._get_user_by_id(wallet)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get referrals
        referrals = await referral_service.get_user_referrals(
            user_id=wallet,
            level=level,
            limit=pagination.limit,
            offset=pagination.offset
        )
        
        # Get stats
        stats = await referral_service.get_user_referral_stats(wallet)
        
        return ReferralInfoResponse(
            success=True,
            message="Referral information retrieved successfully",
            referral_code=user.referral_code or "N/A",
            referrals=referrals,
            total_referrals=stats.total_referrals if stats else 0,
            total_earnings=stats.total_referral_earnings if stats else 0,
            level_breakdown={
                "level_1": stats.level_1_referrals if stats else 0,
                "level_2": stats.level_2_referrals if stats else 0,
                "level_3": stats.level_3_referrals if stats else 0
            },
            earnings_breakdown={
                "level_1": stats.level_1_earnings if stats else 0,
                "level_2": stats.level_2_earnings if stats else 0,
                "level_3": stats.level_3_earnings if stats else 0
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get referral info", error=str(e), wallet=wallet)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get referral info"
        )


@router.get("/commissions", response_model=ReferralCommissionsResponse)
async def get_pending_commissions(
    user_id: str = Depends(get_user_identifier),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_database)
):
    """
    Get pending commissions for the current user.
    """
    referral_service = ReferralService(db)
    
    try:
        commissions = await referral_service.get_pending_commissions(
            user_id=user_id,
            limit=pagination.limit,
            offset=pagination.offset
        )
        
        commission_list = []
        total_pending = 0
        
        for commission in commissions:
            commission_list.append({
                "id": commission.id,
                "amount": commission.commission_amount,
                "rate": float(commission.commission_rate),
                "referee_earning_amount": commission.referee_earning_amount,
                "earning_event_id": commission.earning_event_id,
                "status": commission.status,
                "created_at": commission.created_at
            })
            total_pending += commission.commission_amount
        
        return ReferralCommissionsResponse(
            success=True,
            message="Pending commissions retrieved successfully",
            commissions=commission_list,
            total_pending_amount=total_pending,
            total_commissions=len(commission_list)
        )
    except Exception as e:
        logger.error("Failed to get pending commissions", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pending commissions"
        )


@router.get("/leaderboard", response_model=ReferralLeaderboardResponse)
@cached(ttl=300)  # Cache for 5 minutes
async def get_referral_leaderboard(
    period: str = Query("all", regex="^(daily|weekly|monthly|all)$"),
    pagination: PaginationParams = Depends(get_pagination_params),
    user_id: str = Depends(get_user_identifier),
    db: AsyncSession = Depends(get_database)
):
    """
    Get referral leaderboard.
    """
    referral_service = ReferralService(db)
    
    try:
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
        
        # Apply pagination to leaderboard
        paginated_leaderboard = leaderboard[pagination.offset:pagination.offset + pagination.limit]
        
        return ReferralLeaderboardResponse(
            success=True,
            message="Leaderboard retrieved successfully",
            leaderboard=paginated_leaderboard,
            player_rank=player_rank,
            total_players=len(leaderboard),
            period=period
        )
    except Exception as e:
        logger.error("Failed to get referral leaderboard", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get referral leaderboard"
        )


@router.get("/config", response_model=ReferralConfigResponse)
# @cached(ttl=3600)  # Cache disabled temporarily
async def get_referral_config(
    db: AsyncSession = Depends(get_database)
):
    """
    Get current referral system configuration.
    """
    referral_service = ReferralService(db)
    
    try:
        config = await referral_service._get_current_config()
        
        return ReferralConfigResponse(
            success=True,
            message="Referral config retrieved successfully",
            is_enabled=config.is_enabled,
            level_1_rate=float(config.level_1_rate),
            level_2_rate=float(config.level_2_rate),
            level_3_rate=float(config.level_3_rate),
            min_earning_threshold=config.min_earning_threshold,
            max_referral_levels=config.max_referral_levels,
            version=config.version
        )
    except Exception as e:
        logger.error("Failed to get referral config", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get referral config"
        )


# ============================================================================
# SOL BALANCE ENDPOINTS
# ============================================================================

@router.get("/{wallet}/sol-balance")
async def get_sol_balance(
    wallet: str = Depends(validate_wallet_param),
    db: AsyncSession = Depends(get_database)
):
    """
    Get user's SOL commission balance.
    """
    referral_service = ReferralService(db)
    
    try:
        balance_info = await referral_service.get_sol_balance(wallet)
        
        return {
            "success": True,
            "message": "SOL balance retrieved successfully",
            **balance_info
        }
    except Exception as e:
        logger.error("Failed to get SOL balance", error=str(e), wallet=wallet)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get SOL balance"
        )


@router.post("/{wallet}/sol-withdraw")
async def request_sol_withdrawal(
    wallet: str = Depends(validate_wallet_param),
    amount_sol: float = Query(..., gt=0, description="Amount to withdraw in SOL"),
    db: AsyncSession = Depends(get_database)
):
    """
    Request SOL withdrawal from commission balance.
    """
    referral_service = ReferralService(db)
    
    try:
        # Convert SOL to lamports
        amount_lamports = int(amount_sol * 1_000_000_000)
        
        withdrawal = await referral_service.request_sol_withdrawal(
            user_id=wallet,
            amount_lamports=amount_lamports
        )
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"SOL withdrawal requested: {amount_sol} SOL",
            "withdrawal_id": withdrawal.id,
            "amount_sol": withdrawal.amount_sol,
            "amount_lamports": withdrawal.amount_lamports,
            "status": withdrawal.status,
            "requested_at": withdrawal.requested_at
        }
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error("Failed to request SOL withdrawal", error=str(e), wallet=wallet, amount_sol=amount_sol)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to request SOL withdrawal"
        )


@router.get("/{wallet}/withdrawals")
async def get_withdrawal_history(
    wallet: str = Depends(validate_wallet_param),
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_database)
):
    """
    Get user's withdrawal history.
    """
    referral_service = ReferralService(db)
    
    try:
        withdrawals = await referral_service.get_withdrawal_history(
            user_id=wallet,
            limit=pagination.limit,
            offset=pagination.offset
        )
        
        withdrawal_list = []
        for withdrawal in withdrawals:
            withdrawal_list.append({
                "id": withdrawal.id,
                "amount_sol": withdrawal.amount_sol,
                "amount_lamports": withdrawal.amount_lamports,
                "status": withdrawal.status,
                "transaction_signature": withdrawal.transaction_signature,
                "requested_at": withdrawal.requested_at,
                "processed_at": withdrawal.processed_at,
                "error_message": withdrawal.error_message
            })
        
        return {
            "success": True,
            "message": "Withdrawal history retrieved successfully",
            "withdrawals": withdrawal_list,
            "total_withdrawals": len(withdrawal_list)
        }
    except Exception as e:
        logger.error("Failed to get withdrawal history", error=str(e), wallet=wallet)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get withdrawal history"
        )


# ============================================================================
# ADMIN ENDPOINTS FOR WITHDRAWAL PROCESSING
# ============================================================================

@router.get("/admin/pending-withdrawals")
async def get_pending_withdrawals_admin(
    pagination: PaginationParams = Depends(get_pagination_params),
    db: AsyncSession = Depends(get_database)
):
    """
    Get all pending withdrawals for admin processing.
    """
    referral_service = ReferralService(db)
    
    try:
        withdrawals = await referral_service.get_pending_withdrawals(
            limit=pagination.limit,
            offset=pagination.offset
        )
        
        withdrawal_list = []
        for withdrawal in withdrawals:
            withdrawal_list.append({
                "id": withdrawal.id,
                "user_id": withdrawal.user_id,
                "amount_sol": withdrawal.amount_sol,
                "amount_lamports": withdrawal.amount_lamports,
                "status": withdrawal.status,
                "requested_at": withdrawal.requested_at
            })
        
        return {
            "success": True,
            "message": "Pending withdrawals retrieved successfully",
            "withdrawals": withdrawal_list,
            "total_pending": len(withdrawal_list)
        }
    except Exception as e:
        logger.error("Failed to get pending withdrawals", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get pending withdrawals"
        )


@router.post("/admin/withdrawal/{withdrawal_id}/complete")
async def complete_withdrawal_admin(
    withdrawal_id: int,
    transaction_signature: str = Query(..., description="Solana transaction signature"),
    db: AsyncSession = Depends(get_database)
):
    """
    Complete a withdrawal with transaction signature (admin only).
    """
    referral_service = ReferralService(db)
    
    try:
        withdrawal = await referral_service.complete_sol_withdrawal(
            withdrawal_id=withdrawal_id,
            transaction_signature=transaction_signature
        )
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"Withdrawal {withdrawal_id} completed successfully",
            "withdrawal": {
                "id": withdrawal.id,
                "user_id": withdrawal.user_id,
                "amount_sol": withdrawal.amount_sol,
                "status": withdrawal.status,
                "transaction_signature": withdrawal.transaction_signature,
                "processed_at": withdrawal.processed_at
            }
        }
    except Exception as e:
        logger.error("Failed to complete withdrawal", error=str(e), withdrawal_id=withdrawal_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete withdrawal"
        )


@router.post("/admin/withdrawal/{withdrawal_id}/fail")
async def fail_withdrawal_admin(
    withdrawal_id: int,
    error_message: str = Query(..., description="Error message"),
    db: AsyncSession = Depends(get_database)
):
    """
    Mark a withdrawal as failed (admin only).
    """
    referral_service = ReferralService(db)
    
    try:
        withdrawal = await referral_service.fail_sol_withdrawal(
            withdrawal_id=withdrawal_id,
            error_message=error_message
        )
        
        await db.commit()
        
        return {
            "success": True,
            "message": f"Withdrawal {withdrawal_id} marked as failed",
            "withdrawal": {
                "id": withdrawal.id,
                "user_id": withdrawal.user_id,
                "amount_sol": withdrawal.amount_sol,
                "status": withdrawal.status,
                "error_message": withdrawal.error_message,
                "processed_at": withdrawal.processed_at
            }
        }
    except Exception as e:
        logger.error("Failed to mark withdrawal as failed", error=str(e), withdrawal_id=withdrawal_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to mark withdrawal as failed"
        )


@router.post("/admin/process-withdrawals")
async def process_withdrawals_manually():
    """
    Manually trigger commission withdrawal processing (admin only).
    """
    try:
        result = await process_withdrawals_now()
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Successfully processed {result['processed_withdrawals']} withdrawals",
                "processed_withdrawals": result["processed_withdrawals"],
                "admin_balance_sol": result["admin_balance_sol"],
                "processed_at": result["processed_at"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.get("error", "Unknown error occurred")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to process withdrawals manually", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process withdrawals"
        )


@router.get("/admin/withdrawal-service-status")
async def get_withdrawal_service_status():
    """
    Get status of the automatic withdrawal service (admin only).
    """
    try:
        admin_balance = await withdrawal_service.get_admin_balance()
        is_configured = withdrawal_service.is_configured()
        
        return {
            "success": True,
            "message": "Withdrawal service status retrieved",
            "service_configured": is_configured,
            "admin_balance_sol": admin_balance,
            "admin_public_key": str(withdrawal_service.admin_keypair.pubkey()) if is_configured else None,
            "min_withdrawal_amount": withdrawal_service.min_withdrawal_amount,
            "max_batch_size": withdrawal_service.max_batch_size,
            "status_checked_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to get withdrawal service status", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get service status"
        )


@router.post("/commission/{commission_id}/pay", response_model=BaseResponse)
async def pay_commission(
    commission_id: int,
    transaction_signature: str = Query(..., description="Solana transaction signature"),
    user_id: str = Depends(get_user_identifier),
    db: AsyncSession = Depends(get_database)
):
    """
    Mark a commission as paid (for admin use or integration with payment system).
    """
    referral_service = ReferralService(db)
    
    try:
        commission = await referral_service.pay_commission(
            commission_id=commission_id,
            transaction_signature=transaction_signature
        )
        
        await db.commit()
        
        return BaseResponse(
            success=True,
            message=f"Commission {commission_id} marked as paid"
        )
    except Exception as e:
        logger.error("Failed to pay commission", error=str(e), commission_id=commission_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pay commission"
        )
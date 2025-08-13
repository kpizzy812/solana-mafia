"""
Earnings routes for the Solana Mafia API.
Handles earnings-related endpoints including claiming and history.
"""

from fastapi import APIRouter, HTTPException, status
from app.api.schemas.common import SuccessResponse, create_success_response
from app.services.resilient_earnings_processor import get_resilient_earnings_processor
from app.scheduler.earnings_scheduler import trigger_manual_earnings

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
    "/{wallet}/update",
    response_model=SuccessResponse,
    summary="Update Player Earnings",
    description="Manually trigger earnings update for a specific player with retry logic"
)
async def update_player_earnings(wallet: str):
    """🔄 Ручное обновление earnings для конкретного игрока."""
    try:
        # Получаем processor
        processor = await get_resilient_earnings_processor()
        
        # Обновляем earnings с retry логикой
        success = await processor.update_single_player(wallet)
        
        if success:
            return create_success_response(
                data={"wallet": wallet, "updated": True},
                message="Earnings updated successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update earnings after retries"
            )
            
    except Exception as e:
        logger.error(f"🚨 Error updating earnings for {wallet}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating earnings: {str(e)}"
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


@router.post(
    "/system/trigger-manual",
    response_model=SuccessResponse,
    summary="Manual Earnings Process",
    description="Manually trigger the daily earnings process for all players (for testing)"
)
async def trigger_manual_earnings_process():
    """🚀 Ручной запуск полного процесса начисления прибыли для всех игроков."""
    try:
        logger.info("🎯 Manual earnings process triggered via API")
        
        # Запускаем полный процесс начисления через планировщик
        processing_stats = await trigger_manual_earnings()
        
        logger.info(
            "✅ Manual earnings process completed successfully",
            total_players=processing_stats.total_players_found,
            successful_updates=processing_stats.successful_updates,
            failed_updates=processing_stats.failed_updates,
            processing_time=f"{processing_stats.total_processing_time:.2f}s",
            success_rate=f"{processing_stats.success_rate * 100:.1f}%"
        )
        
        return create_success_response(
            data={
                "processing_stats": {
                    "total_players_found": processing_stats.total_players_found,
                    "successful_updates": processing_stats.successful_updates,
                    "failed_updates": processing_stats.failed_updates,
                    "processing_time_seconds": round(processing_stats.total_processing_time, 2),
                    "success_rate_percent": round(processing_stats.success_rate * 100, 1),
                    "errors": processing_stats.errors[:5] if processing_stats.errors else []  # Показываем первые 5 ошибок
                },
                "message": "Manual earnings process completed",
                "notifications_sent": True
            },
            message=f"Processed {processing_stats.successful_updates}/{processing_stats.total_players_found} players successfully"
        )
        
    except Exception as e:
        logger.error(f"🚨 Error during manual earnings process: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Manual earnings process failed: {str(e)}"
        )
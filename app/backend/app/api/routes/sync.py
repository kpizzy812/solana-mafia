"""
Blockchain Sync routes for monitoring and managing data synchronization.

Provides endpoints for:
- Health checks and sync status
- Manual sync operations
- Detailed sync reports
- PDA validation statistics
"""

from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, List

from app.api.dependencies import get_database
from app.api.schemas.common import SuccessResponse, create_success_response
from app.models.player import Player
from app.services.blockchain_sync_service import (
    get_blockchain_sync_service,
    manual_sync,
    start_blockchain_sync,
    stop_blockchain_sync
)
from app.services.pda_validator import get_pda_validator

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter()


@router.get(
    "/health",
    response_model=SuccessResponse,
    summary="Blockchain Sync Health Check",
    description="Get comprehensive health status of blockchain synchronization"
)
async def get_sync_health():
    """
    Получить статус здоровья blockchain синхронизации.
    
    Возвращает:
    - Статус sync сервиса
    - Последняя синхронизация
    - Метрики производительности
    - Информация о кэше
    """
    try:
        sync_service = await get_blockchain_sync_service()
        validator = await get_pda_validator()
        
        # Получаем статусы сервисов
        sync_status = await sync_service.get_sync_status()
        cache_stats = validator.get_cache_stats()
        
        health_data = {
            "blockchain_sync": {
                "status": "healthy" if sync_status["is_running"] else "stopped",
                "is_running": sync_status["is_running"],
                "last_sync": sync_status["last_sync"],
                "next_sync_in_seconds": sync_status["next_sync_in_seconds"],
                "total_operations_24h": sync_status["total_operations_24h"],
                "sync_interval_hours": sync_status["sync_interval_hours"]
            },
            "pda_validator": {
                "cache_entries": cache_stats["total_entries"],
                "expired_entries": cache_stats["expired_entries"],
                "cache_ttl_minutes": cache_stats["cache_ttl_minutes"]
            },
            "last_session": sync_status.get("last_session"),
            "recent_operations": sync_status.get("recent_operations", [])
        }
        
        return create_success_response(health_data)
        
    except Exception as e:
        logger.error("Failed to get sync health", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get sync health: {str(e)}"
        )


@router.get(
    "/report",
    response_model=SuccessResponse,
    summary="Detailed Sync Report",
    description="Get comprehensive synchronization report with blockchain validation"
)
async def get_detailed_sync_report(db: AsyncSession = Depends(get_database)):
    """
    Получить детальный отчет о синхронизации базы данных с blockchain.
    
    Включает:
    - Валидацию всех игроков
    - Статистику синхронизации
    - Список невалидных аккаунтов
    - История операций
    """
    try:
        # Получаем всех активных игроков из базы
        result = await db.execute(
            select(Player.wallet).where(Player.is_active == True)
        )
        db_players = [row[0] for row in result.fetchall()]
        
        # Генерируем детальный отчет
        sync_service = await get_blockchain_sync_service()
        detailed_report = await sync_service.get_detailed_sync_report()
        
        # Добавляем информацию о текущих игроках
        detailed_report["current_database_state"] = {
            "total_active_players": len(db_players),
            "player_wallets": db_players
        }
        
        return create_success_response(detailed_report)
        
    except Exception as e:
        logger.error("Failed to generate detailed sync report", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate sync report: {str(e)}"
        )


@router.post(
    "/manual",
    response_model=SuccessResponse,
    summary="Manual Sync",
    description="Trigger manual blockchain synchronization"
)
async def trigger_manual_sync(background_tasks: BackgroundTasks):
    """
    Запустить мануальную синхронизацию blockchain.
    
    Операция выполняется в фоне и возвращает session_id для отслеживания.
    """
    try:
        logger.info("Manual sync triggered via API")
        
        # Запускаем синхронизацию в фоне
        sync_report = await manual_sync()
        
        return create_success_response({
            "session_id": sync_report.session_id,
            "started_at": sync_report.started_at.isoformat(),
            "players_checked": sync_report.players_checked,
            "players_removed": sync_report.players_removed,
            "businesses_removed": sync_report.businesses_removed,
            "success": sync_report.success,
            "duration_seconds": sync_report.duration_seconds,
            "error": sync_report.error
        })
        
    except Exception as e:
        logger.error("Failed to trigger manual sync", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger manual sync: {str(e)}"
        )


@router.post(
    "/validate-players",
    response_model=SuccessResponse,
    summary="Validate Players",
    description="Validate specific player wallets against blockchain"
)
async def validate_players_endpoint(
    player_wallets: List[str],
    use_cache: bool = True
):
    """
    Валидировать список игроков против blockchain.
    
    Args:
        player_wallets: Список кошельков для валидации
        use_cache: Использовать кэш результатов
        
    Returns:
        Результаты валидации для каждого игрока
    """
    try:
        if len(player_wallets) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many players to validate, max 50 allowed"
            )
        
        validator = await get_pda_validator()
        
        if len(player_wallets) == 1:
            # Одиночная валидация
            result = await validator.validate_player_pda(player_wallets[0], use_cache)
            validation_results = [result]
        else:
            # Batch валидация
            validation_results = await validator.batch_validate_players(player_wallets)
        
        # Конвертируем результаты в JSON-serializable формат
        results_data = []
        for result in validation_results:
            results_data.append({
                "wallet": result.wallet,
                "pda": result.pda,
                "exists": result.exists,
                "is_valid": result.is_valid,
                "data_size": result.data_size,
                "owner": result.owner,
                "error": result.error,
                "checked_at": result.checked_at.isoformat() if result.checked_at else None
            })
        
        # Статистика
        valid_count = sum(1 for r in validation_results if r.is_valid)
        existing_count = sum(1 for r in validation_results if r.exists)
        
        return create_success_response({
            "validation_results": results_data,
            "summary": {
                "total_players": len(player_wallets),
                "valid_players": valid_count,
                "existing_pdas": existing_count,
                "invalid_players": len(player_wallets) - valid_count,
                "success_rate": f"{(valid_count / len(player_wallets) * 100):.1f}%" if player_wallets else "0%"
            }
        })
        
    except Exception as e:
        logger.error("Failed to validate players", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate players: {str(e)}"
        )


@router.post(
    "/start",
    response_model=SuccessResponse,
    summary="Start Periodic Sync",
    description="Start automatic periodic blockchain synchronization"
)
async def start_periodic_sync():
    """
    Запустить автоматическую периодическую синхронизацию.
    """
    try:
        await start_blockchain_sync()
        
        return create_success_response({
            "message": "Periodic blockchain sync started",
            "sync_interval_hours": 1
        })
        
    except Exception as e:
        logger.error("Failed to start periodic sync", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start periodic sync: {str(e)}"
        )


@router.post(
    "/stop",
    response_model=SuccessResponse,
    summary="Stop Periodic Sync",
    description="Stop automatic periodic blockchain synchronization"
)
async def stop_periodic_sync():
    """
    Остановить автоматическую периодическую синхронизацию.
    """
    try:
        await stop_blockchain_sync()
        
        return create_success_response({
            "message": "Periodic blockchain sync stopped"
        })
        
    except Exception as e:
        logger.error("Failed to stop periodic sync", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop periodic sync: {str(e)}"
        )


@router.delete(
    "/cache",
    response_model=SuccessResponse,
    summary="Clear Validation Cache",
    description="Clear PDA validation cache to force fresh validation"
)
async def clear_validation_cache():
    """
    Очистить кэш валидации для принудительного обновления.
    """
    try:
        validator = await get_pda_validator()
        cache_stats_before = validator.get_cache_stats()
        
        validator.clear_cache()
        
        return create_success_response({
            "message": "Validation cache cleared",
            "entries_cleared": cache_stats_before["total_entries"]
        })
        
    except Exception as e:
        logger.error("Failed to clear validation cache", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear validation cache: {str(e)}"
        )
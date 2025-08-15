"""
Business Sync API endpoints для тестирования синхронизации бизнесов.
"""

from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime

from app.services.player_business_sync import get_player_business_sync_service
from app.services.blockchain_sync_service import get_blockchain_sync_service, manual_sync

router = APIRouter()


@router.get("/player/{wallet_address}/portfolio")
async def get_player_portfolio(wallet_address: str) -> Dict[str, Any]:
    """
    Получить портфолио игрока с blockchain.
    
    Args:
        wallet_address: Адрес кошелька игрока
        
    Returns:
        Полная информация о портфолио игрока
    """
    business_sync_service = await get_player_business_sync_service()
    
    portfolio = await business_sync_service.get_player_portfolio(wallet_address)
    if not portfolio:
        raise HTTPException(status_code=404, detail="Player not found or no businesses")
    
    return {
        "wallet": portfolio.wallet,
        "total_invested": portfolio.total_invested,
        "total_upgrade_spent": portfolio.total_upgrade_spent,
        "total_slot_spent": portfolio.total_slot_spent,
        "pending_earnings": portfolio.pending_earnings,
        "calculated_total_invested": portfolio.calculated_total_invested,
        "business_count": portfolio.business_count,
        "businesses": [
            {
                "slot_index": biz.slot_index,
                "business_type": biz.business_type,
                "business_type_name": biz.business_type_name,
                "base_invested_amount": biz.base_invested_amount,
                "total_invested_amount": biz.total_invested_amount,
                "daily_rate": biz.daily_rate,
                "upgrade_level": biz.upgrade_level,
                "upgrade_history": biz.upgrade_history,
                "is_active": biz.is_active,
                "created_at": biz.created_at.isoformat(),
                "last_claim": biz.last_claim.isoformat(),
                "total_earned": biz.total_earned,
                "slot_type": biz.slot_type,
                "slot_cost_paid": biz.slot_cost_paid,
                "slot_is_paid": biz.slot_is_paid,
                "slot_yield_bonus": biz.slot_yield_bonus
            }
            for biz in portfolio.businesses
        ],
        "portfolio_analysis": {
            "discrepancy": portfolio.total_invested - portfolio.calculated_total_invested,
            "is_consistent": portfolio.total_invested == portfolio.calculated_total_invested
        }
    }


@router.post("/player/{wallet_address}/sync")
async def sync_player_businesses(wallet_address: str) -> Dict[str, Any]:
    """
    Синхронизировать бизнесы игрока с базой данных.
    
    Args:
        wallet_address: Адрес кошелька игрока
        
    Returns:
        Отчет о синхронизации
    """
    business_sync_service = await get_player_business_sync_service()
    
    sync_report = await business_sync_service.sync_player_businesses(wallet_address)
    
    if not sync_report.get("success", False):
        raise HTTPException(
            status_code=400, 
            detail=f"Sync failed: {sync_report.get('error', 'Unknown error')}"
        )
    
    return sync_report


@router.post("/full-sync")
async def trigger_full_sync() -> Dict[str, Any]:
    """
    Запустить полную синхронизацию всех игроков и их бизнесов.
    
    Returns:
        Детальный отчет о синхронизации
    """
    sync_report = await manual_sync()
    
    return {
        "session_id": sync_report.session_id,
        "started_at": sync_report.started_at.isoformat(),
        "completed_at": sync_report.completed_at.isoformat() if sync_report.completed_at else None,
        "duration_seconds": sync_report.duration_seconds,
        "success": sync_report.success,
        "error": sync_report.error,
        "statistics": {
            "players_checked": sync_report.players_checked,
            "players_removed": sync_report.players_removed,
            "businesses_removed": sync_report.businesses_removed,
            "players_business_synced": sync_report.players_business_synced,
            "businesses_added": sync_report.businesses_added,
            "businesses_updated": sync_report.businesses_updated,
            "portfolio_discrepancies": sync_report.portfolio_discrepancies
        },
        "operations_count": len(sync_report.operations),
        "operations": [
            {
                "action": op.action.value,
                "target_type": op.target_type,
                "target_id": op.target_id,
                "reason": op.reason,
                "timestamp": op.timestamp.isoformat(),
                "details": op.details
            }
            for op in sync_report.operations[-10:]  # Последние 10 операций
        ]
    }


@router.get("/sync-status")
async def get_sync_status() -> Dict[str, Any]:
    """
    Получить статус периодической синхронизации.
    
    Returns:
        Статус sync сервиса
    """
    sync_service = await get_blockchain_sync_service()
    status = await sync_service.get_sync_status()
    
    return status


@router.get("/sync-report")
async def get_detailed_sync_report() -> Dict[str, Any]:
    """
    Получить детальный отчет о синхронизации.
    
    Returns:
        Полный отчет со всей статистикой
    """
    sync_service = await get_blockchain_sync_service()
    report = await sync_service.get_detailed_sync_report()
    
    return report
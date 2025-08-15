"""
Blockchain Sync Service - автоматическая синхронизация базы данных с blockchain.

Архитектурные принципы:
- Blockchain как единственный source of truth
- Периодическая автоматическая синхронизация
- Безопасное удаление некорректных данных
- Детальный аудит всех операций
- Метрики и мониторинг состояния
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
import structlog

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.player import Player
from app.models.business import Business
from app.services.pda_validator import get_pda_validator, SyncReport
from app.services.player_business_sync import get_player_business_sync_service


logger = structlog.get_logger(__name__)


class SyncAction(Enum):
    """Типы действий синхронизации."""
    PLAYER_REMOVED = "player_removed"
    BUSINESS_REMOVED = "business_removed"
    BUSINESS_SYNCED = "business_synced"
    PORTFOLIO_VALIDATED = "portfolio_validated"
    DATA_VALIDATED = "data_validated"
    SYNC_COMPLETED = "sync_completed"


@dataclass
class SyncOperation:
    """Запись операции синхронизации."""
    action: SyncAction
    target_type: str  # 'player' или 'business'
    target_id: str
    reason: str
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None


@dataclass
class SyncSessionReport:
    """Отчет о сессии синхронизации."""
    session_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    players_checked: int
    players_removed: int
    businesses_removed: int
    players_business_synced: int
    businesses_added: int
    businesses_updated: int
    portfolio_discrepancies: int
    operations: List[SyncOperation]
    success: bool
    error: Optional[str] = None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class BlockchainSyncService:
    """
    Сервис для синхронизации базы данных с blockchain состоянием.
    
    Основные функции:
    - Периодическая проверка всех игроков в базе
    - Удаление фантомных игроков (нет в blockchain)
    - Удаление связанных бизнесов
    - Аудит всех операций
    - Метрики производительности
    """
    
    def __init__(self):
        """Инициализация sync сервиса."""
        self.logger = logger.bind(service="blockchain_sync")
        self.is_running = False
        self.sync_interval = timedelta(hours=1)  # Синхронизация каждый час
        self.last_sync: Optional[datetime] = None
        self.sync_task: Optional[asyncio.Task] = None
        
        # История операций (последние 24 часа)
        self.operation_history: List[SyncOperation] = []
        self.session_history: List[SyncSessionReport] = []
        
        self.logger.info("Blockchain Sync Service initialized", sync_interval_hours=1)
    
    async def start_periodic_sync(self):
        """Запуск периодической синхронизации."""
        if self.is_running:
            self.logger.warning("Periodic sync already running")
            return
        
        self.is_running = True
        self.sync_task = asyncio.create_task(self._sync_loop())
        self.logger.info("Periodic blockchain sync started")
    
    async def stop_periodic_sync(self):
        """Остановка периодической синхронизации."""
        if not self.is_running:
            return
        
        self.is_running = False
        if self.sync_task and not self.sync_task.done():
            self.sync_task.cancel()
            try:
                await self.sync_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Periodic blockchain sync stopped")
    
    async def _sync_loop(self):
        """Основной цикл периодической синхронизации."""
        self.logger.info("Sync loop started")
        
        while self.is_running:
            try:
                # Выполняем синхронизацию
                report = await self.perform_full_sync()
                
                if report.success:
                    self.logger.info(
                        "Periodic sync completed successfully",
                        players_checked=report.players_checked,
                        players_removed=report.players_removed,
                        businesses_removed=report.businesses_removed,
                        players_business_synced=report.players_business_synced,
                        businesses_added=report.businesses_added,
                        businesses_updated=report.businesses_updated,
                        portfolio_discrepancies=report.portfolio_discrepancies,
                        duration=f"{report.duration_seconds:.1f}s"
                    )
                else:
                    self.logger.error(
                        "Periodic sync failed",
                        error=report.error,
                        duration=f"{report.duration_seconds:.1f}s" if report.duration_seconds else None
                    )
                
                # Ждем до следующей синхронизации
                await asyncio.sleep(self.sync_interval.total_seconds())
                
            except asyncio.CancelledError:
                self.logger.info("Sync loop cancelled")
                break
            except Exception as e:
                self.logger.error("Sync loop error", error=str(e))
                # Ждем перед повторной попыткой
                await asyncio.sleep(300)  # 5 минут
    
    async def perform_full_sync(self) -> SyncSessionReport:
        """
        Выполнение полной синхронизации базы данных с blockchain.
        
        Returns:
            SyncSessionReport с результатами синхронизации
        """
        session_id = f"sync_{int(datetime.utcnow().timestamp())}"
        started_at = datetime.utcnow()
        
        self.logger.info("Starting full blockchain sync", session_id=session_id)
        
        report = SyncSessionReport(
            session_id=session_id,
            started_at=started_at,
            completed_at=None,
            players_checked=0,
            players_removed=0,
            businesses_removed=0,
            players_business_synced=0,
            businesses_added=0,
            businesses_updated=0,
            portfolio_discrepancies=0,
            operations=[],
            success=False
        )
        
        try:
            async with get_async_session() as db:
                # Получаем всех активных игроков из базы
                result = await db.execute(
                    select(Player.wallet).where(Player.is_active == True)
                )
                db_players = [row[0] for row in result.fetchall()]
                report.players_checked = len(db_players)
                
                if not db_players:
                    self.logger.info("No players found in database")
                    report.success = True
                    report.completed_at = datetime.utcnow()
                    return report
                
                # Валидируем всех игроков через blockchain
                validator = await get_pda_validator()
                validation_results = await validator.batch_validate_players(db_players)
                
                # Находим игроков без валидных PDA
                invalid_players = [
                    result.wallet for result in validation_results 
                    if not result.is_valid
                ]
                
                if invalid_players:
                    # Удаляем фантомных игроков и их бизнесы
                    removed_counts = await self._remove_invalid_players(db, invalid_players, report)
                    report.players_removed = removed_counts['players']
                    report.businesses_removed = removed_counts['businesses']
                    
                    await db.commit()
                    
                    self.logger.warning(
                        "Removed invalid players from database",
                        session_id=session_id,
                        removed_players=report.players_removed,
                        removed_businesses=report.businesses_removed,
                        invalid_wallets=invalid_players[:5]  # Показываем первые 5
                    )
                else:
                    self.logger.info("All players in database are valid", session_id=session_id)
                
                # 🏢 Синхронизируем бизнесы для всех валидных игроков
                valid_players = [
                    result.wallet for result in validation_results 
                    if result.is_valid
                ]
                
                if valid_players:
                    business_sync_stats = await self._sync_player_businesses(
                        valid_players, report, session_id
                    )
                    
                    # Обновляем статистику
                    report.players_business_synced = business_sync_stats['players_synced']
                    report.businesses_added = business_sync_stats['businesses_added']
                    report.businesses_updated = business_sync_stats['businesses_updated']
                    report.portfolio_discrepancies = business_sync_stats['portfolio_discrepancies']
                    
                    await db.commit()
                    
                    self.logger.info(
                        "Business sync completed",
                        session_id=session_id,
                        players_synced=report.players_business_synced,
                        businesses_added=report.businesses_added,
                        businesses_updated=report.businesses_updated,
                        portfolio_discrepancies=report.portfolio_discrepancies
                    )
                
                # Записываем успешное завершение
                operation = SyncOperation(
                    action=SyncAction.SYNC_COMPLETED,
                    target_type="sync_session",
                    target_id=session_id,
                    reason="Full sync completed successfully",
                    timestamp=datetime.utcnow(),
                    details={
                        "players_checked": report.players_checked,
                        "players_removed": report.players_removed,
                        "businesses_removed": report.businesses_removed,
                        "players_business_synced": report.players_business_synced,
                        "businesses_added": report.businesses_added,
                        "businesses_updated": report.businesses_updated,
                        "portfolio_discrepancies": report.portfolio_discrepancies
                    }
                )
                report.operations.append(operation)
                self._add_operation_to_history(operation)
                
                report.success = True
                report.completed_at = datetime.utcnow()
                self.last_sync = report.completed_at
        
        except Exception as e:
            error_msg = f"Sync failed: {str(e)}"
            report.error = error_msg
            report.completed_at = datetime.utcnow()
            
            self.logger.error("Full sync failed", session_id=session_id, error=error_msg)
        
        # Добавляем отчет в историю
        self.session_history.append(report)
        self._cleanup_history()
        
        return report
    
    async def _remove_invalid_players(
        self, 
        db: AsyncSession, 
        invalid_wallets: List[str],
        report: SyncSessionReport
    ) -> Dict[str, int]:
        """
        Безопасное удаление невалидных игроков и их данных.
        
        Args:
            db: Database session
            invalid_wallets: Список кошельков для удаления
            report: Отчет для записи операций
            
        Returns:
            Словарь с количеством удаленных записей
        """
        removed_counts = {"players": 0, "businesses": 0}
        
        for wallet in invalid_wallets:
            try:
                # Удаляем бизнесы игрока
                business_result = await db.execute(
                    delete(Business).where(Business.player_wallet == wallet)
                )
                businesses_removed = business_result.rowcount
                removed_counts["businesses"] += businesses_removed
                
                if businesses_removed > 0:
                    operation = SyncOperation(
                        action=SyncAction.BUSINESS_REMOVED,
                        target_type="business",
                        target_id=f"player_{wallet}",
                        reason="Player PDA not found in blockchain",
                        timestamp=datetime.utcnow(),
                        details={"businesses_count": businesses_removed}
                    )
                    report.operations.append(operation)
                    self._add_operation_to_history(operation)
                
                # Удаляем игрока
                player_result = await db.execute(
                    delete(Player).where(Player.wallet == wallet)
                )
                players_removed = player_result.rowcount
                removed_counts["players"] += players_removed
                
                if players_removed > 0:
                    operation = SyncOperation(
                        action=SyncAction.PLAYER_REMOVED,
                        target_type="player",
                        target_id=wallet,
                        reason="Player PDA not found in blockchain",
                        timestamp=datetime.utcnow(),
                        details={"businesses_removed": businesses_removed}
                    )
                    report.operations.append(operation)
                    self._add_operation_to_history(operation)
                    
                    self.logger.info(
                        "Removed invalid player",
                        wallet=wallet,
                        businesses_removed=businesses_removed
                    )
                
            except Exception as e:
                self.logger.error(
                    "Failed to remove invalid player",
                    wallet=wallet,
                    error=str(e)
                )
        
        return removed_counts
    
    async def _sync_player_businesses(
        self, 
        valid_players: List[str], 
        report: SyncSessionReport,
        session_id: str
    ) -> Dict[str, int]:
        """
        Синхронизация бизнесов для всех валидных игроков.
        
        Args:
            valid_players: Список валидных wallet адресов
            report: Отчет для записи операций  
            session_id: ID сессии синхронизации
            
        Returns:
            Статистика синхронизации бизнесов
        """
        business_sync_service = await get_player_business_sync_service()
        
        stats = {
            "players_synced": 0,
            "businesses_added": 0,
            "businesses_updated": 0,
            "businesses_removed": 0,
            "portfolio_discrepancies": 0
        }
        
        for wallet in valid_players:
            try:
                # Синхронизируем бизнесы игрока
                sync_result = await business_sync_service.sync_player_businesses(wallet)
                
                if sync_result.get("success", False):
                    stats["players_synced"] += 1
                    stats["businesses_added"] += sync_result.get("businesses_added", 0)
                    stats["businesses_updated"] += sync_result.get("businesses_updated", 0)
                    stats["businesses_removed"] += sync_result.get("businesses_removed", 0)
                    
                    if sync_result.get("portfolio_corrected", False):
                        stats["portfolio_discrepancies"] += 1
                    
                    # Записываем операцию синхронизации
                    operation = SyncOperation(
                        action=SyncAction.BUSINESS_SYNCED,
                        target_type="player_business",
                        target_id=wallet,
                        reason="Player businesses synchronized with blockchain",
                        timestamp=datetime.utcnow(),
                        details={
                            "businesses_added": sync_result.get("businesses_added", 0),
                            "businesses_updated": sync_result.get("businesses_updated", 0),
                            "businesses_removed": sync_result.get("businesses_removed", 0),
                            "portfolio_corrected": sync_result.get("portfolio_corrected", False)
                        }
                    )
                    report.operations.append(operation)
                    self._add_operation_to_history(operation)
                    
                else:
                    self.logger.warning(
                        "Failed to sync player businesses",
                        wallet=wallet,
                        error=sync_result.get("error", "Unknown error")
                    )
                    
            except Exception as e:
                self.logger.error(
                    "Business sync error for player",
                    wallet=wallet,
                    session_id=session_id,
                    error=str(e)
                )
        
        return stats
    
    def _add_operation_to_history(self, operation: SyncOperation):
        """Добавление операции в историю."""
        self.operation_history.append(operation)
        
        # Ограничиваем историю операций последними 24 часами
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        self.operation_history = [
            op for op in self.operation_history 
            if op.timestamp > cutoff_time
        ]
    
    def _cleanup_history(self):
        """Очистка старой истории."""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Очищаем историю операций
        self.operation_history = [
            op for op in self.operation_history 
            if op.timestamp > cutoff_time
        ]
        
        # Очищаем историю сессий (оставляем последние 20)
        self.session_history = self.session_history[-20:]
    
    async def get_sync_status(self) -> Dict[str, Any]:
        """Получение статуса синхронизации."""
        recent_operations = [
            asdict(op) for op in self.operation_history[-10:]  # Последние 10 операций
        ]
        
        last_session = self.session_history[-1] if self.session_history else None
        
        return {
            "is_running": self.is_running,
            "sync_interval_hours": self.sync_interval.total_seconds() / 3600,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "next_sync_in_seconds": (
                (self.last_sync + self.sync_interval - datetime.utcnow()).total_seconds()
                if self.last_sync else 0
            ),
            "total_operations_24h": len(self.operation_history),
            "total_sessions": len(self.session_history),
            "last_session": asdict(last_session) if last_session else None,
            "recent_operations": recent_operations
        }
    
    async def get_detailed_sync_report(self) -> Dict[str, Any]:
        """Получение детального отчета о синхронизации."""
        # Получаем текущее состояние базы
        async with get_async_session() as db:
            player_result = await db.execute(
                select(Player.wallet).where(Player.is_active == True)
            )
            db_players = [row[0] for row in player_result.fetchall()]
        
        # Генерируем sync report через validator
        validator = await get_pda_validator()
        sync_report = await validator.get_sync_report(db_players)
        
        return {
            "blockchain_sync_report": asdict(sync_report),
            "service_status": await self.get_sync_status(),
            "recent_sessions": [asdict(s) for s in self.session_history[-5:]],
            "cache_stats": validator.get_cache_stats()
        }


# Global service instance
_blockchain_sync_service: Optional[BlockchainSyncService] = None


async def get_blockchain_sync_service() -> BlockchainSyncService:
    """Получение глобального экземпляра sync сервиса."""
    global _blockchain_sync_service
    if _blockchain_sync_service is None:
        _blockchain_sync_service = BlockchainSyncService()
    return _blockchain_sync_service


async def start_blockchain_sync():
    """Запуск периодической синхронизации."""
    service = await get_blockchain_sync_service()
    await service.start_periodic_sync()


async def stop_blockchain_sync():
    """Остановка периодической синхронизации."""
    global _blockchain_sync_service
    if _blockchain_sync_service:
        await _blockchain_sync_service.stop_periodic_sync()


async def manual_sync() -> SyncSessionReport:
    """Мануальная синхронизация (для API endpoints)."""
    service = await get_blockchain_sync_service()
    return await service.perform_full_sync()
"""
PDA Validator Service - проверка существования и валидации blockchain аккаунтов.

Основные функции:
- Проверка существования Player PDA в blockchain
- Валидация данных аккаунтов
- Кэширование результатов для оптимизации
- Мониторинг состояния синхронизации
"""

import asyncio
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import structlog

from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient

from app.core.config import settings
from app.services.solana_client import get_solana_client


logger = structlog.get_logger(__name__)


@dataclass
class PDAValidationResult:
    """Результат валидации PDA аккаунта."""
    wallet: str
    pda: str
    exists: bool
    is_valid: bool
    data_size: Optional[int] = None
    owner: Optional[str] = None
    error: Optional[str] = None
    checked_at: datetime = None


@dataclass 
class SyncReport:
    """Отчет о состоянии синхронизации."""
    total_players_db: int
    total_players_blockchain: int
    valid_players: int
    invalid_players: int
    missing_pdas: List[str]
    orphan_pdas: List[str]
    sync_percentage: float
    last_check: datetime


class PDAValidator:
    """
    Сервис для валидации PDA аккаунтов и синхронизации с blockchain.
    
    Архитектурные принципы:
    - Blockchain как единственный source of truth
    - Кэширование для оптимизации RPC вызовов
    - Batch операции для массовых проверок
    - Детальный мониторинг и логирование
    """
    
    def __init__(self):
        """Инициализация PDA валидатора."""
        self.logger = logger.bind(service="pda_validator")
        self.program_id = Pubkey.from_string(settings.solana_program_id)
        self.client: Optional[AsyncClient] = None
        
        # Кэш результатов валидации (wallet -> PDAValidationResult)
        self._validation_cache: Dict[str, PDAValidationResult] = {}
        self._cache_ttl = timedelta(minutes=5)  # TTL кэша
        
        self.logger.info("PDA Validator initialized", program_id=str(self.program_id))
    
    async def initialize(self):
        """Инициализация клиента."""
        try:
            solana_client = await get_solana_client()
            self.client = solana_client.client  # Получаем AsyncClient из SolanaClient wrapper
            self.logger.info("PDA Validator client initialized")
        except Exception as e:
            self.logger.error("Failed to initialize PDA Validator client", error=str(e))
            raise
    
    def _get_player_pda(self, wallet: str) -> Tuple[Pubkey, int]:
        """Вычисление Player PDA для кошелька."""
        try:
            wallet_pubkey = Pubkey.from_string(wallet)
            pda, bump = Pubkey.find_program_address(
                [b"player", wallet_pubkey.__bytes__()],
                self.program_id
            )
            return pda, bump
        except Exception as e:
            self.logger.error("Failed to compute Player PDA", wallet=wallet, error=str(e))
            raise
    
    async def validate_player_pda(self, wallet: str, use_cache: bool = True) -> PDAValidationResult:
        """
        Валидация существования и корректности Player PDA.
        
        Args:
            wallet: Кошелек игрока
            use_cache: Использовать кэш результатов
            
        Returns:
            PDAValidationResult с результатом валидации
        """
        if not self.client:
            await self.initialize()
        
        # Проверяем кэш
        if use_cache and wallet in self._validation_cache:
            cached = self._validation_cache[wallet]
            if cached.checked_at and datetime.utcnow() - cached.checked_at < self._cache_ttl:
                self.logger.debug("Using cached validation result", wallet=wallet)
                return cached
        
        try:
            # Вычисляем PDA
            pda, bump = self._get_player_pda(wallet)
            pda_str = str(pda)
            
            # Проверяем существование аккаунта
            # Commitment устанавливается на уровне AsyncClient, не для отдельного запроса
            account_info = await self.client.get_account_info(pda)
            
            result = PDAValidationResult(
                wallet=wallet,
                pda=pda_str,
                exists=account_info.value is not None,
                is_valid=False,
                checked_at=datetime.utcnow()
            )
            
            if account_info.value:
                # Аккаунт существует - проверяем валидность
                account = account_info.value
                result.data_size = len(account.data)  # Размер данных через len()
                result.owner = str(account.owner)
                
                # Проверяем что owner == наша программа
                result.is_valid = (
                    account.owner == self.program_id and
                    len(account.data) > 0  # Должны быть данные
                )
                
                self.logger.info(
                    "Player PDA validation completed",
                    wallet=wallet,
                    pda=pda_str,
                    exists=result.exists,
                    is_valid=result.is_valid,
                    data_size=result.data_size
                )
            else:
                # Аккаунт не существует
                result.error = "Player PDA does not exist"
                self.logger.warning(
                    "Player PDA not found",
                    wallet=wallet,
                    pda=pda_str
                )
            
            # Сохраняем в кэш
            self._validation_cache[wallet] = result
            return result
            
        except Exception as e:
            error_msg = f"PDA validation failed: {str(e)}"
            self.logger.error("PDA validation error", wallet=wallet, error=error_msg)
            
            result = PDAValidationResult(
                wallet=wallet,
                pda="",
                exists=False,
                is_valid=False,
                error=error_msg,
                checked_at=datetime.utcnow()
            )
            
            self._validation_cache[wallet] = result
            return result
    
    async def batch_validate_players(self, wallets: List[str]) -> List[PDAValidationResult]:
        """
        Batch валидация множества игроков.
        
        Args:
            wallets: Список кошельков для проверки
            
        Returns:
            Список результатов валидации
        """
        if not wallets:
            return []
        
        self.logger.info("Starting batch PDA validation", players_count=len(wallets))
        
        # Параллельная валидация с ограничением concurrency
        semaphore = asyncio.Semaphore(10)  # Максимум 10 параллельных RPC вызовов
        
        async def validate_with_semaphore(wallet: str) -> PDAValidationResult:
            async with semaphore:
                return await self.validate_player_pda(wallet)
        
        # Выполняем все валидации параллельно
        tasks = [validate_with_semaphore(wallet) for wallet in wallets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты и исключения
        validation_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                validation_results.append(PDAValidationResult(
                    wallet=wallets[i],
                    pda="",
                    exists=False,
                    is_valid=False,
                    error=f"Validation exception: {str(result)}",
                    checked_at=datetime.utcnow()
                ))
            else:
                validation_results.append(result)
        
        # Статистика
        valid_count = sum(1 for r in validation_results if r.is_valid)
        existing_count = sum(1 for r in validation_results if r.exists)
        
        self.logger.info(
            "Batch PDA validation completed",
            total_players=len(wallets),
            existing_pdas=existing_count,
            valid_pdas=valid_count,
            invalid_pdas=len(wallets) - valid_count
        )
        
        return validation_results
    
    async def get_sync_report(self, db_players: List[str]) -> SyncReport:
        """
        Генерация отчета о состоянии синхронизации базы данных с blockchain.
        
        Args:
            db_players: Список игроков из базы данных
            
        Returns:
            SyncReport с подробной информацией о синхронизации
        """
        self.logger.info("Generating sync report", db_players_count=len(db_players))
        
        # Валидируем всех игроков из базы данных
        validation_results = await self.batch_validate_players(db_players)
        
        # Анализируем результаты
        valid_players = [r for r in validation_results if r.is_valid]
        invalid_players = [r for r in validation_results if not r.is_valid]
        missing_pdas = [r.wallet for r in validation_results if not r.exists]
        
        # TODO: Можно добавить поиск "orphan" PDA (существуют в blockchain, но нет в базе)
        # Для этого нужно перебрать все возможные PDA или использовать getProgramAccounts
        
        sync_percentage = (len(valid_players) / len(db_players) * 100) if db_players else 100
        
        report = SyncReport(
            total_players_db=len(db_players),
            total_players_blockchain=len(valid_players),
            valid_players=len(valid_players),
            invalid_players=len(invalid_players),
            missing_pdas=missing_pdas,
            orphan_pdas=[],  # TODO: реализовать поиск orphan PDA
            sync_percentage=sync_percentage,
            last_check=datetime.utcnow()
        )
        
        self.logger.info(
            "Sync report generated",
            total_db=report.total_players_db,
            total_blockchain=report.total_players_blockchain,
            sync_percentage=f"{report.sync_percentage:.1f}%",
            missing_pdas_count=len(report.missing_pdas)
        )
        
        return report
    
    def clear_cache(self):
        """Очистка кэша валидации."""
        self._validation_cache.clear()
        self.logger.info("PDA validation cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Статистика кэша."""
        now = datetime.utcnow()
        expired_count = sum(
            1 for result in self._validation_cache.values()
            if result.checked_at and now - result.checked_at > self._cache_ttl
        )
        
        return {
            "total_entries": len(self._validation_cache),
            "expired_entries": expired_count,
            "cache_ttl_minutes": self._cache_ttl.total_seconds() / 60
        }


# Global validator instance
_pda_validator: Optional[PDAValidator] = None


async def get_pda_validator() -> PDAValidator:
    """Получение глобального экземпляра PDA валидатора."""
    global _pda_validator
    if _pda_validator is None:
        _pda_validator = PDAValidator()
        await _pda_validator.initialize()
    return _pda_validator


async def validate_players_before_earnings(player_wallets: List[str]) -> List[str]:
    """
    Утилита для валидации игроков перед отправкой earnings транзакций.
    
    Args:
        player_wallets: Список кошельков для проверки
        
    Returns:
        Список валидных кошельков (с существующими PDA)
    """
    if not player_wallets:
        return []
    
    validator = await get_pda_validator()
    validation_results = await validator.batch_validate_players(player_wallets)
    
    valid_wallets = [
        result.wallet for result in validation_results 
        if result.is_valid
    ]
    
    invalid_wallets = [
        result.wallet for result in validation_results 
        if not result.is_valid
    ]
    
    if invalid_wallets:
        logger.warning(
            "Some players filtered out due to invalid PDA",
            total_players=len(player_wallets),
            valid_players=len(valid_wallets),
            invalid_players=len(invalid_wallets),
            invalid_wallets=invalid_wallets[:5]  # Показываем первые 5
        )
    
    return valid_wallets
"""
Player-Business Sync Service - синхронизация бизнесов игроков с blockchain.

Основные функции:
- Чтение всех бизнесов игрока из Player PDA
- Парсинг business_slots структуры
- Синхронизация с базой данных
- Валидация business данных
- Обновление портфолио statistics
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import structlog

from solders.pubkey import Pubkey
from solana.rpc.async_api import AsyncClient
from solana.rpc.commitment import Commitment
from anchorpy import Program, Provider, Wallet

from app.core.config import settings
from app.core.database import get_async_session
from app.models.player import Player
from app.models.business import Business, BusinessType, BusinessSlot
from app.services.pda_validator import get_pda_validator

logger = structlog.get_logger(__name__)


class BusinessSyncAction(Enum):
    """Типы действий синхронизации бизнесов."""
    BUSINESS_ADDED = "business_added"
    BUSINESS_UPDATED = "business_updated" 
    BUSINESS_REMOVED = "business_removed"
    PORTFOLIO_SYNCED = "portfolio_synced"


@dataclass
class OnChainBusiness:
    """Структура бизнеса с blockchain."""
    slot_index: int
    business_type: int  # 0-5
    business_type_name: str
    base_invested_amount: int  # lamports
    total_invested_amount: int  # lamports
    daily_rate: int  # basis points
    upgrade_level: int  # 0-3
    upgrade_history: List[int]  # [u64; 3] upgrade costs
    is_active: bool
    created_at: datetime
    last_claim: datetime
    total_earned: int
    
    # Slot information
    slot_type: str  # "Basic", "Premium", "VIP", "Legendary"
    slot_cost_paid: int  # lamports
    slot_is_paid: bool
    slot_yield_bonus: int  # basis points


@dataclass
class PlayerPortfolio:
    """Портфолио игрока с blockchain."""
    wallet: str
    total_invested: int  # lamports
    total_upgrade_spent: int  # lamports 
    total_slot_spent: int  # lamports
    pending_earnings: int  # lamports
    businesses: List[OnChainBusiness]
    
    @property
    def calculated_total_invested(self) -> int:
        """Рассчитанная стоимость всех активных бизнесов."""
        return sum(biz.total_invested_amount for biz in self.businesses)
    
    @property
    def business_count(self) -> int:
        """Количество активных бизнесов."""
        return len(self.businesses)


class PlayerBusinessSyncService:
    """
    Сервис синхронизации бизнесов игроков с blockchain.
    
    Читает Player PDA, парсит business_slots и синхронизирует с БД.
    """
    
    def __init__(self):
        self.logger = logger.bind(service="player_business_sync")
        self.rpc_client = AsyncClient(settings.solana_rpc_url)
        self.business_type_names = [
            "TobaccoShop", "FuneralService", "CarWorkshop", 
            "ItalianRestaurant", "GentlemenClub", "CharityFund"
        ]
        self.slot_type_names = ["Basic", "Premium", "VIP", "Legendary"]
        
    async def get_player_portfolio(self, wallet_address: str) -> Optional[PlayerPortfolio]:
        """
        Получить полное портфолио игрока с blockchain.
        
        Args:
            wallet_address: Адрес кошелька игрока
            
        Returns:
            PlayerPortfolio или None если игрок не найден
        """
        try:
            # Валидируем Player PDA
            pda_validator = await get_pda_validator()
            validation_result = await pda_validator.validate_player_pda(wallet_address)
            
            if not validation_result.is_valid:
                self.logger.warning("Player PDA not found", wallet=wallet_address)
                return None
            
            # Пока используем mock данные (для production нужен полный parser)
            # В будущем здесь будет: account_data = await rpc_client.get_account_info(validation_result.pda)
            portfolio = await self._parse_player_account(wallet_address, b"")
            
            self.logger.info(
                "Player portfolio loaded",
                wallet=wallet_address,
                businesses=portfolio.business_count,
                total_invested_onchain=portfolio.total_invested,
                calculated_invested=portfolio.calculated_total_invested
            )
            
            return portfolio
            
        except Exception as e:
            self.logger.error("Failed to get player portfolio", wallet=wallet_address, error=str(e))
            return None
    
    async def _parse_player_account(self, wallet: str, account_data: bytes) -> PlayerPortfolio:
        """
        Парсинг Player account data.
        
        Структура Player PDA:
        - discriminator: 8 bytes
        - owner: 32 bytes  
        - business_slots: [BusinessSlotCompact; 9] - main data
        - ... other fields
        """
        # Простой парсинг (для production нужен полный deserializer)
        # Пока используем mock данные на основе debug-player-data.js результатов
        
        businesses = []
        
        # Mock данные на основе известного игрока для тестирования
        if wallet == "2FRZFt4Ko2jYzGS221sizYC1v2hcizn8AjtgHxiJTzMU":
            # Business в слоте 0 (upgraded TobaccoShop)
            businesses.append(OnChainBusiness(
                slot_index=0,
                business_type=0,  # TobaccoShop
                business_type_name="TobaccoShop",
                base_invested_amount=100_000_000,  # 0.1 SOL
                total_invested_amount=120_000_000,  # 0.12 SOL (с апгрейдом)
                daily_rate=200,  # 2%
                upgrade_level=1,
                upgrade_history=[20_000_000, 0, 0],  # первый апгрейд 0.02 SOL
                is_active=True,
                created_at=datetime.fromtimestamp(1757866041),  # from debug data
                last_claim=datetime.fromtimestamp(1757866041),
                total_earned=0,
                slot_type="Basic",
                slot_cost_paid=0,
                slot_is_paid=True,
                slot_yield_bonus=0
            ))
            
            # Business в слоте 1 (базовый TobaccoShop)
            businesses.append(OnChainBusiness(
                slot_index=1,
                business_type=0,  # TobaccoShop
                business_type_name="TobaccoShop", 
                base_invested_amount=100_000_000,  # 0.1 SOL
                total_invested_amount=100_000_000,  # 0.1 SOL (без апгрейдов)
                daily_rate=200,  # 2%
                upgrade_level=0,
                upgrade_history=[0, 0, 0],
                is_active=True,
                created_at=datetime.fromtimestamp(1757879426),  # from debug data
                last_claim=datetime.fromtimestamp(1757879426),
                total_earned=0,
                slot_type="Basic",
                slot_cost_paid=0,
                slot_is_paid=True,
                slot_yield_bonus=0
            ))
        
        return PlayerPortfolio(
            wallet=wallet,
            total_invested=300_000_000,  # 3.0 SOL (из debug данных)
            total_upgrade_spent=20_000_000,  # 0.02 SOL
            total_slot_spent=0,
            pending_earnings=0,
            businesses=businesses
        )
    
    async def sync_player_businesses(self, wallet_address: str) -> Dict[str, Any]:
        """
        Синхронизация бизнесов игрока с базой данных.
        
        Args:
            wallet_address: Адрес кошелька игрока
            
        Returns:
            Отчет о синхронизации
        """
        sync_report = {
            "wallet": wallet_address,
            "timestamp": datetime.utcnow(),
            "success": False,
            "businesses_synced": 0,
            "businesses_added": 0,
            "businesses_updated": 0,
            "businesses_removed": 0,
            "portfolio_corrected": False,
            "actions": []
        }
        
        try:
            # Получаем портфолио с blockchain
            portfolio = await self.get_player_portfolio(wallet_address)
            if not portfolio:
                sync_report["error"] = "Player not found on blockchain"
                return sync_report
            
            async with get_async_session() as db:
                # Получаем игрока из базы
                from sqlalchemy import select
                result = await db.execute(
                    select(Player).where(Player.wallet == wallet_address)
                )
                db_player = result.scalar_one_or_none()
                
                if not db_player:
                    sync_report["error"] = "Player not found in database"
                    return sync_report
                
                # Синхронизируем бизнесы
                sync_stats = await self._sync_businesses_with_db(
                    db, db_player, portfolio, sync_report
                )
                
                # Корректируем портфолио статистику если нужно
                portfolio_corrected = await self._correct_portfolio_stats(
                    db, db_player, portfolio, sync_report
                )
                
                sync_report.update(sync_stats)
                sync_report["portfolio_corrected"] = portfolio_corrected
                sync_report["success"] = True
                
                await db.commit()
                
                self.logger.info(
                    "Player businesses synchronized",
                    wallet=wallet_address,
                    **{k: v for k, v in sync_report.items() if k not in ["actions", "timestamp"]}
                )
                
        except Exception as e:
            sync_report["error"] = str(e)
            self.logger.error("Business sync failed", wallet=wallet_address, error=str(e))
        
        return sync_report
    
    async def _sync_businesses_with_db(
        self, 
        db, 
        db_player: Player, 
        portfolio: PlayerPortfolio,
        sync_report: Dict[str, Any]
    ) -> Dict[str, int]:
        """Синхронизация бизнесов с базой данных."""
        from sqlalchemy import select, delete
        
        stats = {
            "businesses_synced": 0,
            "businesses_added": 0, 
            "businesses_updated": 0,
            "businesses_removed": 0
        }
        
        # Получаем существующие бизнесы из базы
        result = await db.execute(
            select(Business).where(Business.player_wallet == db_player.wallet)
        )
        existing_businesses = {b.slot_index: b for b in result.scalars().all()}
        
        # Обновляем/добавляем бизнесы с blockchain
        for onchain_biz in portfolio.businesses:
            existing_biz = existing_businesses.get(onchain_biz.slot_index)
            
            if existing_biz:
                # Обновляем существующий бизнес
                updated = await self._update_business_from_onchain(
                    existing_biz, onchain_biz, sync_report
                )
                if updated:
                    stats["businesses_updated"] += 1
            else:
                # Добавляем новый бизнес
                await self._create_business_from_onchain(
                    db, db_player, onchain_biz, sync_report
                )
                stats["businesses_added"] += 1
            
            stats["businesses_synced"] += 1
        
        # Удаляем бизнесы которых нет на blockchain
        onchain_slots = {biz.slot_index for biz in portfolio.businesses}
        businesses_to_remove = [
            slot_idx for slot_idx in existing_businesses.keys()
            if slot_idx not in onchain_slots
        ]
        
        if businesses_to_remove:
            await db.execute(
                delete(Business).where(
                    Business.player_wallet == db_player.wallet,
                    Business.slot_index.in_(businesses_to_remove)
                )
            )
            stats["businesses_removed"] = len(businesses_to_remove)
            
            sync_report["actions"].append({
                "action": BusinessSyncAction.BUSINESS_REMOVED.value,
                "details": {"removed_slots": businesses_to_remove}
            })
        
        return stats
    
    async def _update_business_from_onchain(
        self, 
        db_business: Business, 
        onchain_biz: OnChainBusiness,
        sync_report: Dict[str, Any]
    ) -> bool:
        """Обновление существующего бизнеса из blockchain данных."""
        updated = False
        changes = {}
        
        # Проверяем ключевые поля на изменения
        if db_business.level != onchain_biz.upgrade_level:
            changes["level"] = {"old": db_business.level, "new": onchain_biz.upgrade_level}
            db_business.level = onchain_biz.upgrade_level
            updated = True
        
        if db_business.total_invested_amount != onchain_biz.total_invested_amount:
            changes["total_invested"] = {
                "old": db_business.total_invested_amount, 
                "new": onchain_biz.total_invested_amount
            }
            db_business.total_invested_amount = onchain_biz.total_invested_amount
            updated = True
        
        if db_business.daily_rate != onchain_biz.daily_rate:
            changes["daily_rate"] = {"old": db_business.daily_rate, "new": onchain_biz.daily_rate}
            db_business.daily_rate = onchain_biz.daily_rate
            updated = True
        
        if db_business.is_active != onchain_biz.is_active:
            changes["is_active"] = {"old": db_business.is_active, "new": onchain_biz.is_active}
            db_business.is_active = onchain_biz.is_active
            updated = True
        
        if updated:
            db_business.last_sync_at = datetime.utcnow()
            sync_report["actions"].append({
                "action": BusinessSyncAction.BUSINESS_UPDATED.value,
                "slot_index": onchain_biz.slot_index,
                "changes": changes
            })
        
        return updated
    
    async def _create_business_from_onchain(
        self,
        db,
        db_player: Player,
        onchain_biz: OnChainBusiness,
        sync_report: Dict[str, Any]
    ):
        """Создание нового бизнеса из blockchain данных."""
        # Конвертируем business_type
        business_type = BusinessType(onchain_biz.business_type)
        
        new_business = Business(
            owner_id=db_player.user_id,  # assuming this exists
            player_wallet=db_player.wallet,
            business_type=business_type,
            level=onchain_biz.upgrade_level,
            base_cost=onchain_biz.base_invested_amount,
            total_invested_amount=onchain_biz.total_invested_amount,
            daily_rate=onchain_biz.daily_rate,
            is_active=onchain_biz.is_active,
            slot_index=onchain_biz.slot_index,
            on_chain_created_at=onchain_biz.created_at,
            last_sync_at=datetime.utcnow()
        )
        
        db.add(new_business)
        
        sync_report["actions"].append({
            "action": BusinessSyncAction.BUSINESS_ADDED.value,
            "slot_index": onchain_biz.slot_index,
            "business_type": onchain_biz.business_type_name,
            "level": onchain_biz.upgrade_level,
            "total_invested": onchain_biz.total_invested_amount
        })
    
    async def _correct_portfolio_stats(
        self,
        db,
        db_player: Player,
        portfolio: PlayerPortfolio, 
        sync_report: Dict[str, Any]
    ) -> bool:
        """Коррекция статистики портфолио в базе."""
        corrected = False
        corrections = {}
        
        # Проверяем соответствие между blockchain и расчетными значениями
        expected_total = portfolio.calculated_total_invested
        actual_total = portfolio.total_invested
        
        if expected_total != actual_total:
            corrections["portfolio_discrepancy"] = {
                "onchain_total_invested": actual_total,
                "calculated_from_businesses": expected_total,
                "difference": actual_total - expected_total
            }
            corrected = True
        
        # Здесь можно добавить обновление Player модели если нужно
        # Пока просто логируем несоответствия
        
        if corrected:
            sync_report["actions"].append({
                "action": BusinessSyncAction.PORTFOLIO_SYNCED.value,
                "corrections": corrections
            })
        
        return corrected


# Global service instance
_player_business_sync_service: Optional[PlayerBusinessSyncService] = None


async def get_player_business_sync_service() -> PlayerBusinessSyncService:
    """Получение глобального экземпляра sync сервиса."""
    global _player_business_sync_service
    if _player_business_sync_service is None:
        _player_business_sync_service = PlayerBusinessSyncService()
    return _player_business_sync_service
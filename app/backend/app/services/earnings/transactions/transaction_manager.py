"""
Transaction manager for earnings updates.
"""

import asyncio
from typing import List, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import structlog

from app.services.transaction_service import get_transaction_service
from app.services.earnings.core.types import PlayerAccountData
from app.services.signature_processor import queue_admin_transaction_for_processing


class EarningsUpdateResult(Enum):
    """Result types for earnings update attempts."""
    SUCCESS = "success"
    EARNINGS_NOT_DUE = "earnings_not_due"  # Normal case - retry later
    FAILED = "failed"  # Real failure


@dataclass
class EarningsUpdateResponse:
    """Response from earnings update attempt."""
    result: EarningsUpdateResult
    signature: str = ""
    error_message: str = ""


logger = structlog.get_logger(__name__)


class TransactionManager:
    """
    Manages earnings update transactions.
    """
    
    def __init__(self, stats, failed_player_retry_hours: int = 1):
        """Initialize the transaction manager."""
        self.stats = stats
        self.failed_player_retry_hours = failed_player_retry_hours
        self.logger = logger.bind(service="transaction_manager")
        
        # Failed players tracking (for retry logic)
        self._failed_players: Set[str] = set()
        # Set last cleanup to far past to force cleanup on first run
        self._last_failure_cleanup = datetime.utcnow() - timedelta(hours=failed_player_retry_hours + 1)
        
    def cleanup_failed_players(self):
        """Remove old failed players from retry blacklist."""
        current_time = datetime.utcnow()
        if current_time - self._last_failure_cleanup > timedelta(hours=self.failed_player_retry_hours):
            old_count = len(self._failed_players)
            self._failed_players.clear()
            self._last_failure_cleanup = current_time
            
            if old_count > 0:
                self.logger.info(
                    "🧹 Cleaned up failed players blacklist",
                    old_count=old_count,
                    retry_hours=self.failed_player_retry_hours
                )
            else:
                self.logger.info(
                    "🧹 Failed players cleanup - cache was already empty",
                    retry_hours=self.failed_player_retry_hours
                )
    
    async def send_earnings_update(self, wallet: str) -> EarningsUpdateResponse:
        """
        Send permissionless earnings update transaction for a player.
        
        NEW ARCHITECTURE: 
        1. Send transaction to blockchain
        2. Queue signature for processing via SignatureProcessor
        3. Return detailed result (success/not_due/failed)
        """
        try:
            # Get transaction service
            transaction_service = await get_transaction_service()
            
            # Send permissionless update_earnings transaction
            result = await transaction_service.update_player_earnings_permissionless(wallet)
            
            if result.success:
                self.logger.info(
                    "📡 Admin earnings update transaction sent",
                    wallet=wallet,
                    signature=result.signature[:20] + "..."
                )
                
                # Queue signature for processing using our new architecture
                queued = await queue_admin_transaction_for_processing(
                    signature=result.signature,
                    admin_wallet=wallet,  # The player receiving the update
                    operation_type="earnings_update",
                    context={"target_wallet": wallet}
                )
                
                if queued:
                    self.logger.info(
                        "✅ Admin transaction queued for processing",
                        wallet=wallet,
                        signature=result.signature[:20] + "..."
                    )
                    return EarningsUpdateResponse(
                        result=EarningsUpdateResult.SUCCESS,
                        signature=result.signature
                    )
                else:
                    self.logger.error(
                        "❌ Failed to queue admin transaction",
                        wallet=wallet,
                        signature=result.signature[:20] + "..."
                    )
                    return EarningsUpdateResponse(
                        result=EarningsUpdateResult.FAILED,
                        error_message="Failed to queue transaction for processing"
                    )
                    
            else:
                error_msg = result.error or "Unknown error"
                
                # 🎯 КЛЮЧЕВАЯ ЛОГИКА: Проверяем EarningsNotDue
                if "EarningsNotDue" in error_msg or "0x177e" in error_msg:
                    self.logger.info(
                        "⏰ EarningsNotDue (normal) - will retry later",
                        wallet=wallet
                    )
                    return EarningsUpdateResponse(
                        result=EarningsUpdateResult.EARNINGS_NOT_DUE,
                        error_message=error_msg
                    )
                else:
                    self.logger.error(
                        "❌ Earnings update transaction failed",
                        wallet=wallet,
                        error=error_msg
                    )
                    return EarningsUpdateResponse(
                        result=EarningsUpdateResult.FAILED,
                        error_message=error_msg
                    )
                
        except Exception as e:
            error_msg = str(e)
            
            # 🎯 КЛЮЧЕВАЯ ЛОГИКА: Проверяем EarningsNotDue в exceptions
            if "EarningsNotDue" in error_msg or "0x177e" in error_msg:
                self.logger.info(
                    "⏰ EarningsNotDue exception (normal) - will retry later",
                    wallet=wallet
                )
                return EarningsUpdateResponse(
                    result=EarningsUpdateResult.EARNINGS_NOT_DUE,
                    error_message=error_msg
                )
            else:
                self.logger.error(
                    "❌ Failed to send earnings update",
                    wallet=wallet,
                    error=error_msg
                )
                return EarningsUpdateResponse(
                    result=EarningsUpdateResult.FAILED,
                    error_message=error_msg
                )
    
    async def process_earnings_updates(self, players_needing_update: List[PlayerAccountData]):
        """Process earnings updates for all players who need them."""
        successful_updates = 0
        failed_updates = 0
        
        # Process sequentially to avoid overwhelming RPC
        for player_data in players_needing_update:
            try:
                # Skip recently failed players
                if player_data.wallet in self._failed_players:
                    self.logger.debug(
                        "Skipping recently failed player",
                        wallet=player_data.wallet
                    )
                    continue
                
                success = await self.send_earnings_update(player_data.wallet)
                
                if success:
                    successful_updates += 1
                else:
                    failed_updates += 1
                    self._failed_players.add(player_data.wallet)
                
                # Brief pause between transactions
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(
                    "Unexpected error processing player update",
                    wallet=player_data.wallet,
                    error=str(e)
                )
                failed_updates += 1
                self._failed_players.add(player_data.wallet)
        
        self.stats.successful_updates = successful_updates
        self.stats.failed_updates = failed_updates
        
        self.logger.info(
            "Earnings updates completed",
            successful=successful_updates,
            failed=failed_updates,
            success_rate=f"{(successful_updates / len(players_needing_update) * 100):.1f}%" if players_needing_update else "0%"
        )
    
    async def update_single_player_earnings(self, wallet: str, max_retries: int = 3) -> EarningsUpdateResponse:
        """
        🔄 Обновить earnings для одного игрока с retry логикой
        
        Args:
            wallet: Кошелек игрока 
            max_retries: Максимум попыток (по умолчанию 3)
            
        Returns:
            EarningsUpdateResponse: Детальный результат последней попытки
        """
        last_response = None
        
        for attempt in range(max_retries):
            try:
                response = await self.send_earnings_update(wallet)
                last_response = response
                
                if response.result == EarningsUpdateResult.SUCCESS:
                    self.logger.info(f"✅ Single player earnings updated: {wallet} (attempt {attempt + 1})")
                    # Убираем из failed_players если был там
                    self._failed_players.discard(wallet)
                    return response
                elif response.result == EarningsUpdateResult.EARNINGS_NOT_DUE:
                    self.logger.info(f"⏰ EarningsNotDue for {wallet} (attempt {attempt + 1}) - normal, will retry")
                    # Для EarningsNotDue продолжаем retry
                else:
                    # Real failure - не retry
                    self.logger.warning(f"❌ Real failure for {wallet} (attempt {attempt + 1}): {response.error_message}")
                    self._failed_players.add(wallet)
                    return response
                    
            except Exception as e:
                self.logger.error(f"🚨 Error on attempt {attempt + 1} for {wallet}: {e}")
                last_response = EarningsUpdateResponse(
                    result=EarningsUpdateResult.FAILED,
                    error_message=str(e)
                )
            
            # Exponential backoff между попытками
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                self.logger.info(f"🔄 Waiting {wait_time}s before retry {attempt + 2} for {wallet}")
                await asyncio.sleep(wait_time)
        
        # Все попытки провалились или были EarningsNotDue
        if last_response and last_response.result == EarningsUpdateResult.EARNINGS_NOT_DUE:
            self.logger.info(f"⏰ Still EarningsNotDue for {wallet} after {max_retries} attempts - normal")
        else:
            self.logger.error(f"❌ Failed to update {wallet} after {max_retries} attempts")
            self._failed_players.add(wallet)
        
        return last_response or EarningsUpdateResponse(
            result=EarningsUpdateResult.FAILED,
            error_message=f"Failed after {max_retries} attempts"
        )

    async def process_all_players_earnings_updates(self, active_wallets: List[str]):
        """
        🚀 RATE-LIMITED BATCH ARCHITECTURE: RPC-friendly earnings updates.
        
        Решает проблемы масштабирования:
        1. Rate limiting: учитывает RPC план (10 RPS free, 50 RPS paid)
        2. Batch транзакции: до 5 игроков в одной транзакции  
        3. Резерв RPS: для других операций (не все RPS на earnings)
        4. Retry логика: для EarningsNotDue с exponential backoff
        
        Args:
            active_wallets: List of all active player wallet addresses
        """
        import os
        import math
        
        # Настройки rate limiting
        total_rpc_rate = int(os.getenv('RPC_RATE_LIMIT', '10'))
        earnings_percentage = int(os.getenv('EARNINGS_RESERVE_PERCENTAGE', '60'))
        earnings_max_rps = min(
            int(os.getenv('EARNINGS_MAX_RPS', '6')),
            math.floor(total_rpc_rate * earnings_percentage / 100)
        )
        
        # Настройки batch операций
        batch_enabled = os.getenv('EARNINGS_BATCH_ENABLED', 'true').lower() == 'true'
        batch_size = int(os.getenv('EARNINGS_BATCH_SIZE', '5'))
        retry_attempts = 3
        
        # Подготовка
        successful_updates = 0
        failed_updates = 0
        retries_needed = []
        start_time = datetime.utcnow()
        
        # Фильтрация кошельков (убираем недавно failed)
        valid_wallets = [w for w in active_wallets if w not in self._failed_players]
        
        self.logger.info(
            "🚀 Starting RATE-LIMITED BATCH earnings updates",
            total_players=len(active_wallets),
            valid_players=len(valid_wallets),
            skipped_failed=len(active_wallets) - len(valid_wallets),
            earnings_max_rps=earnings_max_rps,
            batch_enabled=batch_enabled,
            batch_size=batch_size if batch_enabled else 1,
            strategy="rate_limited_batch_with_retry"
        )
        
        if not valid_wallets:
            self.logger.info("No valid wallets to process")
            return
        
        # Фаза 1: Rate-limited batch отправка
        self.logger.info("🎯 Phase 1: Rate-limited batch sending")
        
        # Разделяем игроков на батчи
        if batch_enabled:
            batches = [valid_wallets[i:i + batch_size] for i in range(0, len(valid_wallets), batch_size)]
        else:
            batches = [[wallet] for wallet in valid_wallets]  # По одному игроку
        
        total_transactions = len(batches)
        interval_between_requests = 1.0 / earnings_max_rps  # Секунд между запросами
        
        self.logger.info(
            "📊 Batch distribution",
            total_batches=total_transactions,
            interval_between_requests=f"{interval_between_requests:.2f}s",
            estimated_time=f"{total_transactions * interval_between_requests:.1f}s"
        )
        
        # Получаем transaction service
        transaction_service = await get_transaction_service()
        
        for i, batch_wallets in enumerate(batches):
            try:
                # Rate limiting: ждем между запросами
                if i > 0:
                    await asyncio.sleep(interval_between_requests)
                
                # Отправляем batch транзакцию
                if batch_enabled and len(batch_wallets) > 1:
                    result = await transaction_service.update_players_earnings_batch_transaction(batch_wallets)
                    
                    if result.success:
                        successful_updates += len(batch_wallets)
                        
                        # Добавляем batch транзакцию в очередь SignatureProcessor
                        queued = await queue_admin_transaction_for_processing(
                            signature=result.signature,
                            admin_wallet="batch_admin",
                            operation_type="batch_earnings_update",
                            context={"batch_wallets": batch_wallets, "batch_size": len(batch_wallets)}
                        )
                        
                        self.logger.info(
                            "✅ Batch transaction sent",
                            batch_index=f"{i+1}/{total_transactions}",
                            players_in_batch=len(batch_wallets),
                            signature=result.signature[:20] + "...",
                            queued_for_processing=queued
                        )
                    else:
                        error_msg = result.error or "Unknown error"
                        
                        # Проверяем EarningsNotDue для retry (НЕ считаем failure)
                        if "EarningsNotDue" in error_msg:
                            retries_needed.extend(batch_wallets)
                            self.logger.info("⏰ Batch EarningsNotDue (normal), will retry later", batch_wallets=batch_wallets)
                        else:
                            # Только real failures считаем failed
                            failed_updates += len(batch_wallets)
                            for wallet in batch_wallets:
                                self._failed_players.add(wallet)
                            self.logger.warning("❌ Batch transaction failed", error=error_msg)
                
                else:
                    # Single transaction (не batch)
                    wallet = batch_wallets[0]
                    update_response = await self.send_earnings_update(wallet)
                    
                    if update_response.result == EarningsUpdateResult.SUCCESS:
                        successful_updates += 1
                        self.logger.info(
                            "✅ Single transaction sent",
                            wallet=wallet,
                            batch_index=f"{i+1}/{total_transactions}",
                            signature=update_response.signature[:20] + "..."
                        )
                    elif update_response.result == EarningsUpdateResult.EARNINGS_NOT_DUE:
                        # Нормальная ситуация - добавляем для retry
                        retries_needed.append(wallet)
                        self.logger.info(
                            "⏰ Single EarningsNotDue (normal), will retry later",
                            wallet=wallet,
                            batch_index=f"{i+1}/{total_transactions}"
                        )
                    else:
                        # Real failure
                        failed_updates += 1
                        self._failed_players.add(wallet)
                        self.logger.warning(
                            "❌ Single transaction failed",
                            wallet=wallet,
                            error=update_response.error_message
                        )
                        
            except Exception as e:
                error_msg = str(e)
                
                # Проверяем EarningsNotDue для retry (НЕ считаем failure)
                if "EarningsNotDue" in error_msg or "0x177e" in error_msg:
                    retries_needed.extend(batch_wallets)
                    self.logger.info("⏰ Exception EarningsNotDue (normal), will retry later", batch_wallets=batch_wallets)
                else:
                    # Только real failures считаем failed
                    failed_updates += len(batch_wallets)
                    for wallet in batch_wallets:
                        self._failed_players.add(wallet)
                    self.logger.error("❌ Batch processing error", error=error_msg)
        
        phase1_time = (datetime.utcnow() - start_time).total_seconds()
        
        self.logger.info(
            "🎯 Phase 1 completed",
            successful=successful_updates,
            failed=failed_updates,
            retries_needed=len(retries_needed),
            time_taken=f"{phase1_time:.2f}s",
            rps_used=f"{total_transactions / phase1_time:.1f} RPS" if phase1_time > 0 else "instant"
        )
        
        # Фаза 2: Retry для EarningsNotDue
        if retries_needed:
            self.logger.info(
                "🔄 Phase 2: Retry EarningsNotDue transactions",
                retry_wallets=len(retries_needed)
            )
            
            for attempt in range(retry_attempts):
                if not retries_needed:
                    break
                    
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                self.logger.info(
                    f"⏱️ Retry attempt {attempt + 1}, waiting {wait_time}s",
                    wallets_to_retry=len(retries_needed)
                )
                await asyncio.sleep(wait_time)
                
                # Retry с более консервативным rate limiting (50% от основного)
                retry_interval = interval_between_requests * 2
                retry_batches = [retries_needed[i:i + batch_size] for i in range(0, len(retries_needed), batch_size)]
                
                new_retries = []
                
                for j, retry_batch in enumerate(retry_batches):
                    if j > 0:
                        await asyncio.sleep(retry_interval)
                    
                    try:
                        if batch_enabled and len(retry_batch) > 1:
                            result = await transaction_service.update_players_earnings_batch_transaction(retry_batch)
                            
                            if result.success:
                                successful_updates += len(retry_batch)
                                self.logger.info(f"✅ Retry batch successful: {len(retry_batch)} players")
                            else:
                                if "EarningsNotDue" in (result.error or ""):
                                    new_retries.extend(retry_batch)
                                else:
                                    failed_updates += len(retry_batch)
                        else:
                            wallet = retry_batch[0]
                            update_response = await self.send_earnings_update(wallet)
                            
                            if update_response.result == EarningsUpdateResult.SUCCESS:
                                successful_updates += 1
                                self.logger.info(f"✅ Retry successful for {wallet}")
                            elif update_response.result == EarningsUpdateResult.EARNINGS_NOT_DUE:
                                # Все еще not due - retry еще раз 
                                new_retries.append(wallet)
                                self.logger.info(f"⏰ Retry still EarningsNotDue for {wallet}")
                            else:
                                # Real failure - не retry больше
                                failed_updates += 1
                                self._failed_players.add(wallet)
                                self.logger.warning(f"❌ Retry failed for {wallet}: {update_response.error_message}")
                                
                    except Exception as e:
                        if "EarningsNotDue" in str(e):
                            new_retries.extend(retry_batch)
                        else:
                            failed_updates += len(retry_batch)
                
                retries_needed = new_retries
                
                if not retries_needed:
                    self.logger.info("🎉 All retries successful!")
                    break
        
        total_time = (datetime.utcnow() - start_time).total_seconds()
        
        self.stats.successful_updates = successful_updates
        self.stats.failed_updates = failed_updates
        
        # Расчет эффективности
        total_rpc_calls = total_transactions + (len(retries_needed) if retries_needed else 0)
        actual_rps = total_rpc_calls / total_time if total_time > 0 else 0
        players_per_rpc = len(active_wallets) / total_rpc_calls if total_rpc_calls > 0 else 0
        
        self.logger.info(
            "🏁 RATE-LIMITED BATCH earnings completed",
            successful=successful_updates,
            failed=failed_updates,
            still_not_due=len(retries_needed),
            success_rate=f"{(successful_updates / len(active_wallets) * 100):.1f}%" if active_wallets else "0%",
            total_time=f"{total_time:.2f}s",
            rpc_calls_made=total_rpc_calls,
            actual_rps=f"{actual_rps:.2f}",
            rpc_efficiency=f"{players_per_rpc:.1f} players/RPC",
            rpc_savings=f"{((len(active_wallets) - total_rpc_calls) / len(active_wallets) * 100):.1f}%" if batch_enabled else "0%"
        )

    @property
    def failed_players(self) -> Set[str]:
        """Get set of failed players."""
        return self._failed_players
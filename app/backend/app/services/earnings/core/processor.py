"""
Main ResilientEarningsProcessor using modular components.
"""

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from dataclasses import asdict
import structlog

from app.services.adaptive_rpc_client import get_adaptive_rpc_client, AdaptiveRpcClient
from .types import ProcessorStatus, ProcessorStats
from ..database import PlayerRepository
from ..transactions import TransactionManager


logger = structlog.get_logger(__name__)


class ResilientEarningsProcessor:
    """
    🚀 NEW ARCHITECTURE: Send-first earnings processor.
    
    Architecture:
    1. Get all active player wallets from database
    2. Send update_earnings transactions to ALL players
    3. SignatureProcessor handles transaction events and updates database
    4. Simple, reliable, event-driven architecture
    """
    
    def __init__(self):
        self.logger = logger.bind(service="resilient_earnings_processor")
        
        # Load configuration
        self.batch_size_accounts = int(os.getenv('BATCH_SIZE_ACCOUNTS', '500'))
        self.max_concurrent_updates = int(os.getenv('MAX_CONCURRENT_UPDATES', '50'))
        self.timeout_minutes = int(os.getenv('SCHEDULER_TIMEOUT_MINUTES', '30'))
        self.retry_delay_base = int(os.getenv('RETRY_DELAY_BASE', '2'))
        self.failed_player_retry_hours = int(os.getenv('FAILED_PLAYER_RETRY_HOURS', '1'))
        
        # State
        self.status = ProcessorStatus.IDLE
        self.stats = ProcessorStats()
        self.rpc_client: Optional[AdaptiveRpcClient] = None
        
        # Components
        self.player_repository = PlayerRepository()
        self.transaction_manager: Optional[TransactionManager] = None
        
        self.logger.info(
            "ResilientEarningsProcessor initialized",
            batch_size=self.batch_size_accounts,
            concurrent_updates=self.max_concurrent_updates,
            timeout_minutes=self.timeout_minutes
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
    
    async def initialize(self):
        """Initialize the processor."""
        try:
            self.rpc_client = await get_adaptive_rpc_client()
            
            # Initialize components
            self.transaction_manager = TransactionManager(self.stats, self.failed_player_retry_hours)
            
            self.logger.info("Earnings processor initialized successfully")
        except Exception as e:
            self.logger.error("Failed to initialize earnings processor", error=str(e))
            raise
    
    async def shutdown(self):
        """Shutdown the processor."""
        self.logger.info("Earnings processor shutting down")
    
    async def run_daily_earnings_process(self) -> ProcessorStats:
        """
        Run the complete daily earnings process.
        
        Returns:
            ProcessorStats with detailed processing information
        """
        if self.status != ProcessorStatus.IDLE:
            raise Exception(f"Processor is already running with status: {self.status}")
        
        self.status = ProcessorStatus.RUNNING
        self.stats = ProcessorStats(start_time=datetime.now(timezone.utc))
        
        try:
            self.logger.info("Starting daily earnings process with business sync")
            
            # Step 1: Cleanup failed players blacklist
            self.transaction_manager.cleanup_failed_players()
            
            # Step 2: Get all active player wallets
            active_wallets = await self.player_repository.get_active_player_wallets()
            self.stats.total_players_found = len(active_wallets)
            
            if not active_wallets:
                self.logger.info("No active players found")
                self.status = ProcessorStatus.COMPLETED
                return self.stats
            
            # 🔥 НОВЫЙ ШАГ: Синхронизация business данных с blockchain
            self.logger.info("🔄 Step 2.1: Synchronizing business data with blockchain")
            sync_start_time = datetime.now(timezone.utc)
            
            from app.services.player_business_sync import get_player_business_sync_service
            
            business_sync_service = await get_player_business_sync_service()
            sync_successful = 0
            sync_failed = 0
            total_businesses_synced = 0
            total_businesses_added = 0
            total_businesses_updated = 0
            total_portfolio_corrections = 0
            
            # Batch sync всех активных игроков
            for wallet in active_wallets:
                try:
                    sync_report = await business_sync_service.sync_player_businesses(wallet)
                    if sync_report.get("success", False):
                        sync_successful += 1
                        
                        # Собираем статистику
                        total_businesses_synced += sync_report.get("businesses_synced", 0)
                        total_businesses_added += sync_report.get("businesses_added", 0)
                        total_businesses_updated += sync_report.get("businesses_updated", 0)
                        if sync_report.get("portfolio_corrected", False):
                            total_portfolio_corrections += 1
                        
                        # Логируем важные изменения
                        if sync_report.get("businesses_synced", 0) > 0:
                            self.logger.info(
                                "✅ Business sync completed",
                                wallet=wallet,
                                businesses_synced=sync_report.get("businesses_synced", 0),
                                businesses_added=sync_report.get("businesses_added", 0),
                                businesses_updated=sync_report.get("businesses_updated", 0),
                                portfolio_corrected=sync_report.get("portfolio_corrected", False)
                            )
                    else:
                        sync_failed += 1
                        error = sync_report.get("error", "Unknown error")
                        self.logger.warning("⚠️ Business sync failed", wallet=wallet, error=error)
                        
                except Exception as sync_error:
                    sync_failed += 1
                    self.logger.error("❌ Business sync error", wallet=wallet, error=str(sync_error))
            
            sync_duration = (datetime.now(timezone.utc) - sync_start_time).total_seconds()
            
            # Сохраняем статистику в ProcessorStats
            self.stats.business_sync_successful = sync_successful
            self.stats.business_sync_failed = sync_failed
            self.stats.business_sync_duration = sync_duration
            self.stats.businesses_synced_total = total_businesses_synced
            self.stats.businesses_added_total = total_businesses_added
            self.stats.businesses_updated_total = total_businesses_updated
            self.stats.portfolio_corrections_total = total_portfolio_corrections
            
            self.logger.info(
                "🔄 Business synchronization completed",
                total_players=len(active_wallets),
                sync_successful=sync_successful,
                sync_failed=sync_failed,
                sync_rate=f"{(sync_successful / len(active_wallets) * 100):.1f}%",
                sync_duration=f"{sync_duration:.2f}s",
                businesses_synced=total_businesses_synced,
                businesses_added=total_businesses_added,
                businesses_updated=total_businesses_updated,
                portfolio_corrections=total_portfolio_corrections
            )
            
            # Step 3: Send update_earnings transactions to ALL players
            self.logger.info("📡 Step 3: Sending update_earnings transactions to ALL active players")
            self.stats.players_needing_update = len(active_wallets)  # All players get updates
            
            self.logger.info(
                "Processing ALL players for earnings updates",
                total_players=len(active_wallets),
                strategy="blockchain_sync_then_send_earnings",
                business_sync_rate=f"{(sync_successful / len(active_wallets) * 100):.1f}%"
            )
            
            # Send transactions to ALL active players without blockchain reads
            await self.transaction_manager.process_all_players_earnings_updates(active_wallets)
            
            # Transaction signatures will be processed by SignatureProcessor
            # which will handle EarningsUpdated events and update the database
            
            # No need to sync database here - SignatureProcessor handles it through events
            
            # Complete
            self.stats.end_time = datetime.now(timezone.utc)
            self.stats.total_processing_time = (self.stats.end_time - self.stats.start_time).total_seconds()
            
            self.logger.info(
                "Daily earnings process completed successfully",
                total_time=f"{self.stats.total_processing_time:.2f}s",
                earnings_success_rate=f"{self.stats.success_rate * 100:.1f}%",
                business_sync_rate=f"{self.stats.business_sync_rate * 100:.1f}%",
                business_sync_duration=f"{self.stats.business_sync_duration:.2f}s",
                businesses_synced=self.stats.businesses_synced_total,
                businesses_added=self.stats.businesses_added_total,
                businesses_updated=self.stats.businesses_updated_total,
                portfolio_corrections=self.stats.portfolio_corrections_total
            )
            
            return self.stats
            
        except Exception as e:
            self.stats.end_time = datetime.now(timezone.utc)
            if self.stats.start_time:
                self.stats.total_processing_time = (self.stats.end_time - self.stats.start_time).total_seconds()
            
            self.logger.error(
                "Daily earnings process failed",
                error=str(e),
                total_time=f"{self.stats.total_processing_time:.2f}s" if self.stats.start_time else "unknown"
            )
            raise
        finally:
            # Always reset status to IDLE when process completes
            self.status = ProcessorStatus.IDLE
    
    async def update_single_player(self, wallet: str) -> bool:
        """
        🔄 Обновить earnings для одного игрока (для кнопки на фронте)
        
        Args:
            wallet: Кошелек игрока
            
        Returns:
            bool: True если успешно обновлено
        """
        if not self.transaction_manager:
            await self.initialize()
        
        self.logger.info("Manual single player earnings update requested", wallet=wallet)
        
        try:
            success = await self.transaction_manager.update_single_player_earnings(wallet, max_retries=3)
            
            if success:
                self.logger.info("✅ Manual earnings update successful", wallet=wallet)
            else:
                self.logger.error("❌ Manual earnings update failed", wallet=wallet)
            
            return success
            
        except Exception as e:
            self.logger.error("🚨 Error in manual earnings update", wallet=wallet, error=str(e))
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get current processor status and statistics."""
        return {
            "status": self.status.value,
            "stats": asdict(self.stats),
            "failed_players_count": len(self.transaction_manager.failed_players) if self.transaction_manager else 0,
            "config": {
                "batch_size_accounts": self.batch_size_accounts,
                "max_concurrent_updates": self.max_concurrent_updates,
                "timeout_minutes": self.timeout_minutes,
                "retry_delay_base": self.retry_delay_base,
                "failed_player_retry_hours": self.failed_player_retry_hours
            }
        }
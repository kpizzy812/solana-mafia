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
            self.logger.info("Starting daily earnings process")
            
            # Step 1: Cleanup failed players blacklist
            self.transaction_manager.cleanup_failed_players()
            
            # Step 2: Get all active player wallets
            active_wallets = await self.player_repository.get_active_player_wallets()
            self.stats.total_players_found = len(active_wallets)
            
            if not active_wallets:
                self.logger.info("No active players found")
                self.status = ProcessorStatus.COMPLETED
                return self.stats
            
            # Step 3: Send update_earnings transactions to ALL players
            self.logger.info("Sending update_earnings transactions to ALL active players")
            self.stats.players_needing_update = len(active_wallets)  # All players get updates
            
            self.logger.info(
                "Processing ALL players for earnings updates",
                total_players=len(active_wallets),
                strategy="send_all_then_process_events"
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
                success_rate=f"{self.stats.success_rate * 100:.1f}%"
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
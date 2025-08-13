"""
Main EventIndexer class using modular components.
"""

import asyncio
from typing import Dict, Callable, Any, Optional
from datetime import datetime
from dataclasses import asdict

import structlog

from app.core.exceptions import IndexerError
from app.services.solana_client import get_solana_client, SolanaClient
from app.services.event_parser import get_event_parser, EventParser, EventType
from app.indexer.transaction_indexer import get_transaction_indexer, TransactionIndexer

from .types import IndexerStatus, ProcessingStats
from ..monitoring.realtime_monitor import RealtimeMonitor
from ..handlers.player_handlers import PlayerHandlers
from ..handlers.business_handlers import BusinessHandlers
from ..handlers.earnings_handlers import EarningsHandlers


logger = structlog.get_logger(__name__)


class EventIndexer:
    """
    Real-time event indexer for Solana Mafia program.
    
    Features:
    - Continuous monitoring of blockchain events
    - Real-time database updates
    - Event-driven processing with retry logic
    - Comprehensive error handling and recovery
    - Statistics and monitoring
    """
    
    def __init__(self):
        """Initialize the event indexer."""
        self.logger = logger.bind(service="event_indexer")
        self.status = IndexerStatus.STOPPED
        self.stats = ProcessingStats()
        
        # Services
        self.solana_client: Optional[SolanaClient] = None
        self.event_parser: Optional[EventParser] = None
        self.transaction_indexer: Optional[TransactionIndexer] = None
        
        # Components
        self.realtime_monitor: Optional[RealtimeMonitor] = None
        
        # Event handlers
        self._player_handlers = PlayerHandlers(self.stats)
        self._business_handlers = BusinessHandlers(self.stats)
        self._earnings_handlers = EarningsHandlers(self.stats)
        
        # Control flags
        self._running = False
        self._should_stop = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Event handler mappings
        self._event_handlers: Dict[EventType, Callable] = {}
        self._setup_event_handlers()
        
    def _setup_event_handlers(self):
        """Setup event type to handler mappings."""
        self._event_handlers = {
            # Player events
            EventType.PLAYER_CREATED: self._player_handlers.handle_player_created,
            EventType.SLOT_UNLOCKED: self._player_handlers.handle_slot_unlocked,
            EventType.PREMIUM_SLOT_PURCHASED: self._player_handlers.handle_premium_slot_purchased,
            
            # Business events
            EventType.BUSINESS_CREATED: self._business_handlers.handle_business_created,
            EventType.BUSINESS_CREATED_IN_SLOT: self._business_handlers.handle_business_created_in_slot,
            EventType.BUSINESS_UPGRADED: self._business_handlers.handle_business_upgraded,
            EventType.BUSINESS_UPGRADED_IN_SLOT: self._business_handlers.handle_business_upgraded_in_slot,
            EventType.BUSINESS_SOLD: self._business_handlers.handle_business_sold,
            EventType.BUSINESS_SOLD_FROM_SLOT: self._business_handlers.handle_business_sold_from_slot,
            EventType.BUSINESS_TRANSFERRED: self._business_handlers.handle_business_transferred,
            EventType.BUSINESS_DEACTIVATED: self._business_handlers.handle_business_deactivated,
            
            # Earnings events
            EventType.EARNINGS_UPDATED: self._earnings_handlers.handle_earnings_updated,
            EventType.EARNINGS_CLAIMED: self._earnings_handlers.handle_earnings_claimed,
        }
        
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
        
    async def initialize(self):
        """Initialize the indexer and all dependencies."""
        try:
            self.status = IndexerStatus.STARTING
            self.logger.info("Initializing event indexer")
            
            # Initialize services
            self.solana_client = await get_solana_client()
            self.event_parser = get_event_parser()
            self.transaction_indexer = await get_transaction_indexer()
            
            # Initialize components
            self.realtime_monitor = RealtimeMonitor(self)
            await self.realtime_monitor.initialize()
            
            self.stats.start_time = datetime.utcnow()
            self.status = IndexerStatus.STOPPED
            
            self.logger.info("Event indexer initialized successfully")
            
        except Exception as e:
            self.status = IndexerStatus.ERROR
            self.logger.error("Failed to initialize event indexer", error=str(e))
            raise IndexerError(f"Failed to initialize event indexer: {e}")
            
    async def start(self):
        """Start the real-time event indexing."""
        if self.status == IndexerStatus.RUNNING:
            self.logger.warning("Event indexer already running")
            return
            
        try:
            self.status = IndexerStatus.STARTING
            self._should_stop = False
            self._running = True
            
            self.logger.info("Starting event indexer")
            
            # Start monitoring task using the realtime monitor
            self._monitor_task = asyncio.create_task(
                self.realtime_monitor.start_monitoring()
            )
            
            self.status = IndexerStatus.RUNNING
            self.logger.info("Event indexer started successfully")
            
        except Exception as e:
            self.status = IndexerStatus.ERROR
            self._running = False
            self.logger.error("Failed to start event indexer", error=str(e))
            raise IndexerError(f"Failed to start event indexer: {e}")
            
    async def stop(self):
        """Stop the event indexer."""
        if self.status == IndexerStatus.STOPPED:
            return
            
        try:
            self.status = IndexerStatus.STOPPING
            self.logger.info("Stopping event indexer")
            
            self._should_stop = True
            self._running = False
            
            # Cancel monitoring task
            if self._monitor_task and not self._monitor_task.done():
                self._monitor_task.cancel()
                try:
                    await self._monitor_task
                except asyncio.CancelledError:
                    pass
                    
            self.status = IndexerStatus.STOPPED
            self.logger.info("Event indexer stopped")
            
        except Exception as e:
            self.status = IndexerStatus.ERROR
            self.logger.error("Error stopping event indexer", error=str(e))
            
    async def shutdown(self):
        """Shutdown the indexer completely."""
        await self.stop()
        
        if self.solana_client:
            await self.solana_client.close()
            
        self.logger.info("Event indexer shutdown complete")
            
    async def get_status(self) -> Dict[str, Any]:
        """Get current indexer status and statistics."""
        return {
            "status": self.status.value,
            "running": self._running,
            "stats": asdict(self.stats),
            "uptime": (
                datetime.utcnow() - self.stats.start_time
                if self.stats.start_time else None
            )
        }
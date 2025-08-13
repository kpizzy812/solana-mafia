"""
Repository for player data operations.
"""

from datetime import datetime, timezone
from typing import List, Dict
import structlog

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.models.player import Player
from app.models.business import Business
from app.services.earnings.core.types import PlayerAccountData
from app.websocket.notification_service import notification_service


logger = structlog.get_logger(__name__)


class PlayerRepository:
    """
    Repository for player-related database operations.
    """
    
    def __init__(self):
        """Initialize the repository."""
        self.logger = logger.bind(service="player_repository")
        
    async def get_active_player_wallets(self) -> List[str]:
        """Get list of active player wallets from database."""
        try:
            async with get_async_session() as db:
                # Get all players who have businesses (active players)
                result = await db.execute(
                    select(Player.wallet)
                    .join(Business, Player.wallet == Business.player_wallet)
                    .where(Business.is_active == True)
                    .distinct()
                )
                
                wallets = [row[0] for row in result.fetchall()]
                
                self.logger.info(
                    "Retrieved active player wallets",
                    count=len(wallets)
                )
                
                return wallets
                
        except Exception as e:
            self.logger.error("Failed to get active player wallets", error=str(e))
            raise
    
    async def sync_with_blockchain(self, player_states: Dict[str, PlayerAccountData], stats):
        """Sync database state with blockchain (source of truth)."""
        try:
            start_time = datetime.now(timezone.utc)
            
            async with get_async_session() as db:
                # Batch update player states
                updates = []
                for wallet, state in player_states.items():
                    updates.append({
                        'wallet': wallet,
                        'pending_earnings': state.pending_earnings,
                        'last_earnings_update': datetime.fromtimestamp(state.last_auto_update, tz=timezone.utc),
                        'updated_at': datetime.now(timezone.utc)
                    })
                
                # Execute bulk update
                if updates:
                    await db.execute(
                        update(Player),
                        updates
                    )
                    await db.commit()
                    
                    sync_time = (datetime.now(timezone.utc) - start_time).total_seconds()
                    stats.database_sync_time = sync_time
                    
                    self.logger.info(
                        "Database sync completed",
                        players_updated=len(updates),
                        sync_time=f"{sync_time:.2f}s"
                    )
                    
                    # 📡 Отправляем WebSocket уведомления о обновлении earnings
                    for wallet, state in player_states.items():
                        try:
                            await notification_service.notify_earnings_updated(
                                wallet=wallet,
                                earnings_data={
                                    "earnings_balance": state.pending_earnings,
                                    "last_update": datetime.fromtimestamp(state.last_auto_update, tz=timezone.utc).isoformat(),
                                    "updated_at": datetime.now(timezone.utc).isoformat(),
                                    "event": "earnings_sync"
                                }
                            )
                        except Exception as notification_error:
                            self.logger.warning(
                                "Failed to send earnings update notification",
                                wallet=wallet,
                                error=str(notification_error)
                            )
                    
                    self.logger.info(
                        "📡 WebSocket earnings notifications sent",
                        players_notified=len(player_states)
                    )
        
        except Exception as e:
            self.logger.error("Database sync failed", error=str(e))
            raise
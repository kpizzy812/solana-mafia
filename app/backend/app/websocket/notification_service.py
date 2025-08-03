"""
Real-time notification service for WebSocket updates.
"""

from datetime import datetime
from typing import Dict, Any, Optional

from app.models.player import Player
from app.models.business import Business
from app.models.event import Event
from .connection_manager import connection_manager
from .schemas import (
    PlayerUpdateMessage,
    BusinessUpdateMessage,
    EarningsUpdateMessage,
    NFTUpdateMessage,
    ReferralUpdateMessage,
    ReferralCommissionMessage,
    ReferralNewMessage,
    MessageType
)

import structlog

logger = structlog.get_logger(__name__)


class NotificationService:
    """Service for sending real-time notifications to WebSocket clients."""
    
    @staticmethod
    async def notify_player_updated(wallet: str, player_data: Dict[str, Any]):
        """Notify clients when player data is updated."""
        try:
            message = PlayerUpdateMessage(
                data={
                    "wallet": wallet,
                    **player_data
                }
            )
            
            sent_count = await connection_manager.send_to_wallet(wallet, message)
            logger.debug(
                "Player update notification sent",
                wallet=wallet,
                sent_to=sent_count,
                data=player_data
            )
            
        except Exception as e:
            logger.error(
                "Error sending player update notification",
                wallet=wallet,
                error=str(e)
            )
    
    @staticmethod
    async def notify_business_created(wallet: str, business_data: Dict[str, Any]):
        """Notify clients when a business is created."""
        try:
            message = BusinessUpdateMessage(
                data={
                    "event": "business_created",
                    "wallet": wallet,
                    **business_data
                }
            )
            
            sent_count = await connection_manager.send_to_wallet(wallet, message)
            logger.debug(
                "Business creation notification sent",
                wallet=wallet,
                sent_to=sent_count,
                business_id=business_data.get("business_id")
            )
            
        except Exception as e:
            logger.error(
                "Error sending business creation notification",
                wallet=wallet,
                error=str(e)
            )
    
    @staticmethod
    async def notify_business_upgraded(wallet: str, business_data: Dict[str, Any]):
        """Notify clients when a business is upgraded."""
        try:
            message = BusinessUpdateMessage(
                data={
                    "event": "business_upgraded",
                    "wallet": wallet,
                    **business_data
                }
            )
            
            sent_count = await connection_manager.send_to_wallet(wallet, message)
            logger.debug(
                "Business upgrade notification sent",
                wallet=wallet,
                sent_to=sent_count,
                business_id=business_data.get("business_id")
            )
            
        except Exception as e:
            logger.error(
                "Error sending business upgrade notification",
                wallet=wallet,
                error=str(e)
            )
    
    @staticmethod
    async def notify_business_sold(wallet: str, business_data: Dict[str, Any]):
        """Notify clients when a business is sold."""
        try:
            message = BusinessUpdateMessage(
                data={
                    "event": "business_sold",
                    "wallet": wallet,
                    **business_data
                }
            )
            
            sent_count = await connection_manager.send_to_wallet(wallet, message)
            logger.debug(
                "Business sale notification sent",
                wallet=wallet,
                sent_to=sent_count,
                business_id=business_data.get("business_id")
            )
            
        except Exception as e:
            logger.error(
                "Error sending business sale notification",
                wallet=wallet,
                error=str(e)
            )
    
    @staticmethod
    async def notify_earnings_updated(wallet: str, earnings_data: Dict[str, Any]):
        """Notify clients when earnings are updated."""
        try:
            message = EarningsUpdateMessage(
                data={
                    "wallet": wallet,
                    **earnings_data
                }
            )
            
            sent_count = await connection_manager.send_to_wallet(wallet, message)
            logger.debug(
                "Earnings update notification sent",
                wallet=wallet,
                sent_to=sent_count,
                new_balance=earnings_data.get("earnings_balance")
            )
            
        except Exception as e:
            logger.error(
                "Error sending earnings update notification",
                wallet=wallet,
                error=str(e)
            )
    
    @staticmethod
    async def notify_earnings_claimed(wallet: str, claim_data: Dict[str, Any]):
        """Notify clients when earnings are claimed."""
        try:
            message = EarningsUpdateMessage(
                data={
                    "event": "earnings_claimed",
                    "wallet": wallet,
                    **claim_data
                }
            )
            
            sent_count = await connection_manager.send_to_wallet(wallet, message)
            logger.debug(
                "Earnings claim notification sent",
                wallet=wallet,
                sent_to=sent_count,
                claimed_amount=claim_data.get("amount")
            )
            
        except Exception as e:
            logger.error(
                "Error sending earnings claim notification",
                wallet=wallet,
                error=str(e)
            )
    
    @staticmethod
    async def notify_nft_minted(wallet: str, nft_data: Dict[str, Any]):
        """Notify clients when an NFT is minted."""
        try:
            message = NFTUpdateMessage(
                data={
                    "event": "nft_minted",
                    "wallet": wallet,
                    **nft_data
                }
            )
            
            sent_count = await connection_manager.send_to_wallet(wallet, message)
            logger.debug(
                "NFT mint notification sent",
                wallet=wallet,
                sent_to=sent_count,
                nft_id=nft_data.get("nft_id")
            )
            
        except Exception as e:
            logger.error(
                "Error sending NFT mint notification",
                wallet=wallet,
                error=str(e)
            )
    
    @staticmethod
    async def notify_nft_burned(wallet: str, nft_data: Dict[str, Any]):
        """Notify clients when an NFT is burned."""
        try:
            message = NFTUpdateMessage(
                data={
                    "event": "nft_burned",
                    "wallet": wallet,
                    **nft_data
                }
            )
            
            sent_count = await connection_manager.send_to_wallet(wallet, message)
            logger.debug(
                "NFT burn notification sent",
                wallet=wallet,
                sent_to=sent_count,
                nft_id=nft_data.get("nft_id")
            )
            
        except Exception as e:
            logger.error(
                "Error sending NFT burn notification",
                wallet=wallet,
                error=str(e)
            )
    
    @staticmethod
    async def notify_nft_transferred(old_wallet: str, new_wallet: str, nft_data: Dict[str, Any]):
        """Notify clients when an NFT is transferred."""
        try:
            # Notify the sender (old owner)
            sender_message = NFTUpdateMessage(
                data={
                    "event": "nft_transferred_out",
                    "wallet": old_wallet,
                    "new_owner": new_wallet,
                    **nft_data
                }
            )
            await connection_manager.send_to_wallet(old_wallet, sender_message)
            
            # Notify the receiver (new owner)
            receiver_message = NFTUpdateMessage(
                data={
                    "event": "nft_transferred_in",
                    "wallet": new_wallet,
                    "previous_owner": old_wallet,
                    **nft_data
                }
            )
            await connection_manager.send_to_wallet(new_wallet, receiver_message)
            
            logger.debug(
                "NFT transfer notifications sent",
                from_wallet=old_wallet,
                to_wallet=new_wallet,
                nft_id=nft_data.get("nft_id")
            )
            
        except Exception as e:
            logger.error(
                "Error sending NFT transfer notifications",
                from_wallet=old_wallet,
                to_wallet=new_wallet,
                error=str(e)
            )
    
    @staticmethod
    async def process_blockchain_event(event: Event):
        """Process a blockchain event and send appropriate notifications."""
        try:
            event_type = event.event_type
            event_data = event.data
            wallet = event_data.get("player_wallet")
            
            if not wallet:
                logger.warning("Event without wallet address", event_id=event.id, event_type=event_type)
                return
            
            # Map blockchain events to notification methods
            if event_type == "PlayerCreated":
                await NotificationService.notify_player_updated(wallet, {
                    "event": "player_created",
                    "created_at": event.timestamp.isoformat()
                })
            
            elif event_type == "BusinessCreated":
                await NotificationService.notify_business_created(wallet, {
                    "business_id": event_data.get("business_id"),
                    "business_type": event_data.get("business_type"),
                    "level": event_data.get("level", 1),
                    "created_at": event.timestamp.isoformat()
                })
            
            elif event_type == "BusinessUpgraded":
                await NotificationService.notify_business_upgraded(wallet, {
                    "business_id": event_data.get("business_id"),
                    "old_level": event_data.get("old_level"),
                    "new_level": event_data.get("new_level"),
                    "upgraded_at": event.timestamp.isoformat()
                })
            
            elif event_type == "BusinessSold":
                await NotificationService.notify_business_sold(wallet, {
                    "business_id": event_data.get("business_id"),
                    "sale_price": event_data.get("sale_price"),
                    "sold_at": event.timestamp.isoformat()
                })
            
            elif event_type == "EarningsUpdated":
                await NotificationService.notify_earnings_updated(wallet, {
                    "earnings_balance": event_data.get("new_balance"),
                    "earnings_added": event_data.get("earnings_added"),
                    "updated_at": event.timestamp.isoformat()
                })
            
            elif event_type == "EarningsClaimed":
                await NotificationService.notify_earnings_claimed(wallet, {
                    "amount": event_data.get("amount"),
                    "remaining_balance": event_data.get("remaining_balance"),
                    "claimed_at": event.timestamp.isoformat()
                })
            
            elif event_type == "BusinessNFTMinted":
                await NotificationService.notify_nft_minted(wallet, {
                    "nft_id": event_data.get("nft_id"),
                    "business_id": event_data.get("business_id"),
                    "minted_at": event.timestamp.isoformat()
                })
            
            elif event_type == "BusinessNFTBurned":
                await NotificationService.notify_nft_burned(wallet, {
                    "nft_id": event_data.get("nft_id"),
                    "business_id": event_data.get("business_id"),
                    "burned_at": event.timestamp.isoformat()
                })
            
            elif event_type == "BusinessTransferred":
                old_owner = event_data.get("old_owner")
                new_owner = event_data.get("new_owner")
                if old_owner and new_owner:
                    await NotificationService.notify_nft_transferred(
                        old_owner, 
                        new_owner, 
                        {
                            "nft_id": event_data.get("nft_id"),
                            "business_id": event_data.get("business_id"),
                            "transferred_at": event.timestamp.isoformat()
                        }
                    )
            
            logger.debug(
                "Blockchain event processed for notifications",
                event_id=event.id,
                event_type=event_type,
                wallet=wallet
            )
            
        except Exception as e:
            logger.error(
                "Error processing blockchain event for notifications",
                event_id=event.id if event else None,
                error=str(e)
            )


# Global notification service instance
notification_service = NotificationService()
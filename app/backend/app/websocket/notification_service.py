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
    PrestigeUpdateMessage,
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
    
    # ============================================================================
    # REFERRAL SYSTEM NOTIFICATIONS
    # ============================================================================
    
    @staticmethod
    async def notify_new_referral(referrer_wallet: str, referral_data: Dict[str, Any]):
        """Notify referrer when someone uses their referral code."""
        try:
            message = ReferralNewMessage(
                data={
                    "event": "new_referral",
                    "referrer_wallet": referrer_wallet,
                    "referee_wallet": referral_data.get("referee_wallet"),
                    "referral_code": referral_data.get("referral_code"),
                    "level": referral_data.get("level", 1),
                    "commission_rate": referral_data.get("commission_rate"),
                    "prestige_awarded": referral_data.get("prestige_awarded", 0),
                    "created_at": datetime.utcnow().isoformat(),
                    **referral_data
                }
            )
            
            sent_count = await connection_manager.send_to_wallet(referrer_wallet, message)
            logger.debug(
                "New referral notification sent",
                referrer_wallet=referrer_wallet,
                referee_wallet=referral_data.get("referee_wallet"),
                sent_to=sent_count,
                prestige_awarded=referral_data.get("prestige_awarded", 0)
            )
            
        except Exception as e:
            logger.error(
                "Error sending new referral notification",
                referrer_wallet=referrer_wallet,
                referee_wallet=referral_data.get("referee_wallet"),
                error=str(e)
            )
    
    @staticmethod
    async def notify_referral_commission(referrer_wallet: str, commission_data: Dict[str, Any]):
        """Notify referrer when they earn a commission from referral."""
        try:
            message = ReferralCommissionMessage(
                data={
                    "event": "referral_commission",
                    "referrer_wallet": referrer_wallet,
                    "referee_wallet": commission_data.get("referee_wallet"),
                    "commission_amount": commission_data.get("commission_amount"),
                    "commission_rate": commission_data.get("commission_rate"),
                    "level": commission_data.get("level"),
                    "referee_earning_amount": commission_data.get("referee_earning_amount"),
                    "action_type": commission_data.get("action_type", "earnings_claim"),
                    "created_at": datetime.utcnow().isoformat(),
                    **commission_data
                }
            )
            
            sent_count = await connection_manager.send_to_wallet(referrer_wallet, message)
            logger.debug(
                "Referral commission notification sent",
                referrer_wallet=referrer_wallet,
                commission_amount=commission_data.get("commission_amount"),
                level=commission_data.get("level"),
                sent_to=sent_count
            )
            
        except Exception as e:
            logger.error(
                "Error sending referral commission notification",
                referrer_wallet=referrer_wallet,
                commission_amount=commission_data.get("commission_amount"),
                error=str(e)
            )
    
    @staticmethod
    async def notify_referral_stats_update(wallet: str, stats_data: Dict[str, Any]):
        """Notify user when their referral statistics are updated."""
        try:
            message = ReferralUpdateMessage(
                data={
                    "event": "referral_stats_updated",
                    "wallet": wallet,
                    "total_referrals": stats_data.get("total_referrals"),
                    "total_earnings": stats_data.get("total_earnings"),
                    "pending_commission": stats_data.get("pending_commission"),
                    "level_1_referrals": stats_data.get("level_1_referrals"),
                    "level_2_referrals": stats_data.get("level_2_referrals"),
                    "level_3_referrals": stats_data.get("level_3_referrals"),
                    "updated_at": datetime.utcnow().isoformat(),
                    **stats_data
                }
            )
            
            sent_count = await connection_manager.send_to_wallet(wallet, message)
            logger.debug(
                "Referral stats update notification sent",
                wallet=wallet,
                total_referrals=stats_data.get("total_referrals"),
                total_earnings=stats_data.get("total_earnings"),
                sent_to=sent_count
            )
            
        except Exception as e:
            logger.error(
                "Error sending referral stats update notification",
                wallet=wallet,
                error=str(e)
            )
    
    @staticmethod
    async def notify_referral_business_activity(referrer_wallet: str, activity_data: Dict[str, Any]):
        """Notify referrer when their referral does business activity (buy/upgrade)."""
        try:
            message = ReferralUpdateMessage(
                data={
                    "event": "referral_business_activity",
                    "referrer_wallet": referrer_wallet,
                    "referee_wallet": activity_data.get("referee_wallet"),
                    "activity_type": activity_data.get("activity_type", "business_purchase"),
                    "business_type": activity_data.get("business_type"),
                    "amount": activity_data.get("amount"),
                    "level": activity_data.get("level"),
                    "prestige_awarded": activity_data.get("prestige_awarded", 0),
                    "created_at": datetime.utcnow().isoformat(),
                    **activity_data
                }
            )
            
            sent_count = await connection_manager.send_to_wallet(referrer_wallet, message)
            logger.debug(
                "Referral business activity notification sent",
                referrer_wallet=referrer_wallet,
                referee_wallet=activity_data.get("referee_wallet"),
                activity_type=activity_data.get("activity_type"),
                prestige_awarded=activity_data.get("prestige_awarded", 0),
                sent_to=sent_count
            )
            
        except Exception as e:
            logger.error(
                "Error sending referral business activity notification",
                referrer_wallet=referrer_wallet,
                referee_wallet=activity_data.get("referee_wallet"),
                error=str(e)
            )
    
    @staticmethod
    async def notify_prestige_level_up(wallet: str, prestige_data: Dict[str, Any]):
        """Notify user when they level up in prestige system."""
        try:
            # Send as a special player update with prestige focus
            message = PlayerUpdateMessage(
                data={
                    "event": "prestige_level_up",
                    "wallet": wallet,
                    "old_level": prestige_data.get("old_level"),
                    "new_level": prestige_data.get("new_level"),
                    "current_points": prestige_data.get("current_points"),
                    "points_awarded": prestige_data.get("points_awarded"),
                    "reason": prestige_data.get("reason", "Unknown"),
                    "level_up_bonus": prestige_data.get("level_up_bonus", 0),
                    "created_at": datetime.utcnow().isoformat(),
                    **prestige_data
                }
            )
            
            sent_count = await connection_manager.send_to_wallet(wallet, message)
            logger.info(
                "🎉 Prestige level up notification sent",
                wallet=wallet,
                old_level=prestige_data.get("old_level"),
                new_level=prestige_data.get("new_level"),
                points_awarded=prestige_data.get("points_awarded"),
                sent_to=sent_count
            )
            
        except Exception as e:
            logger.error(
                "Error sending prestige level up notification",
                wallet=wallet,
                error=str(e)
            )
    
    @staticmethod
    async def notify_prestige_updated(wallet: str, prestige_data: Dict[str, Any]):
        """Notify user when their prestige points are updated (without level up)."""
        try:
            # Create notification data
            notification_data = {
                "event": "prestige_updated",
                "wallet": wallet,
                "points_awarded": prestige_data.get("points_awarded", 0),
                "current_points": prestige_data.get("current_points", 0),
                "current_level": prestige_data.get("current_level"),
                "total_earned": prestige_data.get("total_earned", 0),
                "source": prestige_data.get("source", "unknown"),
                "reason": prestige_data.get("reason", "Points awarded"),
                "quest_id": prestige_data.get("quest_id"),
                "action_type": prestige_data.get("action_type"),
                "created_at": datetime.utcnow().isoformat(),
                **prestige_data
            }
            
            # Try to send via HTTP to WebSocket container first
            try:
                import httpx
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://websocket:8001/notify",
                        json={
                            "type": "prestige_update",
                            "user_wallet": wallet,
                            "data": notification_data
                        },
                        timeout=5.0
                    )
                    
                    if response.status_code == 200:
                        response_data = response.json()
                        sent_count = response_data.get("sent_to", 0)
                        
                        logger.info(
                            "💎 Prestige update notification sent via HTTP",
                            wallet=wallet,
                            points_awarded=prestige_data.get("points_awarded"),
                            current_points=prestige_data.get("current_points"),
                            current_level=prestige_data.get("current_level"),
                            source=prestige_data.get("source"),
                            sent_to=sent_count
                        )
                        return
                    else:
                        logger.warning(
                            "HTTP prestige notification failed, falling back to local",
                            status_code=response.status_code,
                            response=response.text
                        )
                        
            except Exception as http_error:
                logger.warning(
                    "HTTP prestige notification failed, falling back to local connection_manager",
                    error=str(http_error)
                )
            
            # Fallback to local connection_manager (for websocket container)
            message = PrestigeUpdateMessage(data=notification_data)
            sent_count = await connection_manager.send_to_wallet(wallet, message)
            
            logger.info(
                "💎 Prestige update notification sent locally",
                wallet=wallet,
                points_awarded=prestige_data.get("points_awarded"),
                current_points=prestige_data.get("current_points"),
                current_level=prestige_data.get("current_level"),
                source=prestige_data.get("source"),
                sent_to=sent_count
            )
            
        except Exception as e:
            logger.error(
                "Error sending prestige update notification",
                wallet=wallet,
                error=str(e)
            )
    
    @staticmethod
    async def process_blockchain_event(event: Event):
        """Process a blockchain event and send appropriate notifications."""
        try:
            event_type = event.event_type
            event_data = event.parsed_data or {}
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
    
    @staticmethod
    async def broadcast_event(event_data: Dict[str, Any]):
        """
        Broadcast an event to all connected WebSocket clients.
        Used for real-time event notifications from the indexer.
        
        Args:
            event_data: Event data containing type, signature, data, etc.
        """
        try:
            # Create a generic event message
            from .schemas import WebSocketMessage
            
            message = WebSocketMessage(
                type=MessageType.EVENT,
                data=event_data
            )
            
            # Broadcast to all connected clients
            sent_count = await connection_manager.broadcast_to_all(message)
            
            logger.info(
                "📡 Real-time event broadcasted",
                event_type=event_data.get("event_type"),
                signature=event_data.get("signature"),
                sent_to=sent_count
            )
            
            # Also send targeted notification to specific wallet if available
            wallet = event_data.get("data", {}).get("owner") or event_data.get("data", {}).get("player")
            if wallet:
                await connection_manager.send_to_wallet(wallet, message)
                logger.debug(
                    "Targeted real-time notification sent",
                    wallet=wallet,
                    event_type=event_data.get("event_type")
                )
            
        except Exception as e:
            logger.error(
                "Error broadcasting real-time event",
                event_type=event_data.get("event_type"),
                error=str(e)
            )
    
    @staticmethod
    async def notify_signature_processing(
        signature: str, 
        status: str, 
        user_wallet: Optional[str] = None,
        slot_index: Optional[int] = None,
        business_level: Optional[int] = None,
        result: Optional[Dict[str, Any]] = None
    ):
        """
        Notify clients about signature processing status.
        
        This method supports our new signature processing flow:
        - processing: Transaction is being processed
        - completed: Successfully processed  
        - failed: Processing failed
        """
        try:
            # Create notification data
            notification_data = {
                "type": "signature_processing",
                "signature": signature,
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
                "context": {
                    "slot_index": slot_index,
                    "business_level": business_level
                }
            }
            
            # Add result data if available
            if result:
                notification_data["result"] = result
            
            # Send to specific user wallet if provided
            if user_wallet:
                # Try to send via HTTP to WebSocket container first
                try:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            "http://websocket:8001/notify",
                            json={
                                "type": "signature_processing",
                                "user_wallet": user_wallet,
                                "data": notification_data
                            },
                            timeout=5.0
                        )
                        
                        if response.status_code == 200:
                            response_data = response.json()
                            sent_count = response_data.get("sent_to", 0)
                            
                            logger.info(
                                "🎯 Signature processing notification sent via HTTP",
                                signature=signature[:20] + "...",
                                status=status,
                                user_wallet=user_wallet,
                                slot_index=slot_index,
                                sent_to=sent_count
                            )
                            return
                        else:
                            logger.warning(
                                "HTTP notification failed, falling back to local",
                                status_code=response.status_code,
                                response=response.text
                            )
                            
                except Exception as http_error:
                    logger.warning(
                        "HTTP notification failed, falling back to local connection_manager",
                        error=str(http_error)
                    )
                
                # Fallback to local connection_manager (for websocket container)
                from .schemas import WebSocketMessage
                message = WebSocketMessage(
                    type=MessageType.EVENT,
                    data=notification_data
                )
                
                sent_count = await connection_manager.send_to_wallet(user_wallet, message)
                
                logger.info(
                    "🎯 Signature processing notification sent locally",
                    signature=signature[:20] + "...",
                    status=status,
                    user_wallet=user_wallet,
                    slot_index=slot_index,
                    sent_to=sent_count
                )
            else:
                logger.debug(
                    "No user wallet provided for signature notification",
                    signature=signature[:20] + "...",
                    status=status
                )
            
        except Exception as e:
            logger.error(
                "Error sending signature processing notification",
                signature=signature,
                status=status,
                user_wallet=user_wallet,
                error=str(e)
            )


# Global notification service instance
notification_service = NotificationService()


def get_notification_service() -> NotificationService:
    """Get the global notification service instance."""
    return notification_service
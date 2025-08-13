"""
Telegram Bot service for sending notifications and managing bot interactions.
Uses aiogram v3.21.0 for modern async operations with improved error handling.
"""

import asyncio
from typing import List, Optional, Dict, Any, Union
from datetime import datetime

from aiogram import Bot, Dispatcher, Router
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import (
    TelegramAPIError, 
    TelegramBadRequest, 
    TelegramForbiddenError,
    TelegramNetworkError,
    TelegramRetryAfter
)
import structlog

from app.core.config import settings
from app.models.user import User, UserType
from app.models.referral import ReferralCommission

logger = structlog.get_logger(__name__)


class TelegramBotService:
    """Service for Telegram Bot operations using aiogram v3."""
    
    def __init__(self):
        """Initialize Telegram Bot service with aiogram."""
        self.bot: Optional[Bot] = None
        self.dispatcher: Optional[Dispatcher] = None
        self.router: Optional[Router] = None
        self.is_initialized = False
        
        if hasattr(settings, 'telegram_bot_token') and settings.telegram_bot_token:
            try:
                # Initialize bot with default properties for HTML parsing
                self.bot = Bot(
                    token=settings.telegram_bot_token,
                    default=DefaultBotProperties(
                        parse_mode=ParseMode.HTML,
                        disable_web_page_preview=True
                    )
                )
                
                # Initialize dispatcher and router
                self.dispatcher = Dispatcher()
                self.router = Router()
                self.dispatcher.include_router(self.router)
                
                self.is_initialized = True
                logger.info("Telegram Bot service initialized successfully with aiogram v3")
            except Exception as e:
                logger.error("Failed to initialize Telegram Bot", error=str(e))
        else:
            logger.warning("Telegram Bot token not configured")
    
    def is_available(self) -> bool:
        """Check if Telegram Bot service is available."""
        return self.is_initialized and self.bot is not None
    
    async def send_message(
        self,
        chat_id: Union[int, str],
        message: str,
        parse_mode: Optional[ParseMode] = None,
        disable_notification: bool = False,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        disable_web_page_preview: Optional[bool] = None
    ) -> bool:
        """
        Send a message to a Telegram chat using aiogram.
        
        Args:
            chat_id: Telegram chat ID
            message: Message text
            parse_mode: Message parse mode (HTML, Markdown, None for default)
            disable_notification: Send silently
            reply_markup: Inline keyboard markup
            disable_web_page_preview: Disable link previews
            
        Returns:
            bool: True if sent successfully
        """
        if not self.is_available():
            logger.warning("Telegram Bot not available for sending message")
            return False
        
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode,
                disable_notification=disable_notification,
                reply_markup=reply_markup,
                disable_web_page_preview=disable_web_page_preview
            )
            logger.debug("Message sent successfully", chat_id=chat_id, message_length=len(message))
            return True
            
        except TelegramForbiddenError as e:
            logger.warning(
                "Bot was blocked by user or chat",
                chat_id=chat_id,
                error=str(e)
            )
            return False
            
        except TelegramBadRequest as e:
            logger.error(
                "Bad request to Telegram API",
                chat_id=chat_id,
                error=str(e)
            )
            return False
            
        except TelegramRetryAfter as e:
            logger.warning(
                "Rate limit hit, should retry after",
                chat_id=chat_id,
                retry_after=e.retry_after,
                error=str(e)
            )
            # Optionally wait and retry
            await asyncio.sleep(min(e.retry_after, 60))  # Max 60 second wait
            return False
            
        except TelegramNetworkError as e:
            logger.error(
                "Network error sending message",
                chat_id=chat_id,
                error=str(e)
            )
            return False
            
        except TelegramAPIError as e:
            logger.error(
                "Telegram API error",
                chat_id=chat_id,
                error=str(e),
                error_code=getattr(e, 'error_code', None)
            )
            return False
            
        except Exception as e:
            logger.error(
                "Unexpected error sending message",
                chat_id=chat_id,
                error=str(e),
                error_type=type(e).__name__
            )
            return False
    
    async def send_notification(
        self,
        user: User,
        title: str,
        message: str,
        notification_type: str = "info"
    ) -> bool:
        """
        Send a notification to a user.
        
        Args:
            user: User object
            title: Notification title
            message: Notification message
            notification_type: Type of notification (info, success, warning, error)
            
        Returns:
            bool: True if sent successfully
        """
        if not self.is_available():
            return False
        
        if user.user_type != UserType.TELEGRAM or not user.telegram_user_id:
            logger.debug("User is not a Telegram user", user_id=user.id)
            return False
        
        # Format notification message
        emoji_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "money": "💰",
            "business": "🏢",
            "referral": "👥"
        }
        
        emoji = emoji_map.get(notification_type, "ℹ️")
        formatted_message = f"{emoji} <b>{title}</b>\n\n{message}"
        
        return await self.send_message(
            chat_id=user.telegram_user_id,
            message=formatted_message,
            disable_notification=(notification_type == "info")
        )
    
    async def notify_earnings_available(
        self,
        user: User,
        earning_amount: int,
        total_pending: int
    ) -> bool:
        """
        Notify user about available earnings.
        
        Args:
            user: User object
            earning_amount: New earning amount in lamports
            total_pending: Total pending earnings in lamports
            
        Returns:
            bool: True if sent successfully
        """
        sol_amount = earning_amount / 1_000_000_000
        total_sol = total_pending / 1_000_000_000
        
        message = (
            f"You've earned <b>{sol_amount:.6f} SOL</b> from your businesses!\n"
            f"Total pending: <b>{total_sol:.6f} SOL</b>\n\n"
            f"💡 <i>Claim your earnings through the game interface.</i>"
        )
        
        return await self.send_notification(
            user=user,
            title="New Earnings Available!",
            message=message,
            notification_type="money"
        )
    
    async def notify_referral_commission(
        self,
        user: User,
        commission: ReferralCommission,
        referee_name: str
    ) -> bool:
        """
        Notify user about referral commission.
        
        Args:
            user: User object
            commission: Commission object
            referee_name: Name of the referee
            
        Returns:
            bool: True if sent successfully
        """
        sol_amount = commission.commission_amount / 1_000_000_000
        rate_percent = float(commission.commission_rate) * 100
        
        message = (
            f"You earned <b>{sol_amount:.6f} SOL</b> ({rate_percent}%) from your referral!\n"
            f"Referrer: <b>{referee_name}</b>\n\n"
            f"💰 Keep inviting friends to earn more commissions!"
        )
        
        return await self.send_notification(
            user=user,
            title="Referral Commission Earned!",
            message=message,
            notification_type="referral"
        )
    
    async def notify_business_nft_transfer(
        self,
        user: User,
        business_name: str,
        transfer_type: str,  # "received" or "sent"
        from_address: Optional[str] = None,
        to_address: Optional[str] = None
    ) -> bool:
        """
        Notify user about business NFT transfer.
        
        Args:
            user: User object
            business_name: Name of the business
            transfer_type: Type of transfer
            from_address: Sender address
            to_address: Recipient address
            
        Returns:
            bool: True if sent successfully
        """
        if transfer_type == "received":
            message = (
                f"You received a business NFT: <b>{business_name}</b>\n"
                f"From: <code>{from_address[:8]}...{from_address[-8:] if from_address else 'Unknown'}</code>\n\n"
                f"🏢 Your new business is now generating earnings!"
            )
            title = "Business NFT Received!"
        else:
            message = (
                f"You sent business NFT: <b>{business_name}</b>\n"
                f"To: <code>{to_address[:8]}...{to_address[-8:] if to_address else 'Unknown'}</code>\n\n"
                f"📤 Business ownership has been transferred."
            )
            title = "Business NFT Sent!"
        
        return await self.send_notification(
            user=user,
            title=title,
            message=message,
            notification_type="business"
        )
    
    async def notify_welcome_new_user(
        self,
        user: User,
        referrer_name: Optional[str] = None
    ) -> bool:
        """
        Send welcome message to new user.
        
        Args:
            user: User object
            referrer_name: Name of referrer if any
            
        Returns:
            bool: True if sent successfully
        """
        if referrer_name:
            message = (
                f"Welcome to <b>Solana Mafia</b>, {user.display_name}! 🎉\n\n"
                f"Thanks to <b>{referrer_name}</b> for the referral!\n\n"
                f"🏢 Start by creating your first business and earning SOL!\n"
                f"💰 Invite friends and earn referral commissions!\n\n"
                f"<i>Good luck building your empire!</i>"
            )
        else:
            message = (
                f"Welcome to <b>Solana Mafia</b>, {user.display_name}! 🎉\n\n"
                f"🏢 Start by creating your first business and earning SOL!\n"
                f"💰 Invite friends with your referral code and earn commissions!\n\n"
                f"<i>Good luck building your empire!</i>"
            )
        
        return await self.send_notification(
            user=user,
            title="Welcome to Solana Mafia!",
            message=message,
            notification_type="success"
        )
    
    async def broadcast_message(
        self,
        user_ids: List[int],
        title: str,
        message: str,
        notification_type: str = "info"
    ) -> Dict[str, int]:
        """
        Broadcast message to multiple users.
        
        Args:
            user_ids: List of Telegram user IDs
            title: Message title
            message: Message content
            notification_type: Type of notification
            
        Returns:
            Dict with success/failure counts
        """
        if not self.is_available():
            return {"sent": 0, "failed": len(user_ids)}
        
        sent_count = 0
        failed_count = 0
        
        emoji_map = {
            "info": "ℹ️",
            "success": "✅",
            "warning": "⚠️",
            "error": "❌",
            "announcement": "📢"
        }
        
        emoji = emoji_map.get(notification_type, "ℹ️")
        formatted_message = f"{emoji} <b>{title}</b>\n\n{message}"
        
        # Send messages with delays to avoid rate limiting
        for user_id in user_ids:
            try:
                success = await self.send_message(
                    chat_id=user_id,
                    message=formatted_message,
                    disable_notification=(notification_type == "info")
                )
                
                if success:
                    sent_count += 1
                else:
                    failed_count += 1
                
                # Small delay to respect rate limits
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error("Failed to send broadcast message", error=str(e), user_id=user_id)
                failed_count += 1
        
        logger.info(
            "Broadcast completed",
            sent=sent_count,
            failed=failed_count,
            total=len(user_ids)
        )
        
        return {"sent": sent_count, "failed": failed_count}
    
    async def send_game_stats_update(
        self,
        user: User,
        stats: Dict[str, Any]
    ) -> bool:
        """
        Send game statistics update to user.
        
        Args:
            user: User object
            stats: Game statistics
            
        Returns:
            bool: True if sent successfully
        """
        total_businesses = stats.get("total_businesses", 0)
        total_earnings = stats.get("total_earnings", 0)
        pending_earnings = stats.get("pending_earnings", 0)
        referral_count = stats.get("referral_count", 0)
        
        earnings_sol = total_earnings / 1_000_000_000
        pending_sol = pending_earnings / 1_000_000_000
        
        message = (
            f"📊 <b>Your Game Statistics</b>\n\n"
            f"🏢 Businesses: <b>{total_businesses}</b>\n"
            f"💰 Total Earnings: <b>{earnings_sol:.6f} SOL</b>\n"
            f"⏳ Pending: <b>{pending_sol:.6f} SOL</b>\n"
            f"👥 Referrals: <b>{referral_count}</b>\n\n"
            f"<i>Keep growing your empire!</i>"
        )
        
        return await self.send_notification(
            user=user,
            title="Game Stats Update",
            message=message,
            notification_type="info"
        )


# Global service instance
_telegram_service = None


def get_telegram_service() -> TelegramBotService:
    """Get global Telegram Bot service instance."""
    global _telegram_service
    if _telegram_service is None:
        _telegram_service = TelegramBotService()
    return _telegram_service


async def send_notification_to_user(
    user: User,
    title: str,
    message: str,
    notification_type: str = "info"
) -> bool:
    """
    Convenience function to send notification to user.
    
    Args:
        user: User object
        title: Notification title
        message: Notification message
        notification_type: Type of notification
        
    Returns:
        bool: True if sent successfully
    """
    telegram_service = get_telegram_service()
    return await telegram_service.send_notification(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type
    )
"""
Telegram Mini Apps specific schemas.
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, validator

from .common import BaseResponse


class TMAUserInfo(BaseModel):
    """Telegram Mini Apps user information."""
    id: int = Field(..., description="Telegram user ID")
    first_name: str = Field(..., description="User's first name")
    last_name: Optional[str] = Field(None, description="User's last name")
    username: Optional[str] = Field(None, description="User's username")
    language_code: Optional[str] = Field(None, description="User's language code")
    is_premium: Optional[bool] = Field(None, description="Whether user has Telegram Premium")
    photo_url: Optional[str] = Field(None, description="User's profile photo URL")


class TMAAuthResponse(BaseResponse):
    """Response for TMA authentication."""
    data: Dict[str, Any] = Field(..., description="Authentication data")
    user_info: TMAUserInfo = Field(..., description="Telegram user information")
    auth_date: datetime = Field(..., description="Authentication timestamp")
    start_param: Optional[str] = Field(None, description="Start parameter (for referrals)")


class TMAPlayerCreateRequest(BaseModel):
    """Request to create a player via TMA."""
    referrer_code: Optional[str] = Field(
        None, 
        description="Referral code from another player",
        max_length=20
    )
    
    @validator('referrer_code')
    def validate_referrer_code(cls, v):
        if v is not None and len(v.strip()) == 0:
            return None
        return v


class TMAPlayerResponse(BaseResponse):
    """Response for TMA player data."""
    player_id: str = Field(..., description="Player identifier (Telegram user ID)")
    telegram_user_id: int = Field(..., description="Telegram user ID")
    username: Optional[str] = Field(None, description="Telegram username")
    first_name: str = Field(..., description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    wallet_address: Optional[str] = Field(None, description="Linked wallet address")
    
    # Game data
    total_businesses: int = Field(default=0, description="Total number of businesses")
    total_earnings: int = Field(default=0, description="Total earnings in lamports")
    pending_earnings: int = Field(default=0, description="Pending earnings in lamports")
    pending_referral_earnings: int = Field(default=0, description="Pending referral earnings")
    
    # Referral data
    referrer_id: Optional[str] = Field(None, description="Referrer's user ID")
    referral_count: int = Field(default=0, description="Number of referrals")
    total_referral_earnings: int = Field(default=0, description="Total referral earnings")
    
    # Status
    is_active: bool = Field(default=True, description="Whether player is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login_at: datetime = Field(..., description="Last login timestamp")


class TMALinkWalletRequest(BaseModel):
    """Request to link wallet to TMA account."""
    wallet_address: str = Field(..., description="Solana wallet address")
    signature: str = Field(..., description="Wallet signature for verification")
    message: str = Field(..., description="Signed message")


class TMAGameStatsResponse(BaseResponse):
    """Response for TMA-specific game statistics."""
    telegram_players: int = Field(..., description="Total Telegram players")
    wallet_players: int = Field(..., description="Total wallet players")
    linked_accounts: int = Field(..., description="Accounts with linked wallets")
    
    # Referral stats
    total_referrals: int = Field(..., description="Total referrals made")
    active_referral_chains: int = Field(..., description="Active referral chains")
    referral_earnings_distributed: int = Field(..., description="Total referral earnings distributed")
    
    # Activity stats
    daily_active_tma_users: int = Field(..., description="Daily active TMA users")
    weekly_active_tma_users: int = Field(..., description="Weekly active TMA users")
    monthly_active_tma_users: int = Field(..., description="Monthly active TMA users")


class TMAReferralInfoResponse(BaseResponse):
    """Response for referral information."""
    referral_code: str = Field(..., description="Player's unique referral code")
    referrals: list[Dict[str, Any]] = Field(..., description="List of referrals")
    referral_earnings: Dict[str, int] = Field(..., description="Referral earnings by level")
    total_referral_earnings: int = Field(..., description="Total referral earnings")
    
    # Referral chain info
    level_1_count: int = Field(default=0, description="Direct referrals count")
    level_2_count: int = Field(default=0, description="Second level referrals count")
    level_3_count: int = Field(default=0, description="Third level referrals count")


class TMALeaderboardResponse(BaseResponse):
    """Response for TMA leaderboard."""
    leaderboard: list[Dict[str, Any]] = Field(..., description="Leaderboard entries")
    player_rank: Optional[int] = Field(None, description="Current player's rank")
    total_players: int = Field(..., description="Total players in leaderboard")


class TMANotificationRequest(BaseModel):
    """Request to send notifications via Telegram."""
    user_ids: list[int] = Field(..., description="List of Telegram user IDs")
    message: str = Field(..., description="Notification message", max_length=1000)
    notification_type: str = Field(..., description="Type of notification")


class TMAWebhookData(BaseModel):
    """Webhook data from Telegram."""
    update_id: int = Field(..., description="Update identifier")
    message: Optional[Dict[str, Any]] = Field(None, description="Message data")
    callback_query: Optional[Dict[str, Any]] = Field(None, description="Callback query data")
    web_app_data: Optional[Dict[str, Any]] = Field(None, description="Web app data")
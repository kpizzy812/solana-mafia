"""
Referral system API schemas.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field, validator

from .common import BaseResponse


class ReferralCodeCreateRequest(BaseModel):
    """Request to create a new referral code."""
    pass  # No additional parameters needed


class ReferralCodeResponse(BaseResponse):
    """Response for referral code creation."""
    code: str = Field(..., description="Unique referral code")
    owner_id: str = Field(..., description="Owner's user ID")
    usage_count: int = Field(default=0, description="Number of times code was used")
    is_active: bool = Field(default=True, description="Whether code is active")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    created_at: datetime = Field(..., description="Creation timestamp")


class ReferralProcessRequest(BaseModel):
    """Request to process a referral."""
    referral_code: str = Field(..., description="Referral code to use", max_length=20)
    additional_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional user data (for Telegram users)"
    )
    
    @validator('referral_code')
    def validate_referral_code(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Referral code cannot be empty")
        return v.strip().upper()


class ReferralStatsResponse(BaseResponse):
    """Response for referral statistics."""
    total_referrals: int = Field(default=0, description="Total referrals across all levels")
    total_earnings: int = Field(default=0, description="Total referral earnings in lamports")
    pending_commission: int = Field(default=0, description="Pending commission amount")
    
    # Level breakdown
    level_1_referrals: int = Field(default=0, description="Direct referrals count")
    level_2_referrals: int = Field(default=0, description="Second-level referrals count")
    level_3_referrals: int = Field(default=0, description="Third-level referrals count")
    
    level_1_earnings: int = Field(default=0, description="Level 1 earnings in lamports")
    level_2_earnings: int = Field(default=0, description="Level 2 earnings in lamports")
    level_3_earnings: int = Field(default=0, description="Level 3 earnings in lamports")
    
    last_updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class ReferralInfoResponse(BaseResponse):
    """Response for detailed referral information."""
    referral_code: str = Field(..., description="User's referral code")
    referrals: List[Dict[str, Any]] = Field(..., description="List of referrals")
    total_referrals: int = Field(..., description="Total referral count")
    total_earnings: int = Field(..., description="Total referral earnings")
    
    level_breakdown: Dict[str, int] = Field(..., description="Referral count by level")
    earnings_breakdown: Dict[str, int] = Field(..., description="Earnings by level")


class ReferralCommissionsResponse(BaseResponse):
    """Response for pending commissions."""
    commissions: List[Dict[str, Any]] = Field(..., description="List of pending commissions")
    total_pending_amount: int = Field(..., description="Total pending commission amount")
    total_commissions: int = Field(..., description="Number of pending commissions")


class ReferralLeaderboardResponse(BaseResponse):
    """Response for referral leaderboard."""
    leaderboard: List[Dict[str, Any]] = Field(..., description="Leaderboard entries")
    player_rank: Optional[int] = Field(None, description="Current player's rank")
    total_players: int = Field(..., description="Total players in leaderboard")
    period: str = Field(..., description="Leaderboard period")


class ReferralConfigResponse(BaseResponse):
    """Response for referral system configuration."""
    is_enabled: bool = Field(..., description="Whether referral system is enabled")
    level_1_rate: float = Field(..., description="Level 1 commission rate (0.05 = 5%)")
    level_2_rate: float = Field(..., description="Level 2 commission rate")
    level_3_rate: float = Field(..., description="Level 3 commission rate")
    min_earning_threshold: int = Field(..., description="Minimum earning to trigger commission")
    max_referral_levels: int = Field(..., description="Maximum referral levels")
    version: int = Field(..., description="Configuration version")


class ReferralEarningsRequest(BaseModel):
    """Request to process referral earnings."""
    user_id: str = Field(..., description="User ID who earned")
    earning_amount: int = Field(..., description="Earning amount in lamports", gt=0)
    earning_event_id: Optional[str] = Field(None, description="Event ID that triggered earning")


class ReferralMetricsResponse(BaseResponse):
    """Response for referral system metrics."""
    total_referral_codes: int = Field(..., description="Total referral codes created")
    active_referral_codes: int = Field(..., description="Active referral codes")
    total_referral_relations: int = Field(..., description="Total referral relations")
    total_commissions_paid: int = Field(..., description="Total commissions paid")
    total_commission_amount: int = Field(..., description="Total commission amount in lamports")
    
    daily_stats: Dict[str, int] = Field(..., description="Daily statistics")
    weekly_stats: Dict[str, int] = Field(..., description="Weekly statistics")
    monthly_stats: Dict[str, int] = Field(..., description="Monthly statistics")


class BulkReferralProcessRequest(BaseModel):
    """Request to process multiple referrals in bulk."""
    referrals: List[Dict[str, Any]] = Field(..., description="List of referral data to process")
    
    @validator('referrals')
    def validate_referrals(cls, v):
        if not v:
            raise ValueError("Referrals list cannot be empty")
        if len(v) > 100:
            raise ValueError("Cannot process more than 100 referrals at once")
        return v


class ReferralValidationRequest(BaseModel):
    """Request to validate referral code."""
    referral_code: str = Field(..., description="Referral code to validate")
    user_id: str = Field(..., description="User ID trying to use the code")


class ReferralValidationResponse(BaseResponse):
    """Response for referral code validation."""
    is_valid: bool = Field(..., description="Whether code is valid")
    can_use: bool = Field(..., description="Whether user can use this code")
    reason: Optional[str] = Field(None, description="Reason if invalid or cannot use")
    code_info: Optional[Dict[str, Any]] = Field(None, description="Code information if valid")


class WebReferralProcessRequest(BaseModel):
    """Request to process a web referral (after business purchase)."""
    referral_code: str = Field(..., description="Referral code from URL", max_length=20)
    wallet_address: str = Field(..., description="Player wallet address", max_length=44)
    
    @validator('referral_code')
    def validate_referral_code(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Referral code cannot be empty")
        return v.strip().upper()
    
    @validator('wallet_address')
    def validate_wallet_address(cls, v):
        if not v or len(v.strip()) == 0:
            raise ValueError("Wallet address cannot be empty")
        # Basic Solana wallet address validation
        v = v.strip()
        if len(v) < 32 or len(v) > 44:
            raise ValueError("Invalid wallet address format")
        return v


class WebReferralProcessResponse(BaseResponse):
    """Response for web referral processing."""
    referral_relations_created: int = Field(..., description="Number of referral relations created")
    referrer_wallet: str = Field(..., description="Referrer's wallet address")
    referee_wallet: str = Field(..., description="Referee's wallet address")
    
    # Prestige information
    prestige_awarded_to_referrer: int = Field(default=0, description="Prestige points awarded to referrer")
    referrer_level_up: bool = Field(default=False, description="Whether referrer leveled up")
    
    # Commission rates applied
    commission_rates: List[Dict[str, Any]] = Field(..., description="Commission rates for each level")
    
    # Additional information
    processing_timestamp: datetime = Field(..., description="When the referral was processed")
    next_earnings_will_generate_commissions: bool = Field(
        default=True, 
        description="Whether future earnings will generate commissions"
    )
"""
WebSocket message schemas for real-time communication.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """WebSocket message types."""
    PLAYER_UPDATE = "player_update"
    BUSINESS_UPDATE = "business_update"
    EARNINGS_UPDATE = "earnings_update"
    NFT_UPDATE = "nft_update"
    REFERRAL_UPDATE = "referral_update"
    REFERRAL_COMMISSION = "referral_commission"
    REFERRAL_NEW = "referral_new"
    PRESTIGE_UPDATE = "prestige_update"  # Prestige point and level updates
    EVENT = "event"  # Real-time blockchain events
    ERROR = "error"
    CONNECTION_STATUS = "connection_status"
    SUBSCRIPTION = "subscription"
    UNSUBSCRIPTION = "unsubscription"


class WebSocketMessage(BaseModel):
    """Base WebSocket message schema."""
    type: MessageType
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    data: Dict[str, Any] = Field(default_factory=dict)


class PlayerUpdateMessage(WebSocketMessage):
    """Player update message schema."""
    type: MessageType = MessageType.PLAYER_UPDATE
    data: Dict[str, Any] = Field(
        description="Player update data including earnings, business counts, etc."
    )


class BusinessUpdateMessage(WebSocketMessage):
    """Business update message schema."""
    type: MessageType = MessageType.BUSINESS_UPDATE
    data: Dict[str, Any] = Field(
        description="Business update data including creation, upgrades, sales"
    )


class EarningsUpdateMessage(WebSocketMessage):
    """Earnings update message schema."""
    type: MessageType = MessageType.EARNINGS_UPDATE
    data: Dict[str, Any] = Field(
        description="Earnings update data including balance and pending amounts"
    )


class NFTUpdateMessage(WebSocketMessage):
    """NFT update message schema."""
    type: MessageType = MessageType.NFT_UPDATE
    data: Dict[str, Any] = Field(
        description="NFT update data including minting, burning, transfers"
    )


class ReferralUpdateMessage(WebSocketMessage):
    """Referral update message schema."""
    type: MessageType = MessageType.REFERRAL_UPDATE
    data: Dict[str, Any] = Field(
        description="Referral stats update including total referrals and earnings"
    )


class ReferralCommissionMessage(WebSocketMessage):
    """Referral commission message schema."""
    type: MessageType = MessageType.REFERRAL_COMMISSION
    data: Dict[str, Any] = Field(
        description="Referral commission data including amount, level, and referee info"
    )


class ReferralNewMessage(WebSocketMessage):
    """New referral message schema."""
    type: MessageType = MessageType.REFERRAL_NEW
    data: Dict[str, Any] = Field(
        description="New referral data including referee info and referral level"
    )


class PrestigeUpdateMessage(WebSocketMessage):
    """Prestige update message schema."""
    type: MessageType = MessageType.PRESTIGE_UPDATE
    data: Dict[str, Any] = Field(
        description="Prestige update data including points, level, and awards"
    )


class ErrorMessage(WebSocketMessage):
    """Error message schema."""
    type: MessageType = MessageType.ERROR
    data: Dict[str, Any] = Field(
        description="Error information including code and description"
    )


class ConnectionStatusMessage(WebSocketMessage):
    """Connection status message schema."""
    type: MessageType = MessageType.CONNECTION_STATUS
    data: Dict[str, Any] = Field(
        description="Connection status including connected state and client count"
    )


class SubscriptionMessage(WebSocketMessage):
    """Subscription management message schema."""
    type: MessageType = MessageType.SUBSCRIPTION
    data: Dict[str, Any] = Field(
        description="Subscription data including event types and filters"
    )


# Union type for all possible messages
WebSocketMessageUnion = Union[
    PlayerUpdateMessage,
    BusinessUpdateMessage,
    EarningsUpdateMessage,
    NFTUpdateMessage,
    ReferralUpdateMessage,
    ReferralCommissionMessage,
    ReferralNewMessage,
    PrestigeUpdateMessage,
    ErrorMessage,
    ConnectionStatusMessage,
    SubscriptionMessage
]


class SubscriptionRequest(BaseModel):
    """Client subscription request schema."""
    wallet: str = Field(description="Player wallet address")
    events: list[MessageType] = Field(
        default=[MessageType.PLAYER_UPDATE, MessageType.EARNINGS_UPDATE],
        description="List of event types to subscribe to"
    )
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional filters for events"
    )


class WebSocketResponse(BaseModel):
    """WebSocket response wrapper."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
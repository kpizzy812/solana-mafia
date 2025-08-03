"""
WebSocket authentication utilities.
"""

from typing import Optional
from fastapi import HTTPException, status, Query, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.utils.validation import is_valid_solana_address
from app.api.dependencies import validate_wallet_param

import structlog

logger = structlog.get_logger(__name__)

security = HTTPBearer(auto_error=False)


async def authenticate_websocket_wallet(
    wallet: str = Depends(validate_wallet_param),
    token: Optional[str] = Query(None, description="Optional authentication token"),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Authenticate WebSocket connection using wallet address.
    
    Authentication methods supported:
    1. Bearer token in Authorization header (wallet address)
    2. Token query parameter (wallet address)
    3. Path parameter wallet (validated)
    
    Returns the authenticated wallet address.
    """
    authenticated_wallet = None
    
    # Try Bearer token authentication first
    if credentials and credentials.credentials:
        bearer_wallet = credentials.credentials.strip()
        if is_valid_solana_address(bearer_wallet):
            authenticated_wallet = bearer_wallet
            logger.debug("WebSocket authenticated via Bearer token", wallet=authenticated_wallet)
    
    # Try query parameter token
    elif token:
        token_wallet = token.strip()
        if is_valid_solana_address(token_wallet):
            authenticated_wallet = token_wallet
            logger.debug("WebSocket authenticated via query token", wallet=authenticated_wallet)
    
    # Fallback to path parameter (already validated by dependency)
    if not authenticated_wallet:
        authenticated_wallet = wallet
        logger.debug("WebSocket authenticated via path parameter", wallet=authenticated_wallet)
    
    # Security check: ensure path wallet matches authenticated wallet if both provided
    if authenticated_wallet != wallet:
        logger.warning(
            "WebSocket wallet mismatch",
            path_wallet=wallet,
            auth_wallet=authenticated_wallet
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wallet address mismatch between path and authentication"
        )
    
    return authenticated_wallet


async def validate_websocket_permissions(
    wallet: str,
    requested_subscriptions: Optional[list] = None
) -> bool:
    """
    Validate that a wallet has permission for requested WebSocket subscriptions.
    
    Currently allows all wallets to subscribe to their own data.
    Future implementation might include admin permissions, premium features, etc.
    """
    # Basic validation: wallet can only subscribe to its own events
    if not is_valid_solana_address(wallet):
        return False
    
    # For now, all valid wallets can subscribe to their own events
    # Future: Add premium subscription checks, admin permissions, etc.
    
    logger.debug("WebSocket permissions validated", wallet=wallet)
    return True


def get_connection_limits(wallet: str) -> dict:
    """
    Get connection limits for a wallet.
    
    Returns limits like max connections, subscription limits, etc.
    """
    # Default limits for all users
    limits = {
        "max_connections_per_wallet": 3,
        "max_subscriptions_per_connection": 10,
        "rate_limit_messages_per_minute": 60,
        "ping_interval_seconds": 30
    }
    
    # Future: Implement premium limits, admin overrides, etc.
    # if is_premium_user(wallet):
    #     limits["max_connections_per_wallet"] = 10
    
    return limits
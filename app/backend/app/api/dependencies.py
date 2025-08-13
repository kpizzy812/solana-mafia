"""
API dependencies for FastAPI endpoints.
Provides reusable dependency functions for validation, authentication, and data access.
"""

from typing import Optional, Dict, Any, AsyncGenerator
from fastapi import Depends, HTTPException, Header, Query, Path, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import structlog

from app.core.database import get_async_session
from app.core.config import settings
from app.core.exceptions import ValidationError, NotFoundError, AuthenticationError
from app.models.player import Player
from app.models.business import Business
# Убрано BusinessNFT - NFT больше не используются
from app.utils.validation import validate_wallet_address
from app.api.schemas.common import PaginationParams, SortParams
from app.auth.tma_auth import AuthType, TMAInitData


logger = structlog.get_logger(__name__)


# Security scheme for wallet authentication
wallet_auth_scheme = HTTPBearer(auto_error=False)


async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """Get database session dependency."""
    async with get_async_session() as session:
        yield session


async def validate_wallet_param(
    wallet: str = Path(..., description="Solana wallet address")
) -> str:
    """Validate wallet address path parameter."""
    if not validate_wallet_address(wallet):
        logger.warning("Invalid wallet address provided", wallet=wallet)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_WALLET_ADDRESS",
                "message": "Invalid Solana wallet address format"
            }
        )
    return wallet


async def validate_business_id_param(
    business_id: str = Path(..., description="Business identifier")
) -> str:
    """Validate business ID path parameter."""
    if not business_id or len(business_id) < 8:
        logger.warning("Invalid business ID provided", business_id=business_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "INVALID_BUSINESS_ID",
                "message": "Invalid business ID format"
            }
        )
    return business_id


# Убрано validate_nft_mint_param - NFT больше не используются


async def get_pagination_params(
    limit: int = Query(50, ge=1, le=1000, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Number of items to skip")
) -> PaginationParams:
    """Get pagination parameters."""
    return PaginationParams(limit=limit, offset=offset)


async def get_sort_params(
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order")
) -> SortParams:
    """Get sort parameters."""
    return SortParams(sort_by=sort_by, sort_order=sort_order)


async def get_player_by_wallet(
    wallet: str = Depends(validate_wallet_param),
    db: AsyncSession = Depends(get_database)
) -> Player:
    """Get player by wallet address."""
    try:
        result = await db.execute(
            select(Player).where(Player.wallet == wallet)
        )
        player = result.scalar_one_or_none()
        
        if not player:
            logger.info("Player not found", wallet=wallet)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "PLAYER_NOT_FOUND",
                    "message": f"Player with wallet {wallet} not found"
                }
            )
        
        logger.debug("Player found", wallet=wallet, player_id=player.wallet)
        return player
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching player", wallet=wallet, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Failed to fetch player data"
            }
        )


async def get_player_by_wallet_optional(
    wallet: str = Depends(validate_wallet_param),
    db: AsyncSession = Depends(get_database)
) -> Optional[Player]:
    """Get player by wallet address, return None if not found."""
    try:
        result = await db.execute(
            select(Player).where(Player.wallet == wallet)
        )
        player = result.scalar_one_or_none()
        
        if player:
            logger.debug("Player found", wallet=wallet, player_id=player.wallet)
        else:
            logger.info("Player not found", wallet=wallet)
        
        return player
        
    except Exception as e:
        logger.error("Error fetching player", wallet=wallet, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Failed to fetch player data"
            }
        )


async def get_business_by_id(
    business_id: str = Depends(validate_business_id_param),
    db: AsyncSession = Depends(get_database)
) -> Business:
    """Get business by ID."""
    try:
        result = await db.execute(
            select(Business).where(Business.business_id == business_id)
        )
        business = result.scalar_one_or_none()
        
        if not business:
            logger.info("Business not found", business_id=business_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "BUSINESS_NOT_FOUND",
                    "message": f"Business with ID {business_id} not found"
                }
            )
        
        logger.debug("Business found", business_id=business_id)
        return business
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error fetching business", business_id=business_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "DATABASE_ERROR",
                "message": "Failed to fetch business data"
            }
        )


# Убрано get_nft_by_mint - NFT больше не используются


async def verify_business_ownership(
    business: Business = Depends(get_business_by_id),
    player: Player = Depends(get_player_by_wallet),
) -> Business:
    """Verify that the player owns the business."""
    if business.owner != player.wallet:
        logger.warning(
            "Business ownership verification failed",
            business_id=business.business_id,
            business_owner=business.owner,
            requesting_wallet=player.wallet
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "BUSINESS_NOT_OWNED",
                "message": "You do not own this business"
            }
        )
    
    return business


# Убрано verify_nft_ownership - NFT больше не используются


async def get_optional_wallet_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(wallet_auth_scheme)
) -> Optional[str]:
    """Get optional wallet authentication from Bearer token."""
    if not credentials:
        return None
    
    # For now, we'll treat the token as a wallet address
    # In a real implementation, you'd verify the signature
    token = credentials.credentials
    
    if validate_wallet_address(token):
        return token
    
    logger.warning("Invalid wallet token provided", token=token[:8] + "...")
    return None


async def get_required_wallet_auth(
    wallet: Optional[str] = Depends(get_optional_wallet_auth)
) -> str:
    """Get required wallet authentication."""
    if not wallet:
        logger.warning("Missing wallet authentication")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AUTHENTICATION_REQUIRED",
                "message": "Wallet authentication required"
            }
        )
    
    return wallet


async def get_rate_limit_key(
    request_ip: str = Header(None, alias="x-forwarded-for"),
    wallet: Optional[str] = Depends(get_optional_wallet_auth)
) -> str:
    """Get rate limiting key."""
    if wallet:
        return f"wallet:{wallet}"
    
    # Fallback to IP address
    client_ip = request_ip or "unknown"
    return f"ip:{client_ip}"


async def validate_admin_access(
    wallet: str = Depends(get_required_wallet_auth)
) -> str:
    """Validate admin access (placeholder implementation)."""
    # In a real implementation, check if wallet is in admin list
    admin_wallets = getattr(settings, 'admin_wallets', [])
    
    if wallet not in admin_wallets:
        logger.warning("Unauthorized admin access attempt", wallet=wallet)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "ADMIN_ACCESS_DENIED",
                "message": "Admin access required"
            }
        )
    
    return wallet


# Common query parameters
async def get_business_type_filter(
    business_type: Optional[int] = Query(
        None, 
        ge=0, 
        le=9, 
        description="Filter by business type (0-9)"
    )
) -> Optional[int]:
    """Get business type filter parameter."""
    return business_type


async def get_active_only_filter(
    active_only: bool = Query(
        True, 
        description="Filter to show only active items"
    )
) -> bool:
    """Get active only filter parameter."""
    return active_only


async def get_date_range_filter(
    start_date: Optional[str] = Query(
        None, 
        regex=r"^\d{4}-\d{2}-\d{2}$",
        description="Start date filter (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(
        None,
        regex=r"^\d{4}-\d{2}-\d{2}$", 
        description="End date filter (YYYY-MM-DD)"
    )
) -> Dict[str, Optional[str]]:
    """Get date range filter parameters."""
    return {"start_date": start_date, "end_date": end_date}


# TMA Authentication Dependencies

async def get_auth_data(request: Request) -> Dict[str, Any]:
    """Get authentication data from request state."""
    return {
        'wallet': getattr(request.state, 'wallet', None),
        'tma_data': getattr(request.state, 'tma_data', None),
        'auth_type': getattr(request.state, 'auth_type', None)
    }


async def get_optional_auth(
    auth_data: Dict[str, Any] = Depends(get_auth_data)
) -> Dict[str, Any]:
    """Get optional authentication (wallet or TMA)."""
    return auth_data


async def get_required_auth(
    auth_data: Dict[str, Any] = Depends(get_auth_data)
) -> Dict[str, Any]:
    """Get required authentication (wallet or TMA)."""
    if not auth_data.get('wallet') and not auth_data.get('tma_data'):
        logger.warning("Missing authentication")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AUTHENTICATION_REQUIRED",
                "message": "Authentication required (wallet signature or Telegram Mini Apps)"
            }
        )
    
    return auth_data


async def get_tma_auth(
    auth_data: Dict[str, Any] = Depends(get_auth_data)
) -> Dict[str, Any]:
    """Get required TMA authentication."""
    if auth_data.get('auth_type') != AuthType.TMA or not auth_data.get('tma_data'):
        logger.warning("Missing TMA authentication")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "TMA_AUTHENTICATION_REQUIRED",
                "message": "Telegram Mini Apps authentication required"
            }
        )
    
    return auth_data


async def get_wallet_auth(
    auth_data: Dict[str, Any] = Depends(get_auth_data)
) -> str:
    """Get required wallet authentication."""
    if auth_data.get('auth_type') != AuthType.WALLET or not auth_data.get('wallet'):
        logger.warning("Missing wallet authentication")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "WALLET_AUTHENTICATION_REQUIRED",
                "message": "Wallet signature authentication required"
            }
        )
    
    return auth_data['wallet']


async def get_user_identifier(
    auth_data: Dict[str, Any] = Depends(get_required_auth)
) -> str:
    """Get user identifier (wallet address or Telegram user ID)."""
    if auth_data.get('auth_type') == AuthType.WALLET:
        return auth_data['wallet']
    elif auth_data.get('auth_type') == AuthType.TMA:
        tma_data = auth_data['tma_data']
        return f"tg_{tma_data['telegram_user_id']}"
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "INVALID_AUTHENTICATION",
                "message": "Unable to determine user identifier"
            }
        )
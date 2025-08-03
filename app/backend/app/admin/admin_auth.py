"""
Admin authentication and authorization utilities.
"""

from typing import Optional, List
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.utils.validation import is_valid_solana_address

import structlog

logger = structlog.get_logger(__name__)

security = HTTPBearer()


class AdminAuth:
    """Admin authentication and authorization service."""
    
    def __init__(self):
        # Admin wallet addresses (from environment or config)
        self.admin_wallets: List[str] = self._load_admin_wallets()
        # Admin API key (from environment)
        self.admin_api_key: Optional[str] = settings.admin_api_key
        
    def _load_admin_wallets(self) -> List[str]:
        """Load admin wallet addresses from configuration."""
        admin_wallets_str = getattr(settings, 'admin_wallets', '')
        if not admin_wallets_str:
            logger.warning("No admin wallets configured")
            return []
        
        wallets = []
        for wallet in admin_wallets_str.split(','):
            wallet = wallet.strip()
            if is_valid_solana_address(wallet):
                wallets.append(wallet)
            else:
                logger.warning("Invalid admin wallet address", wallet=wallet)
        
        logger.info("Loaded admin wallets", count=len(wallets))
        return wallets
    
    def is_admin_wallet(self, wallet: str) -> bool:
        """Check if a wallet address is an admin wallet."""
        return wallet in self.admin_wallets
    
    def is_valid_api_key(self, api_key: str) -> bool:
        """Check if an API key is valid for admin access."""
        return self.admin_api_key and api_key == self.admin_api_key
    
    def authenticate_request(self, credentials: HTTPAuthorizationCredentials) -> dict:
        """
        Authenticate an admin request using Bearer token.
        
        Token can be either:
        1. Admin wallet address
        2. Admin API key
        """
        token = credentials.credentials.strip()
        
        # Check if token is admin API key
        if self.is_valid_api_key(token):
            return {
                "auth_type": "api_key",
                "authenticated": True,
                "admin": True
            }
        
        # Check if token is admin wallet address
        if is_valid_solana_address(token) and self.is_admin_wallet(token):
            return {
                "auth_type": "wallet",
                "wallet": token,
                "authenticated": True,
                "admin": True
            }
        
        # Authentication failed
        return {
            "authenticated": False,
            "admin": False
        }


# Global admin auth instance
admin_auth = AdminAuth()


async def require_admin_auth(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Dependency that requires admin authentication.
    
    Raises HTTPException if authentication fails.
    Returns authentication info if successful.
    """
    auth_result = admin_auth.authenticate_request(credentials)
    
    if not auth_result.get("authenticated") or not auth_result.get("admin"):
        logger.warning(
            "Admin authentication failed",
            token_type=auth_result.get("auth_type"),
            token_preview=credentials.credentials[:8] + "..." if len(credentials.credentials) > 8 else credentials.credentials
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    logger.debug(
        "Admin authenticated successfully",
        auth_type=auth_result["auth_type"],
        wallet=auth_result.get("wallet", "N/A")
    )
    
    return auth_result


async def optional_admin_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    Dependency that provides optional admin authentication.
    
    Returns authentication info regardless of success/failure.
    Does not raise exceptions.
    """
    if not credentials:
        return {
            "authenticated": False,
            "admin": False
        }
    
    return admin_auth.authenticate_request(credentials)


def require_admin_permissions(required_permissions: Optional[List[str]] = None):
    """
    Decorator for additional permission checks beyond basic admin auth.
    
    Currently just checks basic admin status, but can be extended
    for granular permissions like 'system_monitor', 'user_management', etc.
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # For now, just require basic admin auth
            # Future: Check specific permissions
            return await func(*args, **kwargs)
        return wrapper
    return decorator


def get_admin_context(auth_result: dict) -> dict:
    """
    Get admin context information from authentication result.
    
    Useful for logging and audit trails.
    """
    return {
        "is_admin": auth_result.get("admin", False),
        "auth_type": auth_result.get("auth_type"),
        "wallet": auth_result.get("wallet"),
        "authenticated_at": auth_result.get("authenticated_at")
    }
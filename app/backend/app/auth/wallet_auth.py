"""
Solana wallet authentication module.
"""

from typing import Optional
import structlog
from fastapi import HTTPException, status

from app.utils.validation import validate_wallet_address

logger = structlog.get_logger(__name__)


class WalletAuth:
    """Solana wallet authentication handler."""

    def __init__(self):
        """Initialize wallet authentication."""
        pass

    def validate_wallet_token(self, token: str) -> str:
        """
        Validate wallet token (for now, just the wallet address).
        
        Args:
            token: Wallet address or signed message
            
        Returns:
            str: Validated wallet address
            
        Raises:
            HTTPException: If validation fails
        """
        # For now, treat token as wallet address
        # In production, you'd verify the signature of a signed message
        if not validate_wallet_address(token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid wallet address format"
            )
        
        logger.info("Wallet authenticated", wallet=token)
        return token

    def extract_wallet_from_bearer_token(self, token: str) -> Optional[str]:
        """
        Extract wallet address from Bearer token.
        
        Args:
            token: Bearer token (wallet address for now)
            
        Returns:
            Optional[str]: Wallet address if valid, None otherwise
        """
        try:
            return self.validate_wallet_token(token)
        except HTTPException:
            return None
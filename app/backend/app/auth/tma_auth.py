"""
Telegram Mini Apps authentication module.
Validates Telegram Mini Apps init data according to official documentation.
"""

import hashlib
import hmac
import json
import time
from typing import Dict, Any, Optional, Union
from urllib.parse import unquote, parse_qsl
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import structlog
from fastapi import HTTPException, status

logger = structlog.get_logger(__name__)


class AuthType(str, Enum):
    """Authentication types supported by the system."""
    TMA = "tma"  # Telegram Mini Apps
    WALLET = "wallet"  # Solana wallet signature


@dataclass
class TMAUser:
    """Telegram Mini Apps user data."""
    id: int
    first_name: str
    last_name: Optional[str] = None
    username: Optional[str] = None
    language_code: Optional[str] = None
    is_premium: Optional[bool] = None
    added_to_attachment_menu: Optional[bool] = None
    allows_write_to_pm: Optional[bool] = None
    photo_url: Optional[str] = None


@dataclass
class TMAChat:
    """Telegram Mini Apps chat data."""
    id: int
    type: str
    title: Optional[str] = None
    username: Optional[str] = None
    photo_url: Optional[str] = None


@dataclass
class TMAInitData:
    """Telegram Mini Apps initialization data."""
    auth_date: int
    hash: str
    query_id: Optional[str] = None
    user: Optional[TMAUser] = None
    receiver: Optional[TMAUser] = None
    chat: Optional[TMAChat] = None
    chat_type: Optional[str] = None
    chat_instance: Optional[str] = None
    start_param: Optional[str] = None
    can_send_after: Optional[int] = None

    @property
    def telegram_user_id(self) -> Optional[int]:
        """Get Telegram user ID if available."""
        return self.user.id if self.user else None

    @property
    def is_expired(self, max_age_hours: int = 24) -> bool:
        """Check if init data is expired."""
        now = int(time.time())
        max_age_seconds = max_age_hours * 3600
        return (now - self.auth_date) > max_age_seconds


class TelegramMiniAppAuth:
    """Telegram Mini Apps authentication handler."""

    def __init__(self, bot_token: str, max_age_hours: int = 24):
        """
        Initialize TMA authentication.
        
        Args:
            bot_token: Telegram bot token
            max_age_hours: Maximum age of init data in hours (default: 24)
        """
        self.bot_token = bot_token
        self.max_age_hours = max_age_hours
        self.secret_key = hashlib.sha256(bot_token.encode()).digest()

    def validate_init_data(self, init_data_raw: str) -> TMAInitData:
        """
        Validate Telegram Mini Apps init data.
        
        Args:
            init_data_raw: Raw init data string from Telegram
            
        Returns:
            TMAInitData: Parsed and validated init data
            
        Raises:
            HTTPException: If validation fails
        """
        try:
            # Parse query string
            parsed_data = dict(parse_qsl(init_data_raw))
            
            # Extract hash
            received_hash = parsed_data.pop('hash', None)
            if not received_hash:
                raise ValueError("No hash provided in init data")

            # Create data check string
            data_check_string = self._create_data_check_string(parsed_data)
            
            # Validate signature
            if not self._verify_signature(data_check_string, received_hash):
                raise ValueError("Invalid init data signature")

            # Parse and validate init data
            init_data = self._parse_init_data(parsed_data)
            
            # Check expiration
            if init_data.is_expired(self.max_age_hours):
                raise ValueError(f"Init data expired (older than {self.max_age_hours} hours)")

            logger.info(
                "TMA init data validated successfully",
                user_id=init_data.telegram_user_id,
                auth_date=init_data.auth_date
            )
            
            return init_data

        except Exception as e:
            logger.warning("TMA init data validation failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Telegram Mini Apps init data: {str(e)}"
            )

    def _create_data_check_string(self, data: Dict[str, str]) -> str:
        """Create data check string for signature verification."""
        # Sort keys alphabetically and create key=value pairs
        sorted_params = sorted(data.items())
        data_check_string = '\n'.join(f"{key}={value}" for key, value in sorted_params)
        return data_check_string

    def _verify_signature(self, data_check_string: str, received_hash: str) -> bool:
        """Verify HMAC signature of init data."""
        # Calculate HMAC-SHA256
        calculated_hash = hmac.new(
            self.secret_key,
            data_check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare hashes
        return hmac.compare_digest(calculated_hash, received_hash)

    def _parse_init_data(self, data: Dict[str, str]) -> TMAInitData:
        """Parse init data dictionary into structured format."""
        # Parse auth_date
        auth_date = int(data.get('auth_date', 0))
        if auth_date == 0:
            raise ValueError("Invalid auth_date")

        # Parse user data
        user = None
        if 'user' in data:
            try:
                user_data = json.loads(unquote(data['user']))
                user = TMAUser(**user_data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("Failed to parse user data", error=str(e))

        # Parse receiver data
        receiver = None
        if 'receiver' in data:
            try:
                receiver_data = json.loads(unquote(data['receiver']))
                receiver = TMAUser(**receiver_data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("Failed to parse receiver data", error=str(e))

        # Parse chat data
        chat = None
        if 'chat' in data:
            try:
                chat_data = json.loads(unquote(data['chat']))
                chat = TMAChat(**chat_data)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("Failed to parse chat data", error=str(e))

        return TMAInitData(
            auth_date=auth_date,
            hash=data.get('hash', ''),
            query_id=data.get('query_id'),
            user=user,
            receiver=receiver,
            chat=chat,
            chat_type=data.get('chat_type'),
            chat_instance=data.get('chat_instance'),
            start_param=data.get('start_param'),
            can_send_after=int(data['can_send_after']) if data.get('can_send_after') else None
        )


def validate_init_data(init_data_raw: str, bot_token: str, max_age_hours: int = 24) -> TMAInitData:
    """
    Utility function to validate Telegram Mini Apps init data.
    
    Args:
        init_data_raw: Raw init data string
        bot_token: Telegram bot token
        max_age_hours: Maximum age in hours
        
    Returns:
        TMAInitData: Validated init data
    """
    auth = TelegramMiniAppAuth(bot_token, max_age_hours)
    return auth.validate_init_data(init_data_raw)


def parse_auth_header(auth_header: str) -> tuple[AuthType, str]:
    """
    Parse Authorization header and extract auth type and data.
    
    Args:
        auth_header: Authorization header value
        
    Returns:
        tuple: (auth_type, auth_data)
        
    Raises:
        HTTPException: If header format is invalid
    """
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required"
        )

    try:
        auth_type_str, auth_data = auth_header.split(' ', 1)
        auth_type = AuthType(auth_type_str.lower())
        return auth_type, auth_data
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected: 'Bearer <token>' or 'tma <init_data>'"
        )
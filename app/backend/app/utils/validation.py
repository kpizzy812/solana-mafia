"""
Blockchain data validation utilities.
Provides validation functions for Solana addresses, signatures, and game-specific data.
"""

import re
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timedelta
import base58
from solders.pubkey import Pubkey
from solders.signature import Signature

import structlog
from app.core.exceptions import ValidationError
from app.core.config import settings


logger = structlog.get_logger(__name__)


class SolanaValidator:
    """Validator for Solana blockchain data."""
    
    @staticmethod
    def is_valid_pubkey(address: str) -> bool:
        """
        Validate if a string is a valid Solana public key.
        
        Args:
            address: String to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not address or len(address) < 32 or len(address) > 44:
                return False
            Pubkey.from_string(address)
            return True
        except Exception:
            return False
            
    @staticmethod
    def is_valid_signature(signature: str) -> bool:
        """
        Validate if a string is a valid Solana transaction signature.
        
        Args:
            signature: String to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            if not signature or len(signature) < 80 or len(signature) > 88:
                return False
            Signature.from_string(signature)
            return True
        except Exception:
            return False
            
    @staticmethod
    def is_valid_base58(data: str) -> bool:
        """
        Validate if a string is valid base58 encoding.
        
        Args:
            data: String to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            base58.b58decode(data)
            return True
        except Exception:
            return False
            
    @staticmethod
    def validate_program_id(program_id: str) -> bool:
        """
        Validate if the program ID matches our expected program.
        
        Args:
            program_id: Program ID to validate
            
        Returns:
            True if valid, False otherwise
        """
        return (
            SolanaValidator.is_valid_pubkey(program_id) and
            program_id == settings.solana_program_id
        )


class GameDataValidator:
    """Validator for game-specific data."""
    
    # Business type constants (should match the Rust program)
    VALID_BUSINESS_TYPES = list(range(10))  # 0-9 business types
    MAX_BUSINESS_LEVEL = 10
    MAX_SLOT_INDEX = 25  # 0-24 for regular slots, 25+ for premium
    MIN_EARNINGS_PER_HOUR = 1
    MAX_EARNINGS_PER_HOUR = 1000000  # 1M lamports per hour
    
    @staticmethod
    def validate_business_type(business_type: int) -> bool:
        """Validate business type."""
        return business_type in GameDataValidator.VALID_BUSINESS_TYPES
        
    @staticmethod
    def validate_business_level(level: int) -> bool:
        """Validate business level."""
        return 1 <= level <= GameDataValidator.MAX_BUSINESS_LEVEL
        
    @staticmethod
    def validate_slot_index(slot_index: int) -> bool:
        """Validate slot index."""
        return 0 <= slot_index <= GameDataValidator.MAX_SLOT_INDEX
        
    @staticmethod
    def validate_earnings_amount(amount: int) -> bool:
        """Validate earnings amount."""
        return (
            GameDataValidator.MIN_EARNINGS_PER_HOUR <= amount <= 
            GameDataValidator.MAX_EARNINGS_PER_HOUR
        )
        
    @staticmethod
    def validate_lamports_amount(amount: int) -> bool:
        """Validate lamports amount (must be non-negative)."""
        return amount >= 0
        
    @staticmethod
    def validate_business_name(name: str) -> bool:
        """Validate business name."""
        if not name or not isinstance(name, str):
            return False
        return 1 <= len(name.strip()) <= 32
        
    @staticmethod
    def validate_upgrade_logic(old_level: int, new_level: int) -> bool:
        """Validate business upgrade logic."""
        return (
            GameDataValidator.validate_business_level(old_level) and
            GameDataValidator.validate_business_level(new_level) and
            new_level == old_level + 1
        )


class EventDataValidator:
    """Validator for event data consistency."""
    
    @staticmethod
    def validate_player_created_event(data: Dict[str, Any]) -> List[str]:
        """
        Validate PlayerCreated event data.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Required fields
        if "wallet" not in data:
            errors.append("Missing wallet field")
        elif not SolanaValidator.is_valid_pubkey(data["wallet"]):
            errors.append("Invalid wallet address")
            
        # Optional referrer validation
        if "referrer" in data and data["referrer"]:
            if not SolanaValidator.is_valid_pubkey(data["referrer"]):
                errors.append("Invalid referrer address")
                
        # Slots unlocked validation
        if "slots_unlocked" in data:
            if not isinstance(data["slots_unlocked"], int) or data["slots_unlocked"] < 1:
                errors.append("Invalid slots_unlocked value")
                
        return errors
        
    @staticmethod
    def validate_business_created_event(data: Dict[str, Any]) -> List[str]:
        """
        Validate BusinessCreated event data.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Required fields
        required_fields = [
            "business_id", "owner", "business_type", "name", 
            "slot_index", "cost", "earnings_per_hour", "nft_mint"
        ]
        
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing {field} field")
                
        # Validate specific fields if present
        if "owner" in data and not SolanaValidator.is_valid_pubkey(data["owner"]):
            errors.append("Invalid owner address")
            
        if "nft_mint" in data and not SolanaValidator.is_valid_pubkey(data["nft_mint"]):
            errors.append("Invalid NFT mint address")
            
        if "business_type" in data and not GameDataValidator.validate_business_type(data["business_type"]):
            errors.append("Invalid business type")
            
        if "slot_index" in data and not GameDataValidator.validate_slot_index(data["slot_index"]):
            errors.append("Invalid slot index")
            
        if "cost" in data and not GameDataValidator.validate_lamports_amount(data["cost"]):
            errors.append("Invalid cost amount")
            
        if "earnings_per_hour" in data and not GameDataValidator.validate_earnings_amount(data["earnings_per_hour"]):
            errors.append("Invalid earnings per hour")
            
        if "name" in data and not GameDataValidator.validate_business_name(data["name"]):
            errors.append("Invalid business name")
            
        return errors
        
    @staticmethod
    def validate_business_upgraded_event(data: Dict[str, Any]) -> List[str]:
        """
        Validate BusinessUpgraded event data.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Required fields
        required_fields = [
            "business_id", "owner", "old_level", "new_level", 
            "upgrade_cost", "new_earnings_per_hour", "nft_mint"
        ]
        
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing {field} field")
                
        # Validate specific fields
        if "owner" in data and not SolanaValidator.is_valid_pubkey(data["owner"]):
            errors.append("Invalid owner address")
            
        if "nft_mint" in data and not SolanaValidator.is_valid_pubkey(data["nft_mint"]):
            errors.append("Invalid NFT mint address")
            
        if "old_level" in data and "new_level" in data:
            if not GameDataValidator.validate_upgrade_logic(data["old_level"], data["new_level"]):
                errors.append("Invalid upgrade logic")
                
        if "upgrade_cost" in data and not GameDataValidator.validate_lamports_amount(data["upgrade_cost"]):
            errors.append("Invalid upgrade cost")
            
        if "new_earnings_per_hour" in data and not GameDataValidator.validate_earnings_amount(data["new_earnings_per_hour"]):
            errors.append("Invalid new earnings per hour")
            
        return errors
        
    @staticmethod
    def validate_business_sold_event(data: Dict[str, Any]) -> List[str]:
        """
        Validate BusinessSold event data.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Required fields
        required_fields = [
            "business_id", "seller", "sale_price", "penalty_amount", 
            "days_held", "nft_mint"
        ]
        
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing {field} field")
                
        # Validate addresses
        if "seller" in data and not SolanaValidator.is_valid_pubkey(data["seller"]):
            errors.append("Invalid seller address")
            
        if "buyer" in data and data["buyer"] and not SolanaValidator.is_valid_pubkey(data["buyer"]):
            errors.append("Invalid buyer address")
            
        if "nft_mint" in data and not SolanaValidator.is_valid_pubkey(data["nft_mint"]):
            errors.append("Invalid NFT mint address")
            
        # Validate amounts
        if "sale_price" in data and not GameDataValidator.validate_lamports_amount(data["sale_price"]):
            errors.append("Invalid sale price")
            
        if "penalty_amount" in data and not GameDataValidator.validate_lamports_amount(data["penalty_amount"]):
            errors.append("Invalid penalty amount")
            
        if "days_held" in data and (not isinstance(data["days_held"], int) or data["days_held"] < 0):
            errors.append("Invalid days held")
            
        return errors
        
    @staticmethod
    def validate_earnings_event(data: Dict[str, Any], event_type: str) -> List[str]:
        """
        Validate earnings-related event data.
        
        Args:
            data: Event data
            event_type: "updated" or "claimed"
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Common validation
        if "wallet" not in data:
            errors.append("Missing wallet field")
        elif not SolanaValidator.is_valid_pubkey(data["wallet"]):
            errors.append("Invalid wallet address")
            
        if event_type == "updated":
            required_fields = ["earnings_amount", "total_earnings"]
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing {field} field")
                elif not GameDataValidator.validate_lamports_amount(data[field]):
                    errors.append(f"Invalid {field}")
                    
        elif event_type == "claimed":
            required_fields = ["amount_claimed", "treasury_fee", "net_amount"]
            for field in required_fields:
                if field not in data:
                    errors.append(f"Missing {field} field")
                elif not GameDataValidator.validate_lamports_amount(data[field]):
                    errors.append(f"Invalid {field}")
                    
        return errors


class TransactionValidator:
    """Validator for transaction-level data."""
    
    @staticmethod
    def validate_transaction_signature(signature: str) -> bool:
        """Validate transaction signature format."""
        return SolanaValidator.is_valid_signature(signature)
        
    @staticmethod
    def validate_slot_number(slot: int) -> bool:
        """Validate slot number."""
        return isinstance(slot, int) and slot > 0
        
    @staticmethod
    def validate_block_time(block_time: Optional[datetime]) -> bool:
        """Validate block time."""
        if block_time is None:
            return True
        return isinstance(block_time, datetime) and block_time <= datetime.utcnow()
        
    @staticmethod
    def validate_transaction_success(success: bool, logs: List[str]) -> bool:
        """Validate transaction success status against logs."""
        if not isinstance(success, bool):
            return False
            
        # If transaction failed, logs should contain error information
        if not success:
            return any("error" in log.lower() or "failed" in log.lower() for log in logs)
            
        return True


def validate_event_data(event_type: str, data: Dict[str, Any]) -> List[str]:
    """
    Comprehensive event data validation.
    
    Args:
        event_type: Type of event to validate
        data: Event data to validate
        
    Returns:
        List of validation errors (empty if valid)
        
    Raises:
        ValidationError: If event type is not supported
    """
    validators = {
        "PlayerCreated": EventDataValidator.validate_player_created_event,
        "BusinessCreated": EventDataValidator.validate_business_created_event,
        "BusinessUpgraded": EventDataValidator.validate_business_upgraded_event,
        "BusinessSold": EventDataValidator.validate_business_sold_event,
        "EarningsUpdated": lambda d: EventDataValidator.validate_earnings_event(d, "updated"),
        "EarningsClaimed": lambda d: EventDataValidator.validate_earnings_event(d, "claimed"),
    }
    
    validator = validators.get(event_type)
    if not validator:
        raise ValidationError(f"Unsupported event type: {event_type}")
        
    return validator(data)


def validate_wallet_address(wallet: str) -> bool:
    """Validate wallet address format."""
    return SolanaValidator.is_valid_pubkey(wallet)


def validate_nft_mint(mint: str) -> bool:
    """Validate NFT mint address format."""
    return SolanaValidator.is_valid_pubkey(mint)


def is_valid_solana_address(address: str) -> bool:
    """
    Validate if a string is a valid Solana address.
    Alias for validate_wallet_address for compatibility.
    """
    return validate_wallet_address(address)
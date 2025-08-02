"""
Custom exception classes for the application.
Provides structured error handling across all modules.
"""

from typing import Any, Optional, Dict


class SolanaMafiaException(Exception):
    """Base exception class for Solana Mafia backend."""
    
    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ConfigurationError(SolanaMafiaException):
    """Raised when there's a configuration error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "CONFIGURATION_ERROR", details)


class DatabaseError(SolanaMafiaException):
    """Raised when there's a database error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "DATABASE_ERROR", details)


class SolanaError(SolanaMafiaException):
    """Raised when there's a Solana blockchain error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "SOLANA_ERROR", details)


class IndexerError(SolanaMafiaException):
    """Raised when there's an event indexer error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "INDEXER_ERROR", details)


class SchedulerError(SolanaMafiaException):
    """Raised when there's a scheduler error."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "SCHEDULER_ERROR", details)


class ValidationError(SolanaMafiaException):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details)


class NotFoundError(SolanaMafiaException):
    """Raised when a requested resource is not found."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "NOT_FOUND", details)


class AuthenticationError(SolanaMafiaException):
    """Raised when authentication fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHENTICATION_ERROR", details)


class AuthorizationError(SolanaMafiaException):
    """Raised when authorization fails."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "AUTHORIZATION_ERROR", details)


class RateLimitError(SolanaMafiaException):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "RATE_LIMIT_ERROR", details)


class ExternalServiceError(SolanaMafiaException):
    """Raised when an external service error occurs."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)


# Player-specific exceptions
class PlayerNotFoundError(NotFoundError):
    """Raised when a player is not found."""
    
    def __init__(self, wallet: str):
        super().__init__(
            f"Player not found: {wallet}",
            {"wallet": wallet}
        )


class BusinessNotFoundError(NotFoundError):
    """Raised when a business is not found."""
    
    def __init__(self, business_id: str):
        super().__init__(
            f"Business not found: {business_id}",
            {"business_id": business_id}
        )


class NFTNotFoundError(NotFoundError):
    """Raised when an NFT is not found."""
    
    def __init__(self, mint: str):
        super().__init__(
            f"NFT not found: {mint}",
            {"mint": mint}
        )


# Business logic exceptions
class InsufficientFundsError(ValidationError):
    """Raised when there are insufficient funds for an operation."""
    
    def __init__(self, required: int, available: int):
        super().__init__(
            f"Insufficient funds: required {required}, available {available}",
            {"required": required, "available": available}
        )


class InvalidSlotError(ValidationError):
    """Raised when an invalid slot operation is attempted."""
    
    def __init__(self, slot_index: int, reason: str):
        super().__init__(
            f"Invalid slot operation at index {slot_index}: {reason}",
            {"slot_index": slot_index, "reason": reason}
        )


class BusinessOwnershipError(AuthorizationError):
    """Raised when business ownership validation fails."""
    
    def __init__(self, wallet: str, business_mint: str):
        super().__init__(
            f"Wallet {wallet} does not own business NFT {business_mint}",
            {"wallet": wallet, "business_mint": business_mint}
        )
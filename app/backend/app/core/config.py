"""
Configuration management using Pydantic Settings.
Supports multiple environments: development, staging, production.
"""

from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment-based configuration."""
    
    # Application
    app_name: str = "Solana Mafia Backend"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # API
    api_v1_prefix: str = "/api/v1"
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Database
    database_url: str = Field(
        default="postgresql://solana_mafia:password@localhost:5432/solana_mafia_db",
        env="DATABASE_URL"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 20
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_prefix: str = "solana_mafia:"
    
    # Solana
    solana_rpc_url: str = Field(
        default="https://api.devnet.solana.com",
        env="SOLANA_RPC_URL"
    )
    solana_program_id: str = Field(
        default="3Ly6bEWRfKyVGwrRN27gHhBogo1K4HbZyk69KHW9AUx7",
        env="SOLANA_PROGRAM_ID"
    )
    solana_commitment: str = "confirmed"
    
    # Indexer settings
    indexer_batch_size: int = 1000
    indexer_poll_interval: int = 5  # seconds
    indexer_max_retries: int = 3
    indexer_retry_delay: int = 10  # seconds
    
    # Scheduler settings
    scheduler_enabled: bool = True
    scheduler_interval: int = 60  # seconds
    scheduler_batch_size: int = 50
    scheduler_max_workers: int = 5
    
    # WebSocket
    websocket_enabled: bool = True
    websocket_host: str = "127.0.0.1"
    websocket_port: int = 8001
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or console
    log_file: Optional[str] = None
    
    # Security
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    access_token_expire_minutes: int = 30
    
    # Rate limiting
    rate_limit_enabled: bool = True
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds
    
    @validator("environment")
    def validate_environment(cls, v: str) -> str:
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v.upper()
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


class DatabaseConfig:
    """Database-specific configuration."""
    
    @staticmethod
    def get_database_url(async_driver: bool = True) -> str:
        """Get database URL with appropriate driver."""
        url = settings.database_url
        if async_driver and url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://")
        elif not async_driver and url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql://")
        return url
    
    @staticmethod
    def get_engine_config() -> dict:
        """Get SQLAlchemy engine configuration."""
        return {
            "pool_size": settings.database_pool_size,
            "max_overflow": settings.database_max_overflow,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        }


class SolanaConfig:
    """Solana-specific configuration and constants."""
    
    # Event signatures from the Solana program
    EVENT_SIGNATURES = {
        "PlayerCreated": "player_created",
        "BusinessCreated": "business_created", 
        "BusinessUpgraded": "business_upgraded",
        "BusinessSold": "business_sold",
        "EarningsUpdated": "earnings_updated",
        "EarningsClaimed": "earnings_claimed",
        "BusinessNFTMinted": "business_nft_minted",
        "BusinessNFTBurned": "business_nft_burned",
        "BusinessNFTUpgraded": "business_nft_upgraded",
        "BusinessTransferred": "business_transferred",
        "BusinessDeactivated": "business_deactivated",
        "SlotUnlocked": "slot_unlocked",
        "PremiumSlotPurchased": "premium_slot_purchased",
        "ReferralBonusAdded": "referral_bonus_added",
    }
    
    @staticmethod
    def get_rpc_config() -> dict:
        """Get Solana RPC client configuration."""
        return {
            "endpoint": settings.solana_rpc_url,
            "commitment": settings.solana_commitment,
            "timeout": 30,
        }
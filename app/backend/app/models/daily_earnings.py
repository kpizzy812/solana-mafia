"""
Daily earnings tracking models for monitoring and ensuring all players receive their earnings.
"""

from datetime import datetime, date
from typing import List, Optional
from enum import Enum

from sqlalchemy import Column, Integer, String, DateTime, Date, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship

from app.core.database import Base


class EarningsRunStatus(str, Enum):
    """Status of a daily earnings run."""
    STARTED = "started"
    IN_PROGRESS = "in_progress" 
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"


class PlayerEarningsStatus(str, Enum):
    """Status of individual player earnings for a specific day."""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    RETRIED = "retried"
    MANUAL_FIX_NEEDED = "manual_fix_needed"


class DailyEarningsRun(Base):
    """
    Tracks each daily earnings processing run to ensure all players are processed.
    """
    __tablename__ = "daily_earnings_runs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Date information
    earnings_date = Column(Date, nullable=False, comment="Date for which earnings are being processed")
    
    # Run metadata
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="When the run started")
    completed_at = Column(DateTime, nullable=True, comment="When the run completed")
    status = Column(String(20), nullable=False, default=EarningsRunStatus.STARTED, comment="Current status of the run")
    
    # Statistics
    total_players_found = Column(Integer, nullable=False, default=0, comment="Total players with businesses found")
    players_processed = Column(Integer, nullable=False, default=0, comment="Players successfully processed")
    players_failed = Column(Integer, nullable=False, default=0, comment="Players that failed processing")
    players_skipped = Column(Integer, nullable=False, default=0, comment="Players skipped (no businesses, etc)")
    
    # Processing details
    batch_size = Column(Integer, nullable=False, default=500, comment="Batch size used for processing")
    total_batches = Column(Integer, nullable=False, default=0, comment="Total number of batches processed")
    processing_duration_seconds = Column(Integer, nullable=True, comment="Total processing time in seconds")
    
    # Error tracking
    error_message = Column(Text, nullable=True, comment="Error message if run failed")
    retry_count = Column(Integer, nullable=False, default=0, comment="Number of retry attempts")
    
    # Admin fields
    triggered_by = Column(String(50), nullable=False, default="scheduler", comment="What triggered this run (scheduler/manual/retry)")
    processed_by_admin = Column(String(44), nullable=True, comment="Admin wallet who manually triggered if applicable")
    
    # Relationships
    player_statuses = relationship("PlayerDailyEarningsStatus", back_populates="earnings_run", cascade="all, delete-orphan")
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<DailyEarningsRun(id={self.id}, date={self.earnings_date}, status={self.status})>"
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.total_players_found == 0:
            return 0.0
        return (self.players_processed / self.total_players_found) * 100
    
    @property
    def is_complete(self) -> bool:
        """Check if run is completed (successfully or failed)."""
        return self.status in [EarningsRunStatus.COMPLETED, EarningsRunStatus.FAILED]
    
    @property
    def has_failed_players(self) -> bool:
        """Check if any players failed processing."""
        return self.players_failed > 0


class PlayerDailyEarningsStatus(Base):
    """
    Tracks the earnings status for each player on each day to ensure no one is missed.
    """
    __tablename__ = "player_daily_earnings_status"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Player and date
    player_wallet = Column(String(44), nullable=False, comment="Player wallet address")
    earnings_date = Column(Date, nullable=False, comment="Date for which earnings are tracked")
    earnings_run_id = Column(Integer, ForeignKey("daily_earnings_runs.id"), nullable=False, comment="Associated earnings run")
    
    # Status tracking
    status = Column(String(30), nullable=False, default=PlayerEarningsStatus.PENDING, comment="Processing status for this player")
    
    # Business information at time of processing
    businesses_count = Column(Integer, nullable=False, default=0, comment="Number of businesses player had")
    total_business_levels = Column(Integer, nullable=False, default=0, comment="Sum of all business levels")
    expected_earnings_lamports = Column(Integer, nullable=False, default=0, comment="Expected earnings amount in lamports")
    
    # Processing results
    actual_earnings_applied = Column(Integer, nullable=True, comment="Actual earnings applied in lamports")
    processing_attempts = Column(Integer, nullable=False, default=0, comment="Number of processing attempts")
    
    # Timing
    first_attempt_at = Column(DateTime, nullable=True, comment="When first processing attempt was made")
    last_attempt_at = Column(DateTime, nullable=True, comment="When last processing attempt was made")
    success_at = Column(DateTime, nullable=True, comment="When processing succeeded")
    
    # Error tracking
    error_message = Column(Text, nullable=True, comment="Last error message if processing failed")
    blockchain_error = Column(Boolean, nullable=False, default=False, comment="Whether error was blockchain-related")
    needs_manual_review = Column(Boolean, nullable=False, default=False, comment="Whether this player needs manual admin review")
    
    # Admin resolution
    manually_resolved = Column(Boolean, nullable=False, default=False, comment="Whether admin manually resolved this")
    resolved_by_admin = Column(String(44), nullable=True, comment="Admin wallet who resolved if manually fixed")
    resolution_note = Column(Text, nullable=True, comment="Admin note about resolution")
    
    # Relationships
    earnings_run = relationship("DailyEarningsRun", back_populates="player_statuses")
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<PlayerDailyEarningsStatus(player={self.player_wallet}, date={self.earnings_date}, status={self.status})>"
    
    @property
    def is_failed(self) -> bool:
        """Check if player processing failed."""
        return self.status in [PlayerEarningsStatus.FAILED, PlayerEarningsStatus.MANUAL_FIX_NEEDED]
    
    @property
    def is_successful(self) -> bool:
        """Check if player processing succeeded."""
        return self.status == PlayerEarningsStatus.SUCCESS
    
    @property
    def earnings_variance_percentage(self) -> float:
        """Calculate variance between expected and actual earnings."""
        if self.expected_earnings_lamports == 0 or not self.actual_earnings_applied:
            return 0.0
        
        variance = abs(self.expected_earnings_lamports - self.actual_earnings_applied)
        return (variance / self.expected_earnings_lamports) * 100


# Database indexes for performance
Index('idx_daily_earnings_runs_date_status', DailyEarningsRun.earnings_date, DailyEarningsRun.status)
Index('idx_daily_earnings_runs_status', DailyEarningsRun.status)

Index('idx_player_earnings_status_date', PlayerDailyEarningsStatus.earnings_date)
Index('idx_player_earnings_status_player_date', PlayerDailyEarningsStatus.player_wallet, PlayerDailyEarningsStatus.earnings_date)
Index('idx_player_earnings_status_failed', PlayerDailyEarningsStatus.status, PlayerDailyEarningsStatus.needs_manual_review)
Index('idx_player_earnings_status_run', PlayerDailyEarningsStatus.earnings_run_id)
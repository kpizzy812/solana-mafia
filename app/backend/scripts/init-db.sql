-- Initialize database for Solana Mafia
-- This script runs when the PostgreSQL container starts

-- Create additional indexes that might be needed
-- Note: Tables will be created by SQLAlchemy migrations

-- Enable UUID extension if needed in the future
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create a function to update timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create indexes for performance after tables are created
-- These will be created by migrations, but documented here for reference

/*
-- Performance indexes (created by SQLAlchemy)
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_events_slot_processing 
ON events (slot) WHERE status = 'pending';

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_earnings_schedule_due 
ON earnings_schedule (next_update_time) WHERE is_active = true;

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_players_earnings_due 
ON players (next_earnings_time) WHERE is_active = true;
*/

-- Create materialized view for analytics (optional)
-- This can be created later when we have data
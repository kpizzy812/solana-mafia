BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 001

CREATE TYPE businesstype AS ENUM ('LEMONADE_STAND', 'CAR_WASH', 'RESTAURANT', 'TECH_STARTUP', 'CRYPTO_EXCHANGE');

CREATE TYPE slottype AS ENUM ('BASIC', 'PREMIUM', 'VIP', 'LEGENDARY');

CREATE TYPE eventtype AS ENUM ('PLAYER_CREATED', 'BUSINESS_CREATED', 'BUSINESS_UPGRADED', 'BUSINESS_SOLD', 'EARNINGS_UPDATED', 'EARNINGS_CLAIMED', 'BUSINESS_NFT_MINTED', 'BUSINESS_NFT_BURNED', 'BUSINESS_NFT_UPGRADED', 'BUSINESS_TRANSFERRED', 'BUSINESS_DEACTIVATED', 'SLOT_UNLOCKED', 'PREMIUM_SLOT_PURCHASED', 'BUSINESS_CREATED_IN_SLOT', 'BUSINESS_UPGRADED_IN_SLOT', 'BUSINESS_SOLD_FROM_SLOT', 'REFERRAL_BONUS_ADDED');

CREATE TYPE eventstatus AS ENUM ('PENDING', 'PROCESSING', 'PROCESSED', 'FAILED', 'SKIPPED');

CREATE TYPE earningsstatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'SKIPPED');

CREATE TABLE players (
    wallet VARCHAR(44) NOT NULL, 
    total_invested BIGINT NOT NULL, 
    total_upgrade_spent BIGINT NOT NULL, 
    total_slot_spent BIGINT NOT NULL, 
    total_earned BIGINT NOT NULL, 
    pending_earnings BIGINT NOT NULL, 
    pending_referral_earnings BIGINT NOT NULL, 
    unlocked_slots_count INTEGER NOT NULL, 
    premium_slots_count INTEGER NOT NULL, 
    has_paid_entry BOOLEAN NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    first_business_time TIMESTAMP WITHOUT TIME ZONE, 
    next_earnings_time TIMESTAMP WITHOUT TIME ZONE, 
    last_earnings_update TIMESTAMP WITHOUT TIME ZONE, 
    earnings_interval INTEGER NOT NULL, 
    referrer_wallet VARCHAR(44), 
    referral_count INTEGER NOT NULL, 
    transaction_signature VARCHAR(88), 
    on_chain_created_at TIMESTAMP WITHOUT TIME ZONE, 
    last_sync_at TIMESTAMP WITHOUT TIME ZONE, 
    sync_version INTEGER NOT NULL, 
    roi_percentage DECIMAL(10, 4), 
    daily_earnings_estimate BIGINT NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (wallet)
);

COMMENT ON COLUMN players.wallet IS 'Player''s wallet public key';

COMMENT ON COLUMN players.total_invested IS 'Total amount invested in lamports';

COMMENT ON COLUMN players.total_upgrade_spent IS 'Total spent on upgrades in lamports';

COMMENT ON COLUMN players.total_slot_spent IS 'Total spent on slots in lamports';

COMMENT ON COLUMN players.total_earned IS 'Total earnings claimed in lamports';

COMMENT ON COLUMN players.pending_earnings IS 'Pending earnings in lamports';

COMMENT ON COLUMN players.pending_referral_earnings IS 'Pending referral earnings in lamports';

COMMENT ON COLUMN players.unlocked_slots_count IS 'Number of unlocked regular slots';

COMMENT ON COLUMN players.premium_slots_count IS 'Number of premium slots owned';

COMMENT ON COLUMN players.has_paid_entry IS 'Whether player has paid entry fee';

COMMENT ON COLUMN players.is_active IS 'Whether player account is active';

COMMENT ON COLUMN players.first_business_time IS 'When player created their first business';

COMMENT ON COLUMN players.next_earnings_time IS 'Next scheduled earnings update';

COMMENT ON COLUMN players.last_earnings_update IS 'Last earnings update timestamp';

COMMENT ON COLUMN players.earnings_interval IS 'Earnings update interval in seconds';

COMMENT ON COLUMN players.referrer_wallet IS 'Wallet of referring player';

COMMENT ON COLUMN players.referral_count IS 'Number of players referred';

COMMENT ON COLUMN players.transaction_signature IS 'Transaction signature when player was created';

COMMENT ON COLUMN players.on_chain_created_at IS 'Creation timestamp from on-chain data';

COMMENT ON COLUMN players.last_sync_at IS 'Last synchronization with on-chain data';

COMMENT ON COLUMN players.sync_version IS 'Version for sync conflict resolution';

COMMENT ON COLUMN players.roi_percentage IS 'Return on investment percentage';

COMMENT ON COLUMN players.daily_earnings_estimate IS 'Estimated daily earnings in lamports';

CREATE TYPE businesstype AS ENUM ('LEMONADE_STAND', 'CAR_WASH', 'RESTAURANT', 'TECH_STARTUP', 'CRYPTO_EXCHANGE');

CREATE TABLE business_nfts (
    mint VARCHAR(44) NOT NULL, 
    player_wallet VARCHAR(44) NOT NULL, 
    name VARCHAR(200) NOT NULL, 
    symbol VARCHAR(10) NOT NULL, 
    uri TEXT NOT NULL, 
    business_type businesstype NOT NULL, 
    level INTEGER NOT NULL, 
    serial_number BIGINT NOT NULL, 
    base_invested_amount BIGINT NOT NULL, 
    total_invested_amount BIGINT NOT NULL, 
    daily_rate INTEGER NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    is_burned BOOLEAN NOT NULL, 
    minted_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    burned_at TIMESTAMP WITHOUT TIME ZONE, 
    last_transfer_at TIMESTAMP WITHOUT TIME ZONE, 
    mint_signature VARCHAR(88) NOT NULL, 
    burn_signature VARCHAR(88), 
    metadata_json JSON, 
    image_url TEXT, 
    previous_owner VARCHAR(44), 
    transfer_count INTEGER NOT NULL, 
    last_sync_at TIMESTAMP WITHOUT TIME ZONE, 
    ownership_verified_at TIMESTAMP WITHOUT TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (mint), 
    FOREIGN KEY(player_wallet) REFERENCES players (wallet) ON DELETE CASCADE
);

COMMENT ON COLUMN business_nfts.mint IS 'NFT mint address';

COMMENT ON COLUMN business_nfts.player_wallet IS 'Current owner''s wallet';

COMMENT ON COLUMN business_nfts.name IS 'NFT name';

COMMENT ON COLUMN business_nfts.symbol IS 'NFT symbol';

COMMENT ON COLUMN business_nfts.uri IS 'Metadata URI';

COMMENT ON COLUMN business_nfts.business_type IS 'Type of business this NFT represents';

COMMENT ON COLUMN business_nfts.level IS 'Business level';

COMMENT ON COLUMN business_nfts.serial_number IS 'Unique serial number for this business type';

COMMENT ON COLUMN business_nfts.base_invested_amount IS 'Base investment amount in lamports';

COMMENT ON COLUMN business_nfts.total_invested_amount IS 'Total invested including upgrades in lamports';

COMMENT ON COLUMN business_nfts.daily_rate IS 'Daily rate in basis points';

COMMENT ON COLUMN business_nfts.is_active IS 'Whether NFT is active';

COMMENT ON COLUMN business_nfts.is_burned IS 'Whether NFT has been burned';

COMMENT ON COLUMN business_nfts.minted_at IS 'When NFT was minted';

COMMENT ON COLUMN business_nfts.burned_at IS 'When NFT was burned';

COMMENT ON COLUMN business_nfts.last_transfer_at IS 'Last transfer timestamp';

COMMENT ON COLUMN business_nfts.mint_signature IS 'Transaction signature when NFT was minted';

COMMENT ON COLUMN business_nfts.burn_signature IS 'Transaction signature when NFT was burned';

COMMENT ON COLUMN business_nfts.metadata_json IS 'Cached metadata JSON';

COMMENT ON COLUMN business_nfts.image_url IS 'Direct image URL';

COMMENT ON COLUMN business_nfts.previous_owner IS 'Previous owner wallet';

COMMENT ON COLUMN business_nfts.transfer_count IS 'Number of times NFT has been transferred';

COMMENT ON COLUMN business_nfts.last_sync_at IS 'Last sync with on-chain data';

COMMENT ON COLUMN business_nfts.ownership_verified_at IS 'Last ownership verification timestamp';

CREATE TABLE businesses (
    id SERIAL NOT NULL, 
    player_wallet VARCHAR(44) NOT NULL, 
    nft_mint VARCHAR(44), 
    business_type businesstype NOT NULL, 
    level INTEGER NOT NULL, 
    base_cost BIGINT NOT NULL, 
    total_invested_amount BIGINT NOT NULL, 
    upgrade_costs TEXT, 
    daily_rate INTEGER NOT NULL, 
    last_claim_time TIMESTAMP WITHOUT TIME ZONE, 
    total_earnings_generated BIGINT NOT NULL, 
    is_active BOOLEAN NOT NULL, 
    slot_index INTEGER, 
    creation_signature VARCHAR(88), 
    on_chain_created_at TIMESTAMP WITHOUT TIME ZONE, 
    last_sync_at TIMESTAMP WITHOUT TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(nft_mint) REFERENCES business_nfts (mint) ON DELETE SET NULL, 
    FOREIGN KEY(player_wallet) REFERENCES players (wallet) ON DELETE CASCADE
);

COMMENT ON COLUMN businesses.player_wallet IS 'Owner''s wallet address';

COMMENT ON COLUMN businesses.nft_mint IS 'Associated NFT mint address';

COMMENT ON COLUMN businesses.business_type IS 'Type of business';

COMMENT ON COLUMN businesses.level IS 'Business upgrade level';

COMMENT ON COLUMN businesses.base_cost IS 'Base cost of business in lamports';

COMMENT ON COLUMN businesses.total_invested_amount IS 'Total invested including upgrades in lamports';

COMMENT ON COLUMN businesses.upgrade_costs IS 'JSON array of upgrade costs';

COMMENT ON COLUMN businesses.daily_rate IS 'Daily rate in basis points (100 = 1%)';

COMMENT ON COLUMN businesses.last_claim_time IS 'Last earnings claim timestamp';

COMMENT ON COLUMN businesses.total_earnings_generated IS 'Total earnings generated by this business';

COMMENT ON COLUMN businesses.is_active IS 'Whether business is active and earning';

COMMENT ON COLUMN businesses.slot_index IS 'Index of slot this business occupies';

COMMENT ON COLUMN businesses.creation_signature IS 'Transaction signature when business was created';

COMMENT ON COLUMN businesses.on_chain_created_at IS 'Creation timestamp from blockchain';

COMMENT ON COLUMN businesses.last_sync_at IS 'Last sync with on-chain data';

CREATE TYPE slottype AS ENUM ('BASIC', 'PREMIUM', 'VIP', 'LEGENDARY');

CREATE TABLE business_slots (
    id SERIAL NOT NULL, 
    player_wallet VARCHAR(44) NOT NULL, 
    slot_index INTEGER NOT NULL, 
    slot_type slottype NOT NULL, 
    is_unlocked BOOLEAN NOT NULL, 
    unlock_cost_paid BIGINT NOT NULL, 
    business_id INTEGER, 
    yield_bonus INTEGER NOT NULL, 
    sell_fee_discount INTEGER NOT NULL, 
    unlock_signature VARCHAR(88), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(business_id) REFERENCES businesses (id) ON DELETE SET NULL, 
    FOREIGN KEY(player_wallet) REFERENCES players (wallet) ON DELETE CASCADE
);

COMMENT ON COLUMN business_slots.player_wallet IS 'Owner''s wallet address';

COMMENT ON COLUMN business_slots.slot_index IS 'Slot index (0-based)';

COMMENT ON COLUMN business_slots.slot_type IS 'Type of slot';

COMMENT ON COLUMN business_slots.is_unlocked IS 'Whether slot is unlocked';

COMMENT ON COLUMN business_slots.unlock_cost_paid IS 'Cost paid to unlock this slot';

COMMENT ON COLUMN business_slots.business_id IS 'Business currently in this slot';

COMMENT ON COLUMN business_slots.yield_bonus IS 'Yield bonus in basis points';

COMMENT ON COLUMN business_slots.sell_fee_discount IS 'Sell fee discount percentage';

COMMENT ON COLUMN business_slots.unlock_signature IS 'Transaction signature when slot was unlocked';

CREATE TYPE eventtype AS ENUM ('PLAYER_CREATED', 'BUSINESS_CREATED', 'BUSINESS_UPGRADED', 'BUSINESS_SOLD', 'EARNINGS_UPDATED', 'EARNINGS_CLAIMED', 'BUSINESS_NFT_MINTED', 'BUSINESS_NFT_BURNED', 'BUSINESS_NFT_UPGRADED', 'BUSINESS_TRANSFERRED', 'BUSINESS_DEACTIVATED', 'SLOT_UNLOCKED', 'PREMIUM_SLOT_PURCHASED', 'BUSINESS_CREATED_IN_SLOT', 'BUSINESS_UPGRADED_IN_SLOT', 'BUSINESS_SOLD_FROM_SLOT', 'REFERRAL_BONUS_ADDED');

CREATE TYPE eventstatus AS ENUM ('PENDING', 'PROCESSING', 'PROCESSED', 'FAILED', 'SKIPPED');

CREATE TABLE events (
    id SERIAL NOT NULL, 
    event_type eventtype NOT NULL, 
    transaction_signature VARCHAR(88) NOT NULL, 
    instruction_index INTEGER NOT NULL, 
    event_index INTEGER NOT NULL, 
    slot BIGINT NOT NULL, 
    block_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    raw_data JSON NOT NULL, 
    parsed_data JSON, 
    player_wallet VARCHAR(44), 
    business_mint VARCHAR(44), 
    status eventstatus NOT NULL, 
    processed_at TIMESTAMP WITHOUT TIME ZONE, 
    error_message TEXT, 
    retry_count INTEGER NOT NULL, 
    indexer_version VARCHAR(20) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

COMMENT ON COLUMN events.event_type IS 'Type of event';

COMMENT ON COLUMN events.transaction_signature IS 'Transaction signature';

COMMENT ON COLUMN events.instruction_index IS 'Instruction index within transaction';

COMMENT ON COLUMN events.event_index IS 'Event index within instruction';

COMMENT ON COLUMN events.slot IS 'Blockchain slot number';

COMMENT ON COLUMN events.block_time IS 'Block timestamp';

COMMENT ON COLUMN events.raw_data IS 'Raw event data from blockchain';

COMMENT ON COLUMN events.parsed_data IS 'Parsed and structured event data';

COMMENT ON COLUMN events.player_wallet IS 'Related player wallet';

COMMENT ON COLUMN events.business_mint IS 'Related business NFT mint';

COMMENT ON COLUMN events.status IS 'Processing status';

COMMENT ON COLUMN events.processed_at IS 'When event was processed';

COMMENT ON COLUMN events.error_message IS 'Error message if processing failed';

COMMENT ON COLUMN events.retry_count IS 'Number of processing retries';

COMMENT ON COLUMN events.indexer_version IS 'Version of indexer that processed this event';

CREATE TYPE earningsstatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'SKIPPED');

CREATE TABLE earnings_schedule (
    id SERIAL NOT NULL, 
    player_wallet VARCHAR(44) NOT NULL, 
    next_update_time TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    update_interval INTEGER NOT NULL, 
    status earningsstatus NOT NULL, 
    last_update_attempt TIMESTAMP WITHOUT TIME ZONE, 
    last_successful_update TIMESTAMP WITHOUT TIME ZONE, 
    consecutive_failures INTEGER NOT NULL, 
    last_error TEXT, 
    is_active BOOLEAN NOT NULL, 
    priority INTEGER NOT NULL, 
    average_processing_time INTEGER, 
    total_updates INTEGER NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(player_wallet) REFERENCES players (wallet) ON DELETE CASCADE
);

COMMENT ON COLUMN earnings_schedule.player_wallet IS 'Player wallet address';

COMMENT ON COLUMN earnings_schedule.next_update_time IS 'Next scheduled update time';

COMMENT ON COLUMN earnings_schedule.update_interval IS 'Update interval in seconds';

COMMENT ON COLUMN earnings_schedule.status IS 'Current processing status';

COMMENT ON COLUMN earnings_schedule.last_update_attempt IS 'Last update attempt timestamp';

COMMENT ON COLUMN earnings_schedule.last_successful_update IS 'Last successful update timestamp';

COMMENT ON COLUMN earnings_schedule.consecutive_failures IS 'Number of consecutive failures';

COMMENT ON COLUMN earnings_schedule.last_error IS 'Last error message';

COMMENT ON COLUMN earnings_schedule.is_active IS 'Whether this schedule is active';

COMMENT ON COLUMN earnings_schedule.priority IS 'Processing priority (1=highest, 10=lowest)';

COMMENT ON COLUMN earnings_schedule.average_processing_time IS 'Average processing time in milliseconds';

COMMENT ON COLUMN earnings_schedule.total_updates IS 'Total number of successful updates';

CREATE TABLE earnings_history (
    id SERIAL NOT NULL, 
    player_wallet VARCHAR(44) NOT NULL, 
    event_type VARCHAR(20) NOT NULL, 
    amount BIGINT NOT NULL, 
    previous_balance BIGINT NOT NULL, 
    new_balance BIGINT NOT NULL, 
    base_earnings BIGINT NOT NULL, 
    slot_bonus_earnings BIGINT NOT NULL, 
    referral_earnings BIGINT NOT NULL, 
    business_count INTEGER NOT NULL, 
    transaction_signature VARCHAR(88), 
    processing_time_ms INTEGER, 
    indexer_version VARCHAR(20) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(player_wallet) REFERENCES players (wallet) ON DELETE CASCADE
);

COMMENT ON COLUMN earnings_history.player_wallet IS 'Player wallet address';

COMMENT ON COLUMN earnings_history.event_type IS 'Type of earnings event (update, claim)';

COMMENT ON COLUMN earnings_history.amount IS 'Amount in lamports';

COMMENT ON COLUMN earnings_history.previous_balance IS 'Previous pending earnings balance';

COMMENT ON COLUMN earnings_history.new_balance IS 'New pending earnings balance';

COMMENT ON COLUMN earnings_history.base_earnings IS 'Base business earnings';

COMMENT ON COLUMN earnings_history.slot_bonus_earnings IS 'Bonus earnings from premium slots';

COMMENT ON COLUMN earnings_history.referral_earnings IS 'Referral bonus earnings';

COMMENT ON COLUMN earnings_history.business_count IS 'Number of active businesses at time of update';

COMMENT ON COLUMN earnings_history.transaction_signature IS 'Related blockchain transaction';

COMMENT ON COLUMN earnings_history.processing_time_ms IS 'Processing time in milliseconds';

COMMENT ON COLUMN earnings_history.indexer_version IS 'Version of system that processed this';

CREATE INDEX idx_business_nft_player_active ON business_nfts (player_wallet, is_active);

CREATE INDEX idx_business_nft_business_type ON business_nfts (business_type, level);

CREATE INDEX idx_business_nft_serial ON business_nfts (business_type, serial_number);

CREATE INDEX idx_business_nft_minted_at ON business_nfts (minted_at);

CREATE INDEX idx_business_nft_burned ON business_nfts (is_burned);

CREATE INDEX idx_business_nft_sync ON business_nfts (last_sync_at);

CREATE INDEX idx_business_player_active ON businesses (player_wallet, is_active);

CREATE INDEX idx_business_type_level ON businesses (business_type, level);

CREATE INDEX idx_business_nft ON businesses (nft_mint);

CREATE INDEX idx_business_slot ON businesses (player_wallet, slot_index);

CREATE UNIQUE INDEX idx_slot_player_index ON business_slots (player_wallet, slot_index);

CREATE INDEX idx_slot_player_unlocked ON business_slots (player_wallet, is_unlocked);

CREATE INDEX idx_slot_type ON business_slots (slot_type);

CREATE INDEX idx_earnings_history_player_time ON earnings_history (player_wallet, created_at);

CREATE INDEX idx_earnings_history_event_type ON earnings_history (event_type, created_at);

CREATE INDEX idx_earnings_history_amount ON earnings_history (amount);

CREATE INDEX idx_earnings_history_signature ON earnings_history (transaction_signature);

CREATE INDEX idx_earnings_schedule_next_update ON earnings_schedule (next_update_time, is_active);

CREATE INDEX idx_earnings_schedule_status ON earnings_schedule (status, next_update_time);

CREATE INDEX idx_earnings_schedule_failures ON earnings_schedule (consecutive_failures, is_active);

CREATE INDEX idx_earnings_schedule_priority ON earnings_schedule (priority, next_update_time);

CREATE INDEX idx_event_type_slot ON events (event_type, slot);

CREATE INDEX idx_event_player_type ON events (player_wallet, event_type);

CREATE UNIQUE INDEX idx_event_signature_unique ON events (transaction_signature, instruction_index, event_index);

CREATE INDEX idx_event_status_created ON events (status, created_at);

CREATE INDEX idx_event_block_time ON events (block_time);

CREATE INDEX idx_event_business_mint ON events (business_mint);

CREATE INDEX idx_event_pending_retry ON events (status, retry_count);

CREATE INDEX idx_player_next_earnings ON players (next_earnings_time);

CREATE INDEX idx_player_active_earnings ON players (is_active, next_earnings_time);

CREATE INDEX idx_player_created_at ON players (created_at);

CREATE INDEX idx_player_referrer ON players (referrer_wallet);

CREATE INDEX idx_player_sync ON players (last_sync_at);

INSERT INTO alembic_version (version_num) VALUES ('001') RETURNING alembic_version.version_num;

COMMIT;


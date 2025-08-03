"""Initial migration - all models

Revision ID: 001
Revises: 
Create Date: 2024-08-02 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE businesstype AS ENUM ('TOBACCO_SHOP', 'FUNERAL_SERVICE', 'CAR_WORKSHOP', 'ITALIAN_RESTAURANT', 'GENTLEMEN_CLUB', 'CHARITY_FUND')")
    op.execute("CREATE TYPE slottype AS ENUM ('BASIC', 'PREMIUM', 'VIP', 'LEGENDARY')")
    op.execute("CREATE TYPE eventtype AS ENUM ('PLAYER_CREATED', 'BUSINESS_CREATED', 'BUSINESS_UPGRADED', 'BUSINESS_SOLD', 'EARNINGS_UPDATED', 'EARNINGS_CLAIMED', 'BUSINESS_NFT_MINTED', 'BUSINESS_NFT_BURNED', 'BUSINESS_NFT_UPGRADED', 'BUSINESS_TRANSFERRED', 'BUSINESS_DEACTIVATED', 'SLOT_UNLOCKED', 'PREMIUM_SLOT_PURCHASED', 'BUSINESS_CREATED_IN_SLOT', 'BUSINESS_UPGRADED_IN_SLOT', 'BUSINESS_SOLD_FROM_SLOT', 'REFERRAL_BONUS_ADDED')")
    op.execute("CREATE TYPE eventstatus AS ENUM ('PENDING', 'PROCESSING', 'PROCESSED', 'FAILED', 'SKIPPED')")
    op.execute("CREATE TYPE earningsstatus AS ENUM ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'SKIPPED')")

    # Create players table
    op.create_table('players',
        sa.Column('wallet', sa.String(length=44), nullable=False, comment='Player\'s wallet public key'),
        sa.Column('total_invested', sa.BigInteger(), nullable=False, comment='Total amount invested in lamports'),
        sa.Column('total_upgrade_spent', sa.BigInteger(), nullable=False, comment='Total spent on upgrades in lamports'),
        sa.Column('total_slot_spent', sa.BigInteger(), nullable=False, comment='Total spent on slots in lamports'),
        sa.Column('total_earned', sa.BigInteger(), nullable=False, comment='Total earnings claimed in lamports'),
        sa.Column('pending_earnings', sa.BigInteger(), nullable=False, comment='Pending earnings in lamports'),
        sa.Column('pending_referral_earnings', sa.BigInteger(), nullable=False, comment='Pending referral earnings in lamports'),
        sa.Column('unlocked_slots_count', sa.Integer(), nullable=False, comment='Number of unlocked regular slots'),
        sa.Column('premium_slots_count', sa.Integer(), nullable=False, comment='Number of premium slots owned'),
        sa.Column('has_paid_entry', sa.Boolean(), nullable=False, comment='Whether player has paid entry fee'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Whether player account is active'),
        sa.Column('first_business_time', sa.DateTime(), nullable=True, comment='When player created their first business'),
        sa.Column('next_earnings_time', sa.DateTime(), nullable=True, comment='Next scheduled earnings update'),
        sa.Column('last_earnings_update', sa.DateTime(), nullable=True, comment='Last earnings update timestamp'),
        sa.Column('earnings_interval', sa.Integer(), nullable=False, comment='Earnings update interval in seconds'),
        sa.Column('referrer_wallet', sa.String(length=44), nullable=True, comment='Wallet of referring player'),
        sa.Column('referral_count', sa.Integer(), nullable=False, comment='Number of players referred'),
        sa.Column('transaction_signature', sa.String(length=88), nullable=True, comment='Transaction signature when player was created'),
        sa.Column('on_chain_created_at', sa.DateTime(), nullable=True, comment='Creation timestamp from on-chain data'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True, comment='Last synchronization with on-chain data'),
        sa.Column('sync_version', sa.Integer(), nullable=False, comment='Version for sync conflict resolution'),
        sa.Column('roi_percentage', sa.DECIMAL(precision=10, scale=4), nullable=True, comment='Return on investment percentage'),
        sa.Column('daily_earnings_estimate', sa.BigInteger(), nullable=False, comment='Estimated daily earnings in lamports'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('wallet')
    )

    # Create business_nfts table
    op.create_table('business_nfts',
        sa.Column('mint', sa.String(length=44), nullable=False, comment='NFT mint address'),
        sa.Column('player_wallet', sa.String(length=44), nullable=False, comment='Current owner\'s wallet'),
        sa.Column('name', sa.String(length=200), nullable=False, comment='NFT name'),
        sa.Column('symbol', sa.String(length=10), nullable=False, comment='NFT symbol'),
        sa.Column('uri', sa.Text(), nullable=False, comment='Metadata URI'),
        sa.Column('business_type', postgresql.ENUM('TOBACCO_SHOP', 'FUNERAL_SERVICE', 'CAR_WORKSHOP', 'ITALIAN_RESTAURANT', 'GENTLEMEN_CLUB', 'CHARITY_FUND', name='businesstype'), nullable=False, comment='Type of business this NFT represents'),
        sa.Column('level', sa.Integer(), nullable=False, comment='Business level'),
        sa.Column('serial_number', sa.BigInteger(), nullable=False, comment='Unique serial number for this business type'),
        sa.Column('base_invested_amount', sa.BigInteger(), nullable=False, comment='Base investment amount in lamports'),
        sa.Column('total_invested_amount', sa.BigInteger(), nullable=False, comment='Total invested including upgrades in lamports'),
        sa.Column('daily_rate', sa.Integer(), nullable=False, comment='Daily rate in basis points'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Whether NFT is active'),
        sa.Column('is_burned', sa.Boolean(), nullable=False, comment='Whether NFT has been burned'),
        sa.Column('minted_at', sa.DateTime(), nullable=False, comment='When NFT was minted'),
        sa.Column('burned_at', sa.DateTime(), nullable=True, comment='When NFT was burned'),
        sa.Column('last_transfer_at', sa.DateTime(), nullable=True, comment='Last transfer timestamp'),
        sa.Column('mint_signature', sa.String(length=88), nullable=False, comment='Transaction signature when NFT was minted'),
        sa.Column('burn_signature', sa.String(length=88), nullable=True, comment='Transaction signature when NFT was burned'),
        sa.Column('metadata_json', sa.JSON(), nullable=True, comment='Cached metadata JSON'),
        sa.Column('image_url', sa.Text(), nullable=True, comment='Direct image URL'),
        sa.Column('previous_owner', sa.String(length=44), nullable=True, comment='Previous owner wallet'),
        sa.Column('transfer_count', sa.Integer(), nullable=False, comment='Number of times NFT has been transferred'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True, comment='Last sync with on-chain data'),
        sa.Column('ownership_verified_at', sa.DateTime(), nullable=True, comment='Last ownership verification timestamp'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['player_wallet'], ['players.wallet'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('mint')
    )

    # Create businesses table
    op.create_table('businesses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('player_wallet', sa.String(length=44), nullable=False, comment='Owner\'s wallet address'),
        sa.Column('nft_mint', sa.String(length=44), nullable=True, comment='Associated NFT mint address'),
        sa.Column('business_type', postgresql.ENUM('TOBACCO_SHOP', 'FUNERAL_SERVICE', 'CAR_WORKSHOP', 'ITALIAN_RESTAURANT', 'GENTLEMEN_CLUB', 'CHARITY_FUND', name='businesstype'), nullable=False, comment='Type of business'),
        sa.Column('level', sa.Integer(), nullable=False, comment='Business upgrade level'),
        sa.Column('base_cost', sa.BigInteger(), nullable=False, comment='Base cost of business in lamports'),
        sa.Column('total_invested_amount', sa.BigInteger(), nullable=False, comment='Total invested including upgrades in lamports'),
        sa.Column('upgrade_costs', sa.Text(), nullable=True, comment='JSON array of upgrade costs'),
        sa.Column('daily_rate', sa.Integer(), nullable=False, comment='Daily rate in basis points (100 = 1%)'),
        sa.Column('last_claim_time', sa.DateTime(), nullable=True, comment='Last earnings claim timestamp'),
        sa.Column('total_earnings_generated', sa.BigInteger(), nullable=False, comment='Total earnings generated by this business'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Whether business is active and earning'),
        sa.Column('slot_index', sa.Integer(), nullable=True, comment='Index of slot this business occupies'),
        sa.Column('creation_signature', sa.String(length=88), nullable=True, comment='Transaction signature when business was created'),
        sa.Column('on_chain_created_at', sa.DateTime(), nullable=True, comment='Creation timestamp from blockchain'),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True, comment='Last sync with on-chain data'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['nft_mint'], ['business_nfts.mint'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['player_wallet'], ['players.wallet'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create business_slots table
    op.create_table('business_slots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('player_wallet', sa.String(length=44), nullable=False, comment='Owner\'s wallet address'),
        sa.Column('slot_index', sa.Integer(), nullable=False, comment='Slot index (0-based)'),
        sa.Column('slot_type', postgresql.ENUM('BASIC', 'PREMIUM', 'VIP', 'LEGENDARY', name='slottype'), nullable=False, comment='Type of slot'),
        sa.Column('is_unlocked', sa.Boolean(), nullable=False, comment='Whether slot is unlocked'),
        sa.Column('unlock_cost_paid', sa.BigInteger(), nullable=False, comment='Cost paid to unlock this slot'),
        sa.Column('business_id', sa.Integer(), nullable=True, comment='Business currently in this slot'),
        sa.Column('yield_bonus', sa.Integer(), nullable=False, comment='Yield bonus in basis points'),
        sa.Column('sell_fee_discount', sa.Integer(), nullable=False, comment='Sell fee discount percentage'),
        sa.Column('unlock_signature', sa.String(length=88), nullable=True, comment='Transaction signature when slot was unlocked'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['player_wallet'], ['players.wallet'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create events table
    op.create_table('events',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_type', postgresql.ENUM('PLAYER_CREATED', 'BUSINESS_CREATED', 'BUSINESS_UPGRADED', 'BUSINESS_SOLD', 'EARNINGS_UPDATED', 'EARNINGS_CLAIMED', 'BUSINESS_NFT_MINTED', 'BUSINESS_NFT_BURNED', 'BUSINESS_NFT_UPGRADED', 'BUSINESS_TRANSFERRED', 'BUSINESS_DEACTIVATED', 'SLOT_UNLOCKED', 'PREMIUM_SLOT_PURCHASED', 'BUSINESS_CREATED_IN_SLOT', 'BUSINESS_UPGRADED_IN_SLOT', 'BUSINESS_SOLD_FROM_SLOT', 'REFERRAL_BONUS_ADDED', name='eventtype'), nullable=False, comment='Type of event'),
        sa.Column('transaction_signature', sa.String(length=88), nullable=False, comment='Transaction signature'),
        sa.Column('instruction_index', sa.Integer(), nullable=False, comment='Instruction index within transaction'),
        sa.Column('event_index', sa.Integer(), nullable=False, comment='Event index within instruction'),
        sa.Column('slot', sa.BigInteger(), nullable=False, comment='Blockchain slot number'),
        sa.Column('block_time', sa.DateTime(), nullable=False, comment='Block timestamp'),
        sa.Column('raw_data', sa.JSON(), nullable=False, comment='Raw event data from blockchain'),
        sa.Column('parsed_data', sa.JSON(), nullable=True, comment='Parsed and structured event data'),
        sa.Column('player_wallet', sa.String(length=44), nullable=True, comment='Related player wallet'),
        sa.Column('business_mint', sa.String(length=44), nullable=True, comment='Related business NFT mint'),
        sa.Column('status', postgresql.ENUM('PENDING', 'PROCESSING', 'PROCESSED', 'FAILED', 'SKIPPED', name='eventstatus'), nullable=False, comment='Processing status'),
        sa.Column('processed_at', sa.DateTime(), nullable=True, comment='When event was processed'),
        sa.Column('error_message', sa.Text(), nullable=True, comment='Error message if processing failed'),
        sa.Column('retry_count', sa.Integer(), nullable=False, comment='Number of processing retries'),
        sa.Column('indexer_version', sa.String(length=20), nullable=False, comment='Version of indexer that processed this event'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create earnings_schedule table
    op.create_table('earnings_schedule',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('player_wallet', sa.String(length=44), nullable=False, comment='Player wallet address'),
        sa.Column('next_update_time', sa.DateTime(), nullable=False, comment='Next scheduled update time'),
        sa.Column('update_interval', sa.Integer(), nullable=False, comment='Update interval in seconds'),
        sa.Column('status', postgresql.ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'SKIPPED', name='earningsstatus'), nullable=False, comment='Current processing status'),
        sa.Column('last_update_attempt', sa.DateTime(), nullable=True, comment='Last update attempt timestamp'),
        sa.Column('last_successful_update', sa.DateTime(), nullable=True, comment='Last successful update timestamp'),
        sa.Column('consecutive_failures', sa.Integer(), nullable=False, comment='Number of consecutive failures'),
        sa.Column('last_error', sa.Text(), nullable=True, comment='Last error message'),
        sa.Column('is_active', sa.Boolean(), nullable=False, comment='Whether this schedule is active'),
        sa.Column('priority', sa.Integer(), nullable=False, comment='Processing priority (1=highest, 10=lowest)'),
        sa.Column('average_processing_time', sa.Integer(), nullable=True, comment='Average processing time in milliseconds'),
        sa.Column('total_updates', sa.Integer(), nullable=False, comment='Total number of successful updates'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['player_wallet'], ['players.wallet'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create earnings_history table
    op.create_table('earnings_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('player_wallet', sa.String(length=44), nullable=False, comment='Player wallet address'),
        sa.Column('event_type', sa.String(length=20), nullable=False, comment='Type of earnings event (update, claim)'),
        sa.Column('amount', sa.BigInteger(), nullable=False, comment='Amount in lamports'),
        sa.Column('previous_balance', sa.BigInteger(), nullable=False, comment='Previous pending earnings balance'),
        sa.Column('new_balance', sa.BigInteger(), nullable=False, comment='New pending earnings balance'),
        sa.Column('base_earnings', sa.BigInteger(), nullable=False, comment='Base business earnings'),
        sa.Column('slot_bonus_earnings', sa.BigInteger(), nullable=False, comment='Bonus earnings from premium slots'),
        sa.Column('referral_earnings', sa.BigInteger(), nullable=False, comment='Referral bonus earnings'),
        sa.Column('business_count', sa.Integer(), nullable=False, comment='Number of active businesses at time of update'),
        sa.Column('transaction_signature', sa.String(length=88), nullable=True, comment='Related blockchain transaction'),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True, comment='Processing time in milliseconds'),
        sa.Column('indexer_version', sa.String(length=20), nullable=False, comment='Version of system that processed this'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['player_wallet'], ['players.wallet'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index('idx_business_nft_player_active', 'business_nfts', ['player_wallet', 'is_active'])
    op.create_index('idx_business_nft_business_type', 'business_nfts', ['business_type', 'level'])
    op.create_index('idx_business_nft_serial', 'business_nfts', ['business_type', 'serial_number'])
    op.create_index('idx_business_nft_minted_at', 'business_nfts', ['minted_at'])
    op.create_index('idx_business_nft_burned', 'business_nfts', ['is_burned'])
    op.create_index('idx_business_nft_sync', 'business_nfts', ['last_sync_at'])
    
    op.create_index('idx_business_player_active', 'businesses', ['player_wallet', 'is_active'])
    op.create_index('idx_business_type_level', 'businesses', ['business_type', 'level'])
    op.create_index('idx_business_nft', 'businesses', ['nft_mint'])
    op.create_index('idx_business_slot', 'businesses', ['player_wallet', 'slot_index'])
    
    op.create_index('idx_slot_player_index', 'business_slots', ['player_wallet', 'slot_index'], unique=True)
    op.create_index('idx_slot_player_unlocked', 'business_slots', ['player_wallet', 'is_unlocked'])
    op.create_index('idx_slot_type', 'business_slots', ['slot_type'])
    
    op.create_index('idx_earnings_history_player_time', 'earnings_history', ['player_wallet', 'created_at'])
    op.create_index('idx_earnings_history_event_type', 'earnings_history', ['event_type', 'created_at'])
    op.create_index('idx_earnings_history_amount', 'earnings_history', ['amount'])
    op.create_index('idx_earnings_history_signature', 'earnings_history', ['transaction_signature'])
    
    op.create_index('idx_earnings_schedule_next_update', 'earnings_schedule', ['next_update_time', 'is_active'])
    op.create_index('idx_earnings_schedule_status', 'earnings_schedule', ['status', 'next_update_time'])
    op.create_index('idx_earnings_schedule_failures', 'earnings_schedule', ['consecutive_failures', 'is_active'])
    op.create_index('idx_earnings_schedule_priority', 'earnings_schedule', ['priority', 'next_update_time'])
    
    op.create_index('idx_event_type_slot', 'events', ['event_type', 'slot'])
    op.create_index('idx_event_player_type', 'events', ['player_wallet', 'event_type'])
    op.create_index('idx_event_signature_unique', 'events', ['transaction_signature', 'instruction_index', 'event_index'], unique=True)
    op.create_index('idx_event_status_created', 'events', ['status', 'created_at'])
    op.create_index('idx_event_block_time', 'events', ['block_time'])
    op.create_index('idx_event_business_mint', 'events', ['business_mint'])
    op.create_index('idx_event_pending_retry', 'events', ['status', 'retry_count'])
    
    op.create_index('idx_player_next_earnings', 'players', ['next_earnings_time'])
    op.create_index('idx_player_active_earnings', 'players', ['is_active', 'next_earnings_time'])
    op.create_index('idx_player_created_at', 'players', ['created_at'])
    op.create_index('idx_player_referrer', 'players', ['referrer_wallet'])
    op.create_index('idx_player_sync', 'players', ['last_sync_at'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_player_sync', table_name='players')
    op.drop_index('idx_player_referrer', table_name='players')
    op.drop_index('idx_player_created_at', table_name='players')
    op.drop_index('idx_player_active_earnings', table_name='players')
    op.drop_index('idx_player_next_earnings', table_name='players')
    
    op.drop_index('idx_event_pending_retry', table_name='events')
    op.drop_index('idx_event_business_mint', table_name='events')
    op.drop_index('idx_event_block_time', table_name='events')
    op.drop_index('idx_event_status_created', table_name='events')
    op.drop_index('idx_event_signature_unique', table_name='events')
    op.drop_index('idx_event_player_type', table_name='events')
    op.drop_index('idx_event_type_slot', table_name='events')
    
    op.drop_index('idx_earnings_schedule_priority', table_name='earnings_schedule')
    op.drop_index('idx_earnings_schedule_failures', table_name='earnings_schedule')
    op.drop_index('idx_earnings_schedule_status', table_name='earnings_schedule')
    op.drop_index('idx_earnings_schedule_next_update', table_name='earnings_schedule')
    
    op.drop_index('idx_earnings_history_signature', table_name='earnings_history')
    op.drop_index('idx_earnings_history_amount', table_name='earnings_history')
    op.drop_index('idx_earnings_history_event_type', table_name='earnings_history')
    op.drop_index('idx_earnings_history_player_time', table_name='earnings_history')
    
    op.drop_index('idx_slot_type', table_name='business_slots')
    op.drop_index('idx_slot_player_unlocked', table_name='business_slots')
    op.drop_index('idx_slot_player_index', table_name='business_slots')
    
    op.drop_index('idx_business_slot', table_name='businesses')
    op.drop_index('idx_business_nft', table_name='businesses')
    op.drop_index('idx_business_type_level', table_name='businesses')
    op.drop_index('idx_business_player_active', table_name='businesses')
    
    op.drop_index('idx_business_nft_sync', table_name='business_nfts')
    op.drop_index('idx_business_nft_burned', table_name='business_nfts')
    op.drop_index('idx_business_nft_minted_at', table_name='business_nfts')
    op.drop_index('idx_business_nft_serial', table_name='business_nfts')
    op.drop_index('idx_business_nft_business_type', table_name='business_nfts')
    op.drop_index('idx_business_nft_player_active', table_name='business_nfts')
    
    # Drop tables
    op.drop_table('earnings_history')
    op.drop_table('earnings_schedule')
    op.drop_table('events')
    op.drop_table('business_slots')
    op.drop_table('businesses')
    op.drop_table('business_nfts')
    op.drop_table('players')
    
    # Drop enum types
    op.execute("DROP TYPE IF EXISTS earningsstatus")
    op.execute("DROP TYPE IF EXISTS eventstatus")
    op.execute("DROP TYPE IF EXISTS eventtype")
    op.execute("DROP TYPE IF EXISTS slottype")
    op.execute("DROP TYPE IF EXISTS businesstype")
"""
Test database models and migrations.
"""

import pytest
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import init_database, close_database, get_async_session
from app.models.player import Player
from app.models.business import Business, BusinessType, BusinessSlot, SlotType
from app.models.nft import BusinessNFT
from app.models.event import Event, EventType, EventStatus
from app.models.earnings import EarningsSchedule, EarningsHistory, EarningsStatus


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_database():
    """Setup database for testing."""
    await init_database()
    yield
    await close_database()


@pytest.mark.asyncio
async def test_player_model():
    """Test Player model creation and operations."""
    async with get_async_session() as session:
        # Create test player
        player = Player(
            wallet="TestWallet123456789012345678901234567890",
            total_invested=0,
            total_upgrade_spent=0,
            total_slot_spent=0,
            total_earned=0,
            pending_earnings=0,
            pending_referral_earnings=0,
            unlocked_slots_count=3,
            premium_slots_count=0,
            has_paid_entry=False,
            is_active=True,
            earnings_interval=86400,
            referral_count=0,
            sync_version=1,
            daily_earnings_estimate=0
        )
        
        session.add(player)
        await session.commit()
        
        # Query player
        result = await session.get(Player, "TestWallet123456789012345678901234567890")
        assert result is not None
        assert result.wallet == "TestWallet123456789012345678901234567890"
        assert result.total_slots == 3
        assert result.net_profit == 0


@pytest.mark.asyncio
async def test_business_nft_model():
    """Test BusinessNFT model creation."""
    async with get_async_session() as session:
        # First create a player
        player = Player(
            wallet="TestPlayer123456789012345678901234567890",
            total_invested=0,
            total_upgrade_spent=0,
            total_slot_spent=0,
            total_earned=0,
            pending_earnings=0,
            pending_referral_earnings=0,
            unlocked_slots_count=3,
            premium_slots_count=0,
            has_paid_entry=False,
            is_active=True,
            earnings_interval=86400,
            referral_count=0,
            sync_version=1,
            daily_earnings_estimate=0
        )
        session.add(player)
        
        # Create NFT
        nft = BusinessNFT(
            mint="TestNFTMint123456789012345678901234567890",
            player_wallet="TestPlayer123456789012345678901234567890",
            name="Test Lemonade Stand #1",
            symbol="MAFIA",
            uri="https://test.com/metadata/1",
            business_type=BusinessType.TOBACCO_SHOP,
            level=1,
            serial_number=1,
            base_invested_amount=1000000,  # 0.001 SOL
            total_invested_amount=1000000,
            daily_rate=100,  # 1%
            is_active=True,
            is_burned=False,
            minted_at=datetime.utcnow(),
            mint_signature="TestSignature" + "0" * 60,
            transfer_count=0
        )
        
        session.add(nft)
        await session.commit()
        
        # Query NFT
        result = await session.get(BusinessNFT, "TestNFTMint123456789012345678901234567890")
        assert result is not None
        assert result.display_name == "Basic Lemonade Stand #1"
        assert result.estimated_value == 1000000


@pytest.mark.asyncio
async def test_event_model():
    """Test Event model creation."""
    async with get_async_session() as session:
        event = Event(
            event_type=EventType.PLAYER_CREATED,
            transaction_signature="TestTxSignature" + "0" * 60,
            instruction_index=0,
            event_index=0,
            slot=1000,
            block_time=datetime.utcnow(),
            raw_data={"test": "data"},
            player_wallet="TestWallet123456789012345678901234567890",
            status=EventStatus.PENDING,
            retry_count=0,
            indexer_version="1.0"
        )
        
        session.add(event)
        await session.commit()
        
        # Test event properties
        assert event.is_player_event
        assert not event.is_business_event
        assert not event.is_nft_event
        assert event.can_retry()


@pytest.mark.asyncio
async def test_earnings_schedule_model():
    """Test EarningsSchedule model."""
    async with get_async_session() as session:
        schedule = EarningsSchedule(
            player_wallet="TestWallet123456789012345678901234567890",
            next_update_time=datetime.utcnow(),
            update_interval=86400,
            status=EarningsStatus.PENDING,
            consecutive_failures=0,
            is_active=True,
            priority=5,
            total_updates=0
        )
        
        session.add(schedule)
        await session.commit()
        
        # Test schedule properties
        assert schedule.is_due
        assert not schedule.is_overdue


if __name__ == "__main__":
    pytest.main([__file__])
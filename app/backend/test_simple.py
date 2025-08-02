#!/usr/bin/env python3
"""
Simple test of database models
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from app.models.player import Player
from app.models.business import Business, BusinessType, BusinessSlot, SlotType
from app.models.nft import BusinessNFT
from app.models.event import Event, EventType, EventStatus
from app.models.earnings import EarningsSchedule, EarningsHistory, EarningsStatus

# Database URL
DATABASE_URL = "postgresql://solana_mafia:password@localhost:5432/solana_mafia_db"

def test_models():
    """Test database models with real data"""
    print("🧪 Testing database models...")
    
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    
    with Session() as session:
        # Clean up any existing test data
        session.query(Player).filter(Player.wallet.like("TestWallet%")).delete()
        session.query(BusinessNFT).filter(BusinessNFT.mint.like("TestNFT%")).delete()
        session.query(Business).filter(Business.player_wallet.like("TestWallet%")).delete()
        session.query(Event).filter(Event.player_wallet.like("TestWallet%")).delete()
        session.query(EarningsSchedule).filter(EarningsSchedule.player_wallet.like("TestWallet%")).delete()
        session.commit()
        
        print("\n1. Testing Player model...")
        
        # Create test player
        player = Player(
            wallet="TestWallet123456789012345678901234567890",
            total_invested=1000000,  # 0.001 SOL
            total_upgrade_spent=0,
            total_slot_spent=0,
            total_earned=0,
            pending_earnings=50000,  # 0.00005 SOL
            pending_referral_earnings=0,
            unlocked_slots_count=3,
            premium_slots_count=0,
            has_paid_entry=True,
            is_active=True,
            earnings_interval=86400,
            referral_count=0,
            sync_version=1,
            daily_earnings_estimate=50000
        )
        
        session.add(player)
        session.commit()
        
        # Test player properties
        print(f"   ✅ Player created: {player.wallet[:10]}...")
        print(f"   ✅ Total slots: {player.total_slots}")
        print(f"   ✅ Net profit: {player.net_profit}")
        print(f"   ✅ Claimable amount: {player.get_claimable_amount()}")
        
        print("\n2. Testing BusinessNFT model...")
        
        # Create NFT
        nft = BusinessNFT(
            mint="TestNFTMint123456789012345678901234567890",
            player_wallet="TestWallet123456789012345678901234567890",
            name="Test Lemonade Stand #1",
            symbol="MAFIA",
            uri="https://test.com/metadata/1",
            business_type=BusinessType.LEMONADE_STAND,
            level=1,
            serial_number=1,
            base_invested_amount=1000000,
            total_invested_amount=1000000,
            daily_rate=100,  # 1%
            is_active=True,
            is_burned=False,
            minted_at=datetime.now(timezone.utc),
            mint_signature="TestSignature" + "0" * 60,
            transfer_count=0
        )
        
        session.add(nft)
        session.commit()
        
        print(f"   ✅ NFT created: {nft.mint[:10]}...")
        print(f"   ✅ Display name: {nft.display_name}")
        print(f"   ✅ Estimated value: {nft.estimated_value}")
        print(f"   ✅ Business type: {nft.business_type.value}")
        
        print("\n3. Testing Business model...")
        
        # Create business
        business = Business(
            player_wallet="TestWallet123456789012345678901234567890",
            nft_mint="TestNFTMint123456789012345678901234567890",
            business_type=BusinessType.LEMONADE_STAND,
            level=1,
            base_cost=1000000,
            total_invested_amount=1000000,
            daily_rate=100,
            total_earnings_generated=0,
            is_active=True,
            slot_index=0
        )
        
        session.add(business)
        session.commit()
        
        print(f"   ✅ Business created: ID {business.id}")
        print(f"   ✅ Total invested: {business.total_invested_amount}")
        print(f"   ✅ Daily rate: {business.daily_rate} basis points")
        
        print("\n4. Testing Event model...")
        
        # Create event
        event = Event(
            event_type=EventType.BUSINESS_CREATED,
            transaction_signature="TestTxSignature" + "0" * 60,
            instruction_index=0,
            event_index=0,
            slot=1000,
            block_time=datetime.now(timezone.utc),
            raw_data={"business_type": "LEMONADE_STAND", "amount": 1000000},
            player_wallet="TestWallet123456789012345678901234567890",
            business_mint="TestNFTMint123456789012345678901234567890",
            status=EventStatus.PENDING,
            retry_count=0,
            indexer_version="1.0"
        )
        
        session.add(event)
        session.commit()
        
        print(f"   ✅ Event created: ID {event.id}")
        print(f"   ✅ Is business event: {event.is_business_event}")
        print(f"   ✅ Can retry: {event.can_retry()}")
        
        print("\n5. Testing EarningsSchedule model...")
        
        # Create earnings schedule
        schedule = EarningsSchedule(
            player_wallet="TestWallet123456789012345678901234567890",
            next_update_time=datetime.now(timezone.utc),
            update_interval=86400,
            status=EarningsStatus.PENDING,
            consecutive_failures=0,
            is_active=True,
            priority=5,
            total_updates=0
        )
        
        session.add(schedule)
        session.commit()
        
        print(f"   ✅ Schedule created: ID {schedule.id}")
        print(f"   ✅ Is due: {schedule.is_due}")
        print(f"   ✅ Priority level: {schedule.priority}")
        
        print("\n6. Testing data queries...")
        
        # Query player with relationships
        player_with_data = session.query(Player).filter_by(
            wallet="TestWallet123456789012345678901234567890"
        ).first()
        
        print(f"   ✅ Player found: {player_with_data.wallet[:10]}...")
        print(f"   ✅ Player businesses count: {len(player_with_data.businesses)}")
        print(f"   ✅ Player NFTs count: {len(player_with_data.nfts)}")
        print(f"   ✅ Player earnings history count: {len(player_with_data.earnings_history)}")
        
        print("\n✅ All model tests passed!")

if __name__ == "__main__":
    test_models()
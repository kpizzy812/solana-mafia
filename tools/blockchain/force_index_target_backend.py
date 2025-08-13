#!/usr/bin/env python3
"""
Force index the specific transaction containing business creation.
"""

import asyncio
import sys
import os

# Add backend path to sys.path
sys.path.append('/Users/a1/Projects/solana-mafia/app/backend')

from app.indexer.transaction_indexer import TransactionIndexer
from app.core.config import settings
from app.core.database import init_database

async def force_index_target():
    """Force index the target transaction."""
    
    # Target transaction details
    target_signature = "4YGibu6LVo7cuXyfZTUQbxdP28oH7afQSn8yDksyTMSrfb4EAJS188mD6jqtns28wfBEqXuaKVex4T6TYz5ndG29"
    target_slot = 399191186
    
    print(f"🎯 Forcing indexing of target transaction:")
    print(f"   Signature: {target_signature}")
    print(f"   Slot: {target_slot}")
    print(f"   Program ID: {settings.solana_program_id}")
    
    # Create indexer
    indexer = TransactionIndexer()
    
    try:
        # Initialize database first
        await init_database()
        await indexer.initialize()
        
        # Force index the specific slot range
        start_slot = target_slot - 10
        end_slot = target_slot + 10
        
        print(f"🔍 Indexing slot range: {start_slot} to {end_slot}")
        
        stats = await indexer.index_transactions_batch(
            start_slot=start_slot,
            end_slot=end_slot,
            limit=1000
        )
        
        print(f"📊 Indexing stats:")
        print(f"   Transactions processed: {stats.transactions_processed}")
        print(f"   Events found: {stats.events_found}")
        print(f"   Events stored: {stats.events_stored}")
        print(f"   Errors: {stats.errors_encountered}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        
    finally:
        await indexer.shutdown()

if __name__ == "__main__":
    asyncio.run(force_index_target())
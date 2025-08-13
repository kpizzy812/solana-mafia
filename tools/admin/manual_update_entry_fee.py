#!/usr/bin/env python3
"""
Manually update entry fee in the smart contract.

This script allows manual testing of entry fee updates to the Solana smart contract.
Use this to test if the dynamic pricing service transaction sending works correctly.
"""

import asyncio
import sys
from pathlib import Path

# Add the parent directory to sys.path so we can import app modules
sys.path.append(str(Path(__file__).parent))

from app.services.dynamic_pricing_service import dynamic_pricing_service
from app.services.coingecko_service import coingecko_service

async def manual_update_entry_fee():
    """Manually update entry fee based on current conditions."""
    
    print("🔧 Manual Entry Fee Update")
    print("=" * 30)
    print()
    
    # Check if service is ready
    if not dynamic_pricing_service.admin_keypair:
        print("❌ Admin keypair not available")
        print("   Make sure ADMIN_PRIVATE_KEY environment variable is set")
        return False
    
    print(f"✅ Admin keypair: {dynamic_pricing_service.admin_keypair.pubkey()}")
    print()
    
    # Get current data
    print("📊 Gathering current data...")
    
    try:
        total_players = await dynamic_pricing_service.get_total_players()
        print(f"  - Total players (has_paid_entry=True): {total_players}")
        
        sol_price = await coingecko_service.get_sol_price_usd()
        if not sol_price:
            print("❌ Could not fetch SOL price")
            return False
        
        print(f"  - SOL price: ${sol_price:.2f}")
        
        # Calculate new fee
        new_fee_lamports = dynamic_pricing_service.calculate_entry_fee_lamports(total_players, sol_price)
        fee_usd = dynamic_pricing_service.calculate_entry_fee_usd(total_players)
        fee_sol = new_fee_lamports / 1_000_000_000
        
        print(f"  - Calculated fee: {new_fee_lamports} lamports")
        print(f"  - That's {fee_sol:.6f} SOL (≈${fee_usd:.2f})")
        print()
        
        # Ask for confirmation
        response = input("🤔 Do you want to send this update to the smart contract? [y/N]: ")
        if response.lower() != 'y':
            print("❌ Update cancelled by user")
            return False
        
        print()
        print("📡 Sending transaction to smart contract...")
        
        # Send the update
        success = await dynamic_pricing_service._send_update_transaction(new_fee_lamports)
        
        if success:
            print("✅ Entry fee updated successfully!")
            print(f"   New fee: {new_fee_lamports} lamports ({fee_sol:.6f} SOL ≈ ${fee_usd:.2f})")
            print(f"   Based on {total_players} players at ${sol_price:.2f}/SOL")
            
            # Update service cache
            dynamic_pricing_service.last_entry_fee = new_fee_lamports
            
            return True
        else:
            print("❌ Failed to update entry fee")
            print("   Check the logs for error details")
            return False
            
    except Exception as e:
        print(f"❌ Error during update: {e}")
        import traceback
        traceback.print_exc()
        return False

async def check_current_contract_fee():
    """Check what entry fee is currently set in the contract."""
    print("🔍 Checking current contract state...")
    print("   (This would require reading from the GameConfig account)")
    print("   For now, you can check this through the frontend or RPC calls")
    print()

async def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        await check_current_contract_fee()
        return
    
    print("⚠️  WARNING: This script will send a real transaction to the blockchain!")
    print("   Make sure you're on the correct network (devnet/mainnet)")
    print("   The transaction will cost a small amount of SOL for gas fees")
    print()
    
    success = await manual_update_entry_fee()
    
    if success:
        print()
        print("🎉 Update completed successfully!")
        print()
        print("💡 Next steps:")
        print("   - Check the frontend FOMO display for updated price")
        print("   - Verify the entry fee is correct for new players")
        print("   - Monitor the dynamic pricing service logs")
    else:
        print()
        print("💡 Troubleshooting tips:")
        print("   - Check ADMIN_PRIVATE_KEY environment variable")
        print("   - Verify the admin wallet has SOL for transaction fees")
        print("   - Make sure you're connected to the correct Solana network")
        print("   - Check that the program ID is correct in settings")

if __name__ == "__main__":
    asyncio.run(main())
/**
 * Test script for dynamic pricing functionality
 * Tests CoinGecko integration and entry fee updates
 */

const fetch = require('node-fetch');

const API_BASE = process.env.API_URL || 'http://localhost:8000/api/v1';

async function testCoinGeckoPrice() {
    console.log('📈 Testing CoinGecko SOL price...');
    
    try {
        // Test direct CoinGecko API
        const response = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd');
        const data = await response.json();
        const solPrice = data.solana?.usd;
        
        console.log(`✅ SOL Price: $${solPrice}`);
        return solPrice;
    } catch (error) {
        console.error('❌ CoinGecko API error:', error.message);
        return null;
    }
}

async function getGlobalStats() {
    console.log('\n📊 Getting global stats...');
    
    try {
        const response = await fetch(`${API_BASE}/stats/global`);
        const data = await response.json();
        
        if (data.success) {
            const stats = data.data;
            console.log(`✅ Total players: ${stats.total_players}`);
            console.log(`✅ Current entry fee: ${stats.current_entry_fee} lamports (${(stats.current_entry_fee / 1e9).toFixed(6)} SOL)`);
            console.log(`✅ Entry fee USD: $${stats.current_entry_fee_usd?.toFixed(2) || 'N/A'}`);
            console.log(`✅ SOL price: $${stats.sol_price_usd?.toFixed(2) || 'N/A'}`);
            console.log(`✅ Dynamic pricing enabled: ${stats.pricing_enabled}`);
            return stats;
        } else {
            console.error('❌ Failed to get stats:', data);
            return null;
        }
    } catch (error) {
        console.error('❌ API error:', error.message);
        return null;
    }
}

async function testManualPriceUpdate(feeLamports) {
    console.log(`\n💰 Testing manual price update to ${feeLamports} lamports...`);
    
    try {
        const response = await fetch(`${API_BASE}/admin/pricing/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer admin' // This will need proper admin auth
            },
            body: JSON.stringify({
                fee_lamports: feeLamports
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log(`✅ Entry fee updated to ${data.data.new_fee_sol} SOL`);
            return true;
        } else {
            console.error('❌ Update failed:', data);
            return false;
        }
    } catch (error) {
        console.error('❌ Update error:', error.message);
        return false;
    }
}

async function calculateDynamicPrices() {
    console.log('\n🧮 Testing dynamic price calculation...');
    
    const solPrice = 162; // Example SOL price
    
    console.log(`At SOL price $${solPrice}:`);
    
    // Test different player counts
    const testCounts = [0, 25, 50, 100, 200, 300, 500, 1000];
    
    for (const playerCount of testCounts) {
        let feeUsd;
        if (playerCount <= 100) {
            feeUsd = 2.0 + (8.0 * playerCount / 100);
        } else if (playerCount <= 500) {
            feeUsd = 10.0 + (10.0 * (playerCount - 100) / 400);
        } else {
            feeUsd = 20.0;
        }
        
        const feeSol = feeUsd / solPrice;
        const feeLamports = Math.floor(feeSol * 1e9);
        
        console.log(`  ${playerCount} players: $${feeUsd.toFixed(2)} = ${feeSol.toFixed(6)} SOL = ${feeLamports} lamports`);
    }
}

async function main() {
    console.log('🚀 Solana Mafia Dynamic Pricing Test\n');
    
    // Test CoinGecko price fetching
    await testCoinGeckoPrice();
    
    // Test dynamic price calculations
    await calculateDynamicPrices();
    
    // Get current global stats
    await getGlobalStats();
    
    // Test manual price update (will fail without proper admin auth)
    // await testManualPriceUpdate(15_000_000); // Set to 0.015 SOL
    
    console.log('\n✨ Test completed!');
    console.log('\n📝 To use manual pricing:');
    console.log('1. Add your admin private key to .env: ADMIN_PRIVATE_KEY=your_base58_key');
    console.log('2. Set DYNAMIC_PRICING_ENABLED=true');
    console.log('3. Use POST /api/v1/admin/pricing/update with proper admin auth');
}

if (require.main === module) {
    main().catch(console.error);
}

module.exports = {
    testCoinGeckoPrice,
    getGlobalStats,
    testManualPriceUpdate,
    calculateDynamicPrices
};
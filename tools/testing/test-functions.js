// scripts/test-functions.js
// Индивидуальные функции для тестирования

const anchor = require("@coral-xyz/anchor");
const { PublicKey, Connection, LAMPORTS_PER_SOL } = require("@solana/web3.js");

// Константы
const PROGRAM_ID = new PublicKey("3Ly6bEWRfKyVGwrRN27gHhBogo1K4HbZyk69KHW9AUx7");
const DEVNET_URL = "https://api.devnet.solana.com";

// PDAs (уже известные)
const GAME_STATE_PDA = new PublicKey("AXfj87zMh8zeRaiWwQMH8vjyS5PVcP9Ddm3rTUPGdV3E");
const GAME_CONFIG_PDA = new PublicKey("FK4oeyryrEGAmGf7n38sZ7T9Z2B2wVYNC3WiyyUa1sxJ");
const TREASURY_PDA = new PublicKey("Gh58fNwcBb1HxVFUshVyqzyCeYCkiugzHEMJVDtGUUEU");
const TREASURY_WALLET = new PublicKey("HLWTn3BYB3jvgquBG323XLyqzEj11H4N5m6EMpPGCCG6");

// Setup
function setupProvider() {
    const connection = new Connection(DEVNET_URL, "confirmed");
    const wallet = anchor.Wallet.local();
    const provider = new anchor.AnchorProvider(connection, wallet, {});
    anchor.setProvider(provider);
    
    // Load program
    const idl = require("../target/idl/solana_mafia.json");
    const program = new anchor.Program(idl, PROGRAM_ID, provider);
    
    return { provider, program, connection };
}

// 📊 1. GET GLOBAL STATS
async function testGlobalStats() {
    console.log("📊 TESTING: Get Global Stats");
    console.log("============================");
    
    try {
        const { program } = setupProvider();
        
        await program.methods
            .getGlobalStats()
            .accounts({
                gameState: GAME_STATE_PDA,
            })
            .rpc();
            
        console.log("✅ Global stats retrieved successfully!");
        
        // Также прочитаем аккаунт напрямую
        const gameState = await program.account.gameState.fetch(GAME_STATE_PDA);
        console.log("📈 Game Statistics:");
        console.log(`   Players: ${gameState.totalPlayers}`);
        console.log(`   Businesses: ${gameState.totalBusinesses}`);
        console.log(`   Total Invested: ${gameState.totalInvested} lamports`);
        console.log(`   Total Withdrawn: ${gameState.totalWithdrawn} lamports`);
        
    } catch (error) {
        console.log(`❌ Error: ${error.message}`);
    }
}

// 👤 2. CREATE PLAYER
async function testCreatePlayer() {
    console.log("👤 TESTING: Create Player");
    console.log("=========================");
    
    try {
        const { program, provider } = setupProvider();
        const myWallet = provider.wallet.publicKey;
        
        // Find player PDA
        const [playerPda] = await PublicKey.findProgramAddress(
            [Buffer.from("player"), myWallet.toBuffer()],
            PROGRAM_ID
        );
        
        console.log(`🎯 My wallet: ${myWallet}`);
        console.log(`🎯 Player PDA: ${playerPda}`);
        
        // Check balance first
        const balance = await provider.connection.getBalance(myWallet);
        console.log(`💰 My balance: ${balance / LAMPORTS_PER_SOL} SOL`);
        
        if (balance < 0.01 * LAMPORTS_PER_SOL) {
            console.log("⚠️ Insufficient balance for entry fee!");
            console.log("💡 Run: solana airdrop 1");
            return;
        }
        
        const tx = await program.methods
            .createPlayer(null) // no referrer
            .accounts({
                owner: myWallet,
                player: playerPda,
                gameConfig: GAME_CONFIG_PDA,
                gameState: GAME_STATE_PDA,
                treasuryWallet: TREASURY_WALLET,
                systemProgram: anchor.web3.SystemProgram.programId,
            })
            .rpc();
            
        console.log(`✅ Player created! TX: ${tx}`);
        
        // Verify
        const playerAccount = await program.account.player.fetch(playerPda);
        console.log("👤 Player info:");
        console.log(`   Owner: ${playerAccount.owner}`);
        console.log(`   Entry paid: ${playerAccount.hasPaidEntry}`);
        console.log(`   Total invested: ${playerAccount.totalInvested}`);
        
    } catch (error) {
        if (error.message.includes("already in use")) {
            console.log("ℹ️ Player already exists!");
        } else {
            console.log(`❌ Error: ${error.message}`);
        }
    }
}

// 💰 3. UPDATE EARNINGS
async function testUpdateEarnings() {
    console.log("💰 TESTING: Update Earnings");
    console.log("===========================");
    
    try {
        const { program, provider } = setupProvider();
        const myWallet = provider.wallet.publicKey;
        
        const [playerPda] = await PublicKey.findProgramAddress(
            [Buffer.from("player"), myWallet.toBuffer()],
            PROGRAM_ID
        );
        
        const tx = await program.methods
            .updateEarnings()
            .accounts({
                playerOwner: myWallet,
                player: playerPda,
            })
            .rpc();
            
        console.log(`✅ Earnings updated! TX: ${tx}`);
        
        // Check new balance
        const playerAccount = await program.account.player.fetch(playerPda);
        console.log(`💰 Pending earnings: ${playerAccount.pendingEarnings} lamports`);
        
    } catch (error) {
        console.log(`❌ Error: ${error.message}`);
    }
}

// 📊 4. GET PLAYER DATA
async function testGetPlayerData() {
    console.log("📊 TESTING: Get Player Data");
    console.log("===========================");
    
    try {
        const { program, provider } = setupProvider();
        const myWallet = provider.wallet.publicKey;
        
        const [playerPda] = await PublicKey.findProgramAddress(
            [Buffer.from("player"), myWallet.toBuffer()],
            PROGRAM_ID
        );
        
        await program.methods
            .getPlayerData()
            .accounts({
                player: playerPda,
            })
            .rpc();
            
        console.log("✅ Player data retrieved!");
        
        // Also fetch directly
        const playerAccount = await program.account.player.fetch(playerPda);
        console.log("👤 Player Details:");
        console.log(`   Wallet: ${playerAccount.owner}`);
        console.log(`   Businesses: ${playerAccount.businesses.length}`);
        console.log(`   Total Invested: ${playerAccount.totalInvested} lamports`);
        console.log(`   Pending Earnings: ${playerAccount.pendingEarnings} lamports`);
        console.log(`   Entry Paid: ${playerAccount.hasPaidEntry}`);
        
    } catch (error) {
        console.log(`❌ Error: ${error.message}`);
    }
}

// 💸 5. CLAIM EARNINGS
async function testClaimEarnings() {
    console.log("💸 TESTING: Claim Earnings");
    console.log("==========================");
    
    try {
        const { program, provider } = setupProvider();
        const myWallet = provider.wallet.publicKey;
        
        const [playerPda] = await PublicKey.findProgramAddress(
            [Buffer.from("player"), myWallet.toBuffer()],
            PROGRAM_ID
        );
        
        // Check pending earnings first
        const playerAccount = await program.account.player.fetch(playerPda);
        console.log(`💰 Current pending: ${playerAccount.pendingEarnings} lamports`);
        
        if (playerAccount.pendingEarnings == 0) {
            console.log("ℹ️ No earnings to claim!");
            return;
        }
        
        const balanceBefore = await provider.connection.getBalance(myWallet);
        
        const tx = await program.methods
            .claimEarnings()
            .accounts({
                playerOwner: myWallet,
                player: playerPda,
                treasuryPda: TREASURY_PDA,
                gameState: GAME_STATE_PDA,
            })
            .rpc();
            
        const balanceAfter = await provider.connection.getBalance(myWallet);
        const earned = balanceAfter - balanceBefore;
        
        console.log(`✅ Earnings claimed! TX: ${tx}`);
        console.log(`💰 Received: ${earned} lamports`);
        
    } catch (error) {
        console.log(`❌ Error: ${error.message}`);
    }
}

// 🏦 6. CHECK BALANCES
async function checkAllBalances() {
    console.log("🏦 CHECKING ALL BALANCES");
    console.log("========================");
    
    try {
        const { provider } = setupProvider();
        const myWallet = provider.wallet.publicKey;
        
        const myBalance = await provider.connection.getBalance(myWallet);
        const treasuryPdaBalance = await provider.connection.getBalance(TREASURY_PDA);
        const treasuryWalletBalance = await provider.connection.getBalance(TREASURY_WALLET);
        
        console.log("💰 BALANCES:");
        console.log(`   My Wallet: ${myBalance / LAMPORTS_PER_SOL} SOL`);
        console.log(`   Treasury PDA: ${treasuryPdaBalance / LAMPORTS_PER_SOL} SOL`);
        console.log(`   Treasury Wallet: ${treasuryWalletBalance / LAMPORTS_PER_SOL} SOL`);
        console.log(`   Total System: ${(treasuryPdaBalance + treasuryWalletBalance) / LAMPORTS_PER_SOL} SOL`);
        
    } catch (error) {
        console.log(`❌ Error: ${error.message}`);
    }
}

// Main function
async function main() {
    const args = process.argv.slice(2);
    const command = args[0];
    
    console.log(`🎮 Solana Mafia Manual Testing`);
    console.log(`🌐 Network: devnet`);
    console.log(`📍 Program: ${PROGRAM_ID}`);
    console.log(`👤 Wallet: ${anchor.Wallet.local().publicKey}`);
    console.log("");
    
    switch (command) {
        case 'stats':
            await testGlobalStats();
            break;
        case 'create':
            await testCreatePlayer();
            break;
        case 'update':
            await testUpdateEarnings();
            break;
        case 'player':
            await testGetPlayerData();
            break;
        case 'claim':
            await testClaimEarnings();
            break;
        case 'balances':
            await checkAllBalances();
            break;
        case 'all':
            await testGlobalStats();
            await checkAllBalances();
            await testCreatePlayer();
            await testGetPlayerData();
            await testUpdateEarnings();
            break;
        default:
            console.log("📋 AVAILABLE COMMANDS:");
            console.log("   node scripts/test-functions.js stats     - Get global stats");
            console.log("   node scripts/test-functions.js create    - Create player");
            console.log("   node scripts/test-functions.js update    - Update earnings");
            console.log("   node scripts/test-functions.js player    - Get player data");
            console.log("   node scripts/test-functions.js claim     - Claim earnings");
            console.log("   node scripts/test-functions.js balances  - Check all balances");
            console.log("   node scripts/test-functions.js all       - Run basic tests");
            break;
    }
}

if (require.main === module) {
    main().catch(console.error);
}

module.exports = {
    testGlobalStats,
    testCreatePlayer,
    testUpdateEarnings,
    testGetPlayerData,
    testClaimEarnings,
    checkAllBalances
};
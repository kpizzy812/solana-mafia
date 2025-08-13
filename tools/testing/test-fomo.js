const { PublicKey, Connection, Keypair } = require("@solana/web3.js");
const { AnchorProvider, Wallet, Program } = require("@coral-xyz/anchor");

// Simulate the frontend getFomoData function
async function testFomoData() {
  console.log("🧪 Testing FOMO data fetching...");

  try {
    // Setup (similar to frontend)
    const connection = new Connection("https://api.devnet.solana.com", "confirmed");
    
    // Create a dummy wallet for testing
    const walletKeypair = Keypair.generate();
    const wallet = new Wallet(walletKeypair);
    
    const provider = new AnchorProvider(connection, wallet, { preflightCommitment: 'confirmed' });
    const programId = new PublicKey("HifXYhFJapXPeBgKKZu8gmdc7cZvfERJ9aEkchHxyBLS"); 
    
    // Load IDL manually without Program constructor (to avoid the size issue)
    const idl = require("../target/idl/solana_mafia.json");
    
    // Get PDAs
    const [gameState] = PublicKey.findProgramAddressSync(
      [Buffer.from("game_state")],
      programId
    );
    const [gameConfig] = PublicKey.findProgramAddressSync(
      [Buffer.from("game_config")],
      programId
    );

    console.log(`Testing with Program ID: ${programId.toString()}`);
    console.log(`Game State: ${gameState.toString()}`);
    console.log(`Game Config: ${gameConfig.toString()}`);

    // Try to instantiate Program (this might fail due to the IDL issue)
    let program;
    try {
      program = new Program(idl, programId, provider);
      console.log("✅ Program instance created successfully");
    } catch (error) {
      console.error("❌ Failed to create Program instance:", error.message);
      console.log("💡 This is the IDL size issue we identified");
      return;
    }

    // Test fetching accounts
    try {
      console.log("Fetching game state...");
      const gameStateAccount = await program.account.gameState.fetch(gameState);
      console.log("✅ Game state fetched successfully");
      console.log(`- Total Players: ${gameStateAccount.totalPlayers.toString()}`);
      console.log(`- Is Paused: ${gameStateAccount.isPaused}`);
    } catch (error) {
      console.error("❌ Failed to fetch game state:", error.message);
      return;
    }

    try {
      console.log("Fetching game config...");
      const gameConfigAccount = await program.account.gameConfig.fetch(gameConfig);
      console.log("✅ Game config fetched successfully");
      console.log(`- Base Entry Fee: ${gameConfigAccount.baseEntryFee.toString()} lamports`);
      console.log(`- Max Entry Fee: ${gameConfigAccount.maxEntryFee.toString()} lamports`);
      console.log(`- Players Per Milestone: ${gameConfigAccount.playersPerMilestone.toString()}`);
      console.log(`- Registrations Open: ${gameConfigAccount.registrationsOpen}`);
      
      // Test FOMO calculations
      const totalPlayers = gameStateAccount.totalPlayers.toNumber();
      const baseEntryFee = gameConfigAccount.baseEntryFee.toNumber() / 1e9; // Convert to SOL
      const maxEntryFee = gameConfigAccount.maxEntryFee.toNumber() / 1e9;
      const feeIncrement = gameConfigAccount.feeIncrement.toNumber() / 1e9;
      const playersPerMilestone = gameConfigAccount.playersPerMilestone.toNumber();
      
      const milestones = Math.floor(totalPlayers / playersPerMilestone);
      const currentEntryFee = Math.min(baseEntryFee + (milestones * feeIncrement), maxEntryFee);
      const nextEntryFee = Math.min(baseEntryFee + ((milestones + 1) * feeIncrement), maxEntryFee);
      const nextMilestone = (milestones + 1) * playersPerMilestone;
      const playersUntilIncrease = nextMilestone - totalPlayers;
      
      console.log("\n📊 FOMO Data Calculations:");
      console.log(`- Current Entry Fee: ${currentEntryFee} SOL`);
      console.log(`- Next Entry Fee: ${nextEntryFee} SOL`);
      console.log(`- Players Until Increase: ${playersUntilIncrease}`);
      
    } catch (error) {
      console.error("❌ Failed to fetch game config:", error.message);
      if (error.message.includes('Invalid bool')) {
        console.log("💥 This is the boolean decoding error we were debugging!");
        console.log("🔧 The account data might be corrupted or have a version mismatch.");
      }
      return;
    }

    console.log("\n🎉 FOMO data fetching test completed successfully!");

  } catch (error) {
    console.error("❌ Test failed:", error);
  }
}

testFomoData().catch(console.error);
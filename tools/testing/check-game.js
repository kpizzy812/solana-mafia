const anchor = require("@coral-xyz/anchor");
const { PublicKey, Connection } = require("@solana/web3.js");

async function checkGame() {
  console.log("🔍 Checking Solana Mafia Game state...");

  try {
    // Setup connection
    const connection = new Connection("https://api.devnet.solana.com", "confirmed");
    
    // Find PDAs  
    const programId = new PublicKey("3Ly6bEWRfKyVGwrRN27gHhBogo1K4HbZyk69KHW9AUx7");
    
    const [gameStatePda] = await PublicKey.findProgramAddress(
      [Buffer.from("game_state")],
      programId
    );
    
    const [gameConfigPda] = await PublicKey.findProgramAddress(
      [Buffer.from("game_config")],
      programId
    );
    
    const [treasuryPda] = await PublicKey.findProgramAddress(
      [Buffer.from("treasury")],
      programId
    );

    console.log(`Program ID: ${programId}`);
    console.log(`Game State PDA: ${gameStatePda}`);
    console.log(`Game Config PDA: ${gameConfigPda}`);
    console.log(`Treasury PDA: ${treasuryPda}`);

    // Check if accounts exist
    try {
      const gameStateInfo = await connection.getAccountInfo(gameStatePda);
      if (gameStateInfo) {
        console.log("✅ GameState account exists");
        console.log(`Size: ${gameStateInfo.data.length} bytes`);
        console.log(`Owner: ${gameStateInfo.owner}`);
      } else {
        console.log("❌ GameState account does not exist");
      }
    } catch (error) {
      console.log("❌ Error checking GameState:", error.message);
    }

    try {
      const gameConfigInfo = await connection.getAccountInfo(gameConfigPda);
      if (gameConfigInfo) {
        console.log("✅ GameConfig account exists");
        console.log(`Size: ${gameConfigInfo.data.length} bytes`);
        console.log(`Owner: ${gameConfigInfo.owner}`);
      } else {
        console.log("❌ GameConfig account does not exist");
      }
    } catch (error) {
      console.log("❌ Error checking GameConfig:", error.message);
    }

    // Check if we need to initialize
    const gameStateInfo = await connection.getAccountInfo(gameStatePda);
    const gameConfigInfo = await connection.getAccountInfo(gameConfigPda);
    
    if (!gameStateInfo || !gameConfigInfo) {
      console.log("\n🚀 Game needs to be initialized!");
      console.log("Run this command to initialize:");
      console.log(`ANCHOR_WALLET=/Users/a1/.config/solana/id.json anchor run init-devnet`);
    } else {
      console.log("\n✅ Game is already initialized!");
    }

  } catch (error) {
    console.error("❌ Error:", error);
  }
}

if (require.main === module) {
  checkGame().catch(console.error);
}

module.exports = { checkGame };
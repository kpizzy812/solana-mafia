const { Connection, PublicKey, Keypair } = require("@solana/web3.js");
const { AnchorProvider, Wallet, Program } = require("@coral-xyz/anchor");
const fs = require("fs");
const os = require("os");

async function initializeGame() {
  console.log("🎮 Initializing Solana Mafia Game...");
  
  // Setup
  const connection = new Connection("https://api.devnet.solana.com", "confirmed");
  const keypairPath = os.homedir() + "/.config/solana/id.json";
  const keypairData = JSON.parse(fs.readFileSync(keypairPath, "utf8"));
  const wallet = new Wallet(Keypair.fromSecretKey(new Uint8Array(keypairData)));
  
  const provider = new AnchorProvider(connection, wallet, {});
  
  // Load IDL
  const idl = require("../app/frontend/src/solana_mafia.json");
  // Anchor 0.30+ - Program ID now comes from idl.address
  const program = new Program(idl, provider);
  
  console.log(`Program ID: ${program.programId}`);
  console.log(`Authority: ${wallet.publicKey}`);

  // Find PDAs
  const [gameStatePda] = PublicKey.findProgramAddressSync(
    [Buffer.from("game_state")],
    program.programId
  );
  
  const [gameConfigPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("game_config")],
    program.programId
  );
  
  const [treasuryPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("treasury")],
    program.programId
  );

  console.log(`GameState PDA: ${gameStatePda}`);
  console.log(`GameConfig PDA: ${gameConfigPda}`);
  console.log(`Treasury PDA: ${treasuryPda}`);

  // Check if already initialized
  try {
    const gameStateInfo = await connection.getAccountInfo(gameStatePda);
    if (gameStateInfo) {
      console.log("✅ Game already initialized!");
      
      // Show current state
      const gameState = await program.account.gameState.fetch(gameStatePda);
      console.log("🎮 Current Game State:");
      console.log(`  Authority: ${gameState.authority}`);
      console.log(`  Treasury: ${gameState.treasuryWallet}`);
      console.log(`  Total Players: ${gameState.totalPlayers}`);
      return;
    }
  } catch (error) {
    console.log("GameState not found, proceeding with initialization...");
  }

  try {
    // Initialize the game
    const treasuryWallet = wallet.publicKey; // Use deployer as treasury for now
    
    console.log("🚀 Calling initialize instruction...");
    console.log(`Treasury wallet will be: ${treasuryWallet}`);
    
    const tx = await program.methods
      .initialize(treasuryWallet)
      .accounts({
        authority: wallet.publicKey,
        gameState: gameStatePda,
        gameConfig: gameConfigPda,
        treasuryPda: treasuryPda,
        systemProgram: new PublicKey("11111111111111111111111111111111"),
      })
      .rpc();

    console.log("✅ Game initialized successfully!");
    console.log(`Transaction: ${tx}`);
    console.log(`View on Solana FM: https://solana.fm/tx/${tx}?cluster=devnet-solana`);
    
    // Wait a bit for confirmation
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Verify initialization
    const gameState = await program.account.gameState.fetch(gameStatePda);
    const gameConfig = await program.account.gameConfig.fetch(gameConfigPda);
    
    console.log("\n🎮 Verification - Game State:");
    console.log(`  Authority: ${gameState.authority}`);
    console.log(`  Treasury: ${gameState.treasuryWallet}`);
    console.log(`  Total Players: ${gameState.totalPlayers}`);
    console.log(`  Total Invested: ${gameState.totalInvested}`);
    
    console.log("\n⚙️ Game Config:");
    console.log(`  Entry Fee: ${gameConfig.entryFee} lamports`);
    console.log(`  Treasury Fee: ${gameConfig.treasuryFeePercent}%`);
    
    console.log("\n🎉 Initialization completed successfully!");
    
  } catch (error) {
    console.error("❌ Initialization failed:");
    console.error("Error message:", error.message);
    if (error.logs) {
      console.error("Program logs:", error.logs);
    }
    process.exit(1);
  }
}

initializeGame().catch(console.error);
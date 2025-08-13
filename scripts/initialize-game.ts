import { Connection, PublicKey, Keypair } from "@solana/web3.js";
import { AnchorProvider, Wallet, Program } from "@coral-xyz/anchor";
import * as fs from "fs";
import * as os from "os";
import idl from "../app/frontend/src/solana_mafia.json";

async function initializeGame() {
  console.log("🎮 Initializing Solana Mafia Game...");
  
  // Setup
  const connection = new Connection("https://api.devnet.solana.com", "confirmed");
  const keypairPath = os.homedir() + "/.config/solana/id.json";
  const keypairData = JSON.parse(fs.readFileSync(keypairPath, "utf8"));
  const wallet = new Wallet(Keypair.fromSecretKey(new Uint8Array(keypairData)));
  
  const provider = new AnchorProvider(connection, wallet, {});
  // Anchor 0.30+ - Program ID now comes from idl.address
  const program = new Program(idl as any, provider);
  
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
      return;
    }
  } catch (error) {
    console.log("Game state not found, proceeding with initialization...");
  }

  try {
    // Initialize the game
    const treasuryWallet = wallet.publicKey; // Use deployer as treasury for now
    
    console.log("🚀 Calling initialize instruction...");
    const tx = await program.methods
      .initialize(treasuryWallet)
      .accounts({
        authority: wallet.publicKey,
        gameState: gameStatePda,
        gameConfig: gameConfigPda,
        treasuryPda: treasuryPda,
        systemProgram: PublicKey.default,
      })
      .rpc();

    console.log("✅ Game initialized successfully!");
    console.log(`Transaction: ${tx}`);
    console.log(`View on Solana FM: https://solana.fm/tx/${tx}?cluster=devnet-solana`);
    
    // Verify initialization
    const gameState = await program.account.gameState.fetch(gameStatePda);
    console.log("🎮 Game State:");
    console.log(`  Authority: ${gameState.authority}`);
    console.log(`  Treasury: ${gameState.treasuryWallet}`);
    console.log(`  Total Players: ${gameState.totalPlayers}`);
    
  } catch (error) {
    console.error("❌ Initialization failed:", error);
    process.exit(1);
  }
}

initializeGame().catch(console.error);
// Reset player account - close and recreate
const anchor = require("@coral-xyz/anchor");
const { Connection, PublicKey, SystemProgram } = require("@solana/web3.js");
const fs = require("fs");
const os = require("os");

async function resetPlayer() {
  console.log("🔄 RESETTING PLAYER ACCOUNT...");
  
  const connection = new Connection("https://api.devnet.solana.com", "confirmed");
  const playerPublicKey = new anchor.web3.PublicKey("DfDkPhcm93C4JyXVRdz8M9B7cP8aeZKS9DNxS5cTxEmE");
  
  // Load your wallet (must be the player wallet)
  const keypairPath = os.homedir() + "/.config/solana/id.json";
  const keypairData = JSON.parse(fs.readFileSync(keypairPath, "utf8"));
  const wallet = new anchor.Wallet(anchor.web3.Keypair.fromSecretKey(new Uint8Array(keypairData)));
  const provider = new anchor.AnchorProvider(connection, wallet, {});
  
  // Load program
  const idl = require("./app/frontend/src/solana_mafia.json");
  const program = new anchor.Program(idl, provider);
  
  // Get PDAs
  const [player] = PublicKey.findProgramAddressSync(
    [Buffer.from("player"), playerPublicKey.toBuffer()],
    program.programId
  );
  
  const [gameConfig] = PublicKey.findProgramAddressSync(
    [Buffer.from("game_config")],
    program.programId
  );
  
  const [gameState] = PublicKey.findProgramAddressSync(
    [Buffer.from("game_state")],
    program.programId
  );
  
  try {
    console.log(`Player wallet: ${playerPublicKey}`);
    console.log(`Player PDA: ${player}`);
    
    // Check current account
    const accountInfo = await connection.getAccountInfo(player);
    if (accountInfo) {
      console.log(`❌ Player account exists but corrupted (${accountInfo.data.length} bytes)`);
      console.log("❗ Account needs to be manually closed and recreated");
      console.log("💡 Try creating a business instead - it will reinitialize the player");
      return;
    }
    
    // If account doesn't exist, create player
    console.log("✅ Player account doesn't exist, creating new one...");
    
    const gameStateAccount = await program.account.gameState.fetch(gameState);
    
    const tx = await program.methods
      .createPlayer()
      .accounts({
        owner: playerPublicKey,
        player: player,
        gameState: gameState,
        gameConfig: gameConfig,
        treasuryWallet: gameStateAccount.treasuryWallet,
        systemProgram: SystemProgram.programId,
      })
      .rpc();
      
    console.log("✅ Player created:", tx);
    
  } catch (error) {
    console.error("❌ Failed to reset player:", error);
    console.log("\n💡 WORKAROUND: Try creating a business - it will auto-initialize the player with current structure!");
  }
}

resetPlayer().catch(console.error);
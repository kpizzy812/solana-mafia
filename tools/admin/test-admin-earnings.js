const { Connection, PublicKey, Keypair } = require("@solana/web3.js");
const { AnchorProvider, Wallet, Program } = require("@coral-xyz/anchor");
const fs = require("fs");
const os = require("os");

async function testAdminEarnings() {
  console.log("🔧 Testing admin earnings update...");
  
  // Setup
  const connection = new Connection("https://api.devnet.solana.com", "confirmed");
  const keypairPath = os.homedir() + "/.config/solana/id.json";
  const keypairData = JSON.parse(fs.readFileSync(keypairPath, "utf8"));
  const adminWallet = new Wallet(Keypair.fromSecretKey(new Uint8Array(keypairData)));
  
  const provider = new AnchorProvider(connection, adminWallet, {});
  
  // Load IDL
  const idl = require("./app/frontend/src/solana_mafia.json");
  const program = new Program(idl, provider);
  
  console.log(`Program ID: ${program.programId}`);
  console.log(`Admin: ${adminWallet.publicKey}`);

  // Target player
  const playerWallet = new PublicKey("9BA18LBbm3wL7Yt4YfumaHAqR7eGFriCLZkpZZMX28BF");
  
  // Find PDAs
  const [gameStatePda] = PublicKey.findProgramAddressSync(
    [Buffer.from("game_state")],
    program.programId
  );
  
  const [playerPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("player"), playerWallet.toBuffer()],
    program.programId
  );

  console.log(`Player wallet: ${playerWallet}`);
  console.log(`Player PDA: ${playerPda}`);
  console.log(`GameState PDA: ${gameStatePda}`);

  try {
    console.log("🚀 Calling update_single_player_earnings...");
    
    const tx = await program.methods
      .updateSinglePlayerEarnings(playerWallet)
      .accounts({
        authority: adminWallet.publicKey,
        targetPlayerWallet: playerWallet,
        player: playerPda,
        gameState: gameStatePda,
      })
      .rpc();

    console.log("✅ Earnings updated successfully!");
    console.log(`Transaction: ${tx}`);
    console.log(`View on Solana FM: https://solana.fm/tx/${tx}?cluster=devnet-solana`);
    
  } catch (error) {
    console.error("❌ Earnings update failed:");
    console.error("Error message:", error.message);
    if (error.logs) {
      console.error("Program logs:", error.logs);
    }
  }
}

testAdminEarnings().catch(console.error);
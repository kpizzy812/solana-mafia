// Детальное тестирование sell_business с полными логами
const anchor = require("@coral-xyz/anchor");
const { Connection, PublicKey, Keypair } = require("@solana/web3.js");
const fs = require("fs");
const os = require("os");

async function testSellBusiness() {
  console.log("🔍 Detailed sell_business debugging...");
  
  // Setup
  const connection = new Connection("https://api.devnet.solana.com", "confirmed");
  const keypairPath = os.homedir() + "/.config/solana/id.json";
  const keypairData = JSON.parse(fs.readFileSync(keypairPath, "utf8"));
  const wallet = new anchor.Wallet(Keypair.fromSecretKey(new Uint8Array(keypairData)));
  const provider = new anchor.AnchorProvider(connection, wallet, {});
  
  // Load program
  const idl = require("./app/frontend/src/solana_mafia.json");
  const program = new anchor.Program(idl, provider);
  
  console.log(`Program ID: ${program.programId}`);
  console.log(`User wallet: ${wallet.publicKey}`);

  // Get PDAs
  const [playerPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("player"), wallet.publicKey.toBuffer()],
    program.programId
  );
  
  const [treasuryPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("treasury")],
    program.programId
  );
  
  const [gameState] = PublicKey.findProgramAddressSync(
    [Buffer.from("game_state")],
    program.programId
  );
  
  const [gameConfig] = PublicKey.findProgramAddressSync(
    [Buffer.from("game_config")],
    program.programId
  );

  try {
    // 1. Check player data
    console.log("\n📊 Checking player data...");
    const playerData = await program.account.player.fetch(playerPda);
    console.log(`Player businesses count: ${playerData.businessSlots.filter(slot => slot.business !== null).length}`);
    
    // Find a business to sell
    let slotIndex = -1;
    for (let i = 0; i < playerData.businessSlots.length; i++) {
      if (playerData.businessSlots[i].business !== null) {
        slotIndex = i;
        console.log(`Found business in slot ${i}:`, playerData.businessSlots[i].business);
        break;
      }
    }
    
    if (slotIndex === -1) {
      console.log("❌ No businesses found to sell");
      return;
    }

    // 2. Check Treasury PDA balance
    console.log("\n💰 Checking Treasury PDA...");
    const treasuryBalance = await connection.getBalance(treasuryPda);
    console.log(`Treasury PDA balance: ${treasuryBalance / 1e9} SOL`);
    
    if (treasuryBalance === 0) {
      console.log("❌ Treasury PDA has no funds!");
      return;
    }

    // 3. Get game state
    const gameStateData = await program.account.gameState.fetch(gameState);
    console.log(`Treasury wallet: ${gameStateData.treasuryWallet}`);

    // 4. Try to sell with detailed error catching
    console.log(`\n🔥 Attempting to sell business in slot ${slotIndex}...`);
    
    try {
      const tx = await program.methods
        .sellBusiness(slotIndex)
        .accounts({
          playerOwner: wallet.publicKey,
          player: playerPda,
          treasuryPda: treasuryPda,
          gameState: gameState,
          gameConfig: gameConfig,
          treasuryWallet: gameStateData.treasuryWallet,
          systemProgram: anchor.web3.SystemProgram.programId,
        })
        .rpc({ skipPreflight: false });
      
      console.log("✅ Business sold successfully!");
      console.log(`Transaction: ${tx}`);
      
    } catch (sellError) {
      console.log("\n❌ DETAILED SELL ERROR:");
      console.log("Error message:", sellError.message);
      
      if (sellError.logs) {
        console.log("\n📋 Program logs:");
        sellError.logs.forEach((log, i) => {
          console.log(`${i}: ${log}`);
        });
      }
      
      if (sellError.error) {
        console.log("\n🔍 Error details:", sellError.error);
      }
      
      // Try to understand the error code
      if (sellError.code) {
        console.log(`\n💡 Error code: ${sellError.code}`);
      }
    }
    
  } catch (error) {
    console.error("❌ Setup error:", error);
  }
}

testSellBusiness().catch(console.error);
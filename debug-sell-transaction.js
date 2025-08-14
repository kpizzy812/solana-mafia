// Тестирование построения sell транзакции без отправки
const anchor = require("@coral-xyz/anchor");
const { Connection, PublicKey, Keypair, SystemProgram } = require("@solana/web3.js");
const fs = require("fs");
const os = require("os");

async function debugSellTransaction() {
  console.log("🔍 DEBUGGING SELL TRANSACTION BUILD...");
  
  // Setup
  const connection = new Connection("https://api.devnet.solana.com", "confirmed");
  // Use the actual player wallet
  const playerPublicKey = new anchor.web3.PublicKey("DfDkPhcm93C4JyXVRdz8M9B7cP8aeZKS9DNxS5cTxEmE");
  
  // Create a dummy wallet for testing (we only need to check account existence)
  const keypairPath = os.homedir() + "/.config/solana/id.json";
  const keypairData = JSON.parse(fs.readFileSync(keypairPath, "utf8"));
  const wallet = new anchor.Wallet(Keypair.fromSecretKey(new Uint8Array(keypairData)));
  const provider = new anchor.AnchorProvider(connection, wallet, {});
  
  // Load program
  const idl = require("./app/frontend/src/solana_mafia.json");
  const program = new anchor.Program(idl, provider);
  
  console.log(`Program ID: ${program.programId}`);
  console.log(`Real player wallet: ${playerPublicKey}`);
  console.log(`Admin wallet (for testing): ${wallet.publicKey}`);

  // Get PDAs for the REAL player
  const [player] = PublicKey.findProgramAddressSync(
    [Buffer.from("player"), playerPublicKey.toBuffer()],
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
  
  const [treasuryPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("treasury")],
    program.programId
  );

  try {
    console.log("\n📍 Generated PDAs:");
    console.log(`Player PDA: ${player.toString()}`);
    console.log(`GameState PDA: ${gameState.toString()}`);
    console.log(`GameConfig PDA: ${gameConfig.toString()}`);
    console.log(`Treasury PDA: ${treasuryPda.toString()}`);

    // Get game state for treasury wallet
    const gameStateAccount = await program.account.gameState.fetch(gameState);
    console.log(`Treasury Wallet: ${gameStateAccount.treasuryWallet.toString()}`);

    // Test 1: Try CURRENT frontend order with REAL player
    console.log("\n🧪 TEST 1: Current frontend order...");
    try {
      const instructionCurrent = await program.methods
        .sellBusiness(0) // slot 0
        .accounts({
          playerOwner: playerPublicKey,
          player: player,
          treasuryPda: treasuryPda,
          gameState: gameState,
          gameConfig: gameConfig,
          treasuryWallet: gameStateAccount.treasuryWallet,
          systemProgram: SystemProgram.programId,
        })
        .instruction();
      
      console.log("✅ Current order transaction built successfully");
      console.log(`Instruction data length: ${instructionCurrent.data.length}`);
      console.log(`Number of accounts: ${instructionCurrent.keys.length}`);
      
      // Print account order
      console.log("\n📋 Account order in instruction:");
      instructionCurrent.keys.forEach((key, i) => {
        console.log(`${i}: ${key.pubkey.toString()} (${key.isSigner ? 'signer' : 'not signer'}, ${key.isWritable ? 'writable' : 'readonly'})`);
      });
      
    } catch (currentError) {
      console.log("❌ Current order failed:", currentError.message);
      
      if (currentError.logs) {
        console.log("Program logs:", currentError.logs);
      }
    }

    // Test 2: Try upgrade business for comparison
    console.log("\n🧪 TEST 2: Upgrade business (working function) for comparison...");
    try {
      const upgradeInstruction = await program.methods
        .upgradeBusiness(0) // slot 0
        .accounts({
          playerOwner: playerPublicKey,
          player: player,
          gameConfig: gameConfig,
          gameState: gameState,
          treasuryWallet: gameStateAccount.treasuryWallet,
          systemProgram: SystemProgram.programId,
        })
        .instruction();
      
      console.log("✅ Upgrade transaction built successfully");
      console.log(`Instruction data length: ${upgradeInstruction.data.length}`);
      console.log(`Number of accounts: ${upgradeInstruction.keys.length}`);
      
      // Print account order
      console.log("\n📋 Account order in upgrade instruction:");
      upgradeInstruction.keys.forEach((key, i) => {
        console.log(`${i}: ${key.pubkey.toString()} (${key.isSigner ? 'signer' : 'not signer'}, ${key.isWritable ? 'writable' : 'readonly'})`);
      });
      
    } catch (upgradeError) {
      console.log("❌ Upgrade order failed:", upgradeError.message);
    }

    // Test 3: Check accounts exist
    console.log("\n🧪 TEST 3: Checking account existence...");
    
    const accounts = [
      { name: "Player", pda: player },
      { name: "GameState", pda: gameState },
      { name: "GameConfig", pda: gameConfig },
      { name: "Treasury PDA", pda: treasuryPda },
      { name: "Treasury Wallet", pda: gameStateAccount.treasuryWallet }
    ];
    
    for (const account of accounts) {
      try {
        const info = await connection.getAccountInfo(account.pda);
        if (info) {
          console.log(`✅ ${account.name}: EXISTS (owner: ${info.owner.toString()}, size: ${info.data.length})`);
        } else {
          console.log(`❌ ${account.name}: NOT FOUND`);
        }
      } catch (e) {
        console.log(`❌ ${account.name}: ERROR - ${e.message}`);
      }
    }
    
  } catch (error) {
    console.error("❌ Debug failed:", error);
  }
}

debugSellTransaction().catch(console.error);
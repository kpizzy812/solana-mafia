// Тестирование разных порядков аккаунтов для sell_business
const anchor = require("@coral-xyz/anchor");
const { Connection, PublicKey, Keypair, SystemProgram } = require("@solana/web3.js");
const fs = require("fs");
const os = require("os");

async function testAccountOrders() {
  console.log("🧪 TESTING DIFFERENT ACCOUNT ORDERS FOR SELL_BUSINESS...");
  
  // Setup
  const connection = new Connection("https://api.devnet.solana.com", "confirmed");
  const keypairPath = os.homedir() + "/.config/solana/id.json";
  const keypairData = JSON.parse(fs.readFileSync(keypairPath, "utf8"));
  const wallet = new anchor.Wallet(Keypair.fromSecretKey(new Uint8Array(keypairData)));
  const provider = new anchor.AnchorProvider(connection, wallet, {});
  
  // Load program
  const idl = require("./app/frontend/src/solana_mafia.json");
  const program = new anchor.Program(idl, provider);

  // Get PDAs
  const [player] = PublicKey.findProgramAddressSync(
    [Buffer.from("player"), wallet.publicKey.toBuffer()],
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
    // Get game state for treasury wallet
    const gameStateAccount = await program.account.gameState.fetch(gameState);

    // Test different account orders based on contract struct
    const testCases = [
      {
        name: "CURRENT FRONTEND ORDER",
        accounts: {
          playerOwner: wallet.publicKey,
          player: player,
          treasuryPda: treasuryPda,
          gameState: gameState,
          gameConfig: gameConfig,
          treasuryWallet: gameStateAccount.treasuryWallet,
          systemProgram: SystemProgram.programId,
        }
      },
      {
        name: "CONTRACT ORDER (based on SellBusinessFromSlot struct)",
        accounts: {
          playerOwner: wallet.publicKey,
          player: player,
          treasuryPda: treasuryPda,
          gameState: gameState,
          gameConfig: gameConfig,
          treasuryWallet: gameStateAccount.treasuryWallet,
          systemProgram: SystemProgram.programId,
        }
      },
      {
        name: "ALPHABETICAL ORDER",
        accounts: {
          gameConfig: gameConfig,
          gameState: gameState,
          player: player,
          playerOwner: wallet.publicKey,
          systemProgram: SystemProgram.programId,
          treasuryPda: treasuryPda,
          treasuryWallet: gameStateAccount.treasuryWallet,
        }
      },
      {
        name: "UPGRADE-LIKE ORDER (without treasuryPda)",
        accounts: {
          playerOwner: wallet.publicKey,
          player: player,
          gameState: gameState,
          gameConfig: gameConfig,
          treasuryWallet: gameStateAccount.treasuryWallet,
          systemProgram: SystemProgram.programId,
          // treasuryPda: treasuryPda, // REMOVED to match upgrade
        }
      }
    ];

    for (const testCase of testCases) {
      console.log(`\n🧪 Testing: ${testCase.name}`);
      
      try {
        const instruction = await program.methods
          .sellBusiness(0)
          .accounts(testCase.accounts)
          .instruction();
        
        console.log(`✅ SUCCESS: Transaction built successfully`);
        console.log(`   Instruction size: ${instruction.data.length} bytes`);
        console.log(`   Account count: ${instruction.keys.length}`);
        
        // Show account addresses in order
        console.log("   Account order:");
        instruction.keys.forEach((key, i) => {
          let accountName = "unknown";
          if (key.pubkey.equals(wallet.publicKey)) accountName = "playerOwner";
          else if (key.pubkey.equals(player)) accountName = "player";
          else if (key.pubkey.equals(treasuryPda)) accountName = "treasuryPda";
          else if (key.pubkey.equals(gameState)) accountName = "gameState";
          else if (key.pubkey.equals(gameConfig)) accountName = "gameConfig";
          else if (key.pubkey.equals(gameStateAccount.treasuryWallet)) accountName = "treasuryWallet";
          else if (key.pubkey.equals(SystemProgram.programId)) accountName = "systemProgram";
          
          console.log(`     ${i}: ${accountName} (${key.isSigner ? 'signer' : 'readonly'}, ${key.isWritable ? 'writable' : 'readonly'})`);
        });
        
      } catch (error) {
        console.log(`❌ FAILED: ${error.message}`);
        
        if (error.code) {
          console.log(`   Error code: ${error.code}`);
        }
        
        if (error.logs && error.logs.length > 0) {
          console.log("   Program logs:");
          error.logs.forEach((log, i) => {
            console.log(`     ${i}: ${log}`);
          });
        }
        
        // Try to understand the specific error
        if (error.message.includes("unknown account")) {
          console.log("   → Likely account name mismatch");
        } else if (error.message.includes("AccountNotFound")) {
          console.log("   → One of the accounts doesn't exist");
        } else if (error.message.includes("constraint")) {
          console.log("   → Account constraint violation");
        } else if (error.message.includes("seed")) {
          console.log("   → PDA seed mismatch");
        }
      }
    }

    // Show IDL structure for reference
    console.log("\n📋 IDL instruction structure for reference:");
    const sellBusinessIdl = idl.instructions.find(ix => ix.name === "sellBusiness");
    if (sellBusinessIdl) {
      console.log("Accounts in IDL order:");
      sellBusinessIdl.accounts.forEach((acc, i) => {
        console.log(`  ${i}: ${acc.name} (${acc.isMut ? 'mut' : 'immut'}, ${acc.isSigner ? 'signer' : 'not signer'})`);
      });
    }
    
  } catch (error) {
    console.error("❌ Test setup failed:", error);
  }
}

testAccountOrders().catch(console.error);
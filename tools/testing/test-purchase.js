const { PublicKey, Connection, Keypair, SystemProgram } = require("@solana/web3.js");
const { AnchorProvider, Wallet, Program, BN } = require("@coral-xyz/anchor");
const { TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID, getAssociatedTokenAddress } = require("@solana/spl-token");

async function testPurchase() {
  console.log("🧪 Testing business purchase transaction...");

  try {
    // Setup
    const connection = new Connection("https://api.devnet.solana.com", "confirmed");
    const programId = new PublicKey("HifXYhFJapXPeBgKKZu8gmdc7cZvfERJ9aEkchHxyBLS");
    
    // User wallet (your address)
    const userPublicKey = new PublicKey("DfDkPhcm93C4JyXVRdz8M9B7cP8aeZKS9DNxS5cTxEmE");
    
    // Create dummy wallet for testing
    const dummyWallet = new Wallet(Keypair.generate());
    const provider = new AnchorProvider(connection, dummyWallet, { preflightCommitment: 'confirmed' });

    // Load IDL manually to avoid the size issue
    const fs = require('fs');
    const idlRaw = fs.readFileSync('./target/idl/solana_mafia.json', 'utf8');
    const idl = JSON.parse(idlRaw);

    console.log("Creating program instance...");
    let program;
    try {
      program = new Program(idl, programId, provider);
      console.log("✅ Program instance created");
    } catch (error) {
      console.log("❌ Failed to create program instance:", error.message);
      console.log("💡 Using direct connection approach instead...");
      
      // Let's at least validate the accounts manually
      await validateAccounts(connection, userPublicKey, programId);
      return;
    }

    // Test with your actual user address
    await testWithUser(program, userPublicKey);

  } catch (error) {
    console.error("❌ Test failed:", error);
  }
}

async function validateAccounts(connection, userPublicKey, programId) {
  console.log("\n🔍 Validating accounts manually...");

  // Get PDAs
  const [gameState] = PublicKey.findProgramAddressSync(
    [Buffer.from("game_state")],
    programId
  );
  const [gameConfig] = PublicKey.findProgramAddressSync(
    [Buffer.from("game_config")],
    programId
  );
  const [player] = PublicKey.findProgramAddressSync(
    [Buffer.from("player"), userPublicKey.toBuffer()],
    programId
  );
  const [treasury] = PublicKey.findProgramAddressSync(
    [Buffer.from("treasury")],
    programId
  );

  // Generate test NFT mint
  const nftMint = Keypair.generate();
  const [businessNftPDA] = PublicKey.findProgramAddressSync(
    [Buffer.from("business_nft"), nftMint.publicKey.toBuffer()],
    programId
  );

  const nftTokenAccount = await getAssociatedTokenAddress(
    nftMint.publicKey,
    userPublicKey
  );

  const [nftMetadata] = PublicKey.findProgramAddressSync(
    [
      Buffer.from("metadata"),
      new PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s").toBuffer(),
      nftMint.publicKey.toBuffer()
    ],
    new PublicKey("metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s")
  );

  console.log("📋 Account addresses:");
  console.log(`- User: ${userPublicKey.toString()}`);
  console.log(`- Player: ${player.toString()}`);
  console.log(`- Game State: ${gameState.toString()}`);
  console.log(`- Game Config: ${gameConfig.toString()}`);
  console.log(`- Treasury: ${treasury.toString()}`);
  console.log(`- NFT Mint: ${nftMint.publicKey.toString()}`);
  console.log(`- NFT Token Account: ${nftTokenAccount.toString()}`);
  console.log(`- Business NFT PDA: ${businessNftPDA.toString()}`);
  console.log(`- NFT Metadata: ${nftMetadata.toString()}`);

  // Check which accounts exist
  const accounts = [
    { name: "Game State", pubkey: gameState },
    { name: "Game Config", pubkey: gameConfig },
    { name: "Player", pubkey: player },
    { name: "Treasury", pubkey: treasury },
  ];

  for (const account of accounts) {
    const info = await connection.getAccountInfo(account.pubkey);
    if (info) {
      console.log(`✅ ${account.name}: exists (${info.data.length} bytes)`);
    } else {
      console.log(`❌ ${account.name}: does not exist`);
    }
  }

  // Check user balance
  const balance = await connection.getBalance(userPublicKey);
  console.log(`💰 User balance: ${balance / 1e9} SOL`);
}

async function testWithUser(program, userPublicKey) {
  console.log(`\n🎯 Testing with user: ${userPublicKey.toString()}`);

  // Get PDAs
  const [gameState] = PublicKey.findProgramAddressSync(
    [Buffer.from("game_state")],
    program.programId
  );
  const [player] = PublicKey.findProgramAddressSync(
    [Buffer.from("player"), userPublicKey.toBuffer()],
    program.programId
  );

  try {
    // Check if player exists
    const playerAccount = await program.account.player.fetch(player);
    console.log("✅ Player account found");
    console.log(`- Business Count: ${playerAccount.businessCount}`);
    console.log(`- Total Invested: ${playerAccount.totalInvested} lamports`);
    console.log(`- Has Paid Entry: ${playerAccount.hasPaidEntry}`);

    // Check slots
    console.log("\n🎰 Business Slots:");
    for (let i = 0; i < playerAccount.businessSlots.length; i++) {
      const slot = playerAccount.businessSlots[i];
      console.log(`Slot ${i}: ${slot.isUnlocked ? 'Unlocked' : 'Locked'}, ${slot.business ? 'Has Business' : 'Empty'}`);
    }

  } catch (error) {
    console.error("❌ Failed to fetch player:", error.message);
  }

  try {
    // Check game state
    const gameStateAccount = await program.account.gameState.fetch(gameState);
    console.log("✅ Game State found");
    console.log(`- Total Players: ${gameStateAccount.totalPlayers}`);
    console.log(`- Treasury Wallet: ${gameStateAccount.treasuryWallet}`);
  } catch (error) {
    console.error("❌ Failed to fetch game state:", error.message);
  }
}

testPurchase().catch(console.error);
const { PublicKey, Connection } = require("@solana/web3.js");

async function checkPlayer() {
  console.log("🔍 Checking player account...");

  const connection = new Connection("https://api.devnet.solana.com", "confirmed");
  const programId = new PublicKey("HifXYhFJapXPeBgKKZu8gmdc7cZvfERJ9aEkchHxyBLS");
  const userPublicKey = new PublicKey("DfDkPhcm93C4JyXVRdz8M9B7cP8aeZKS9DNxS5cTxEmE");

  // Find player PDA
  const [playerPDA] = PublicKey.findProgramAddressSync(
    [Buffer.from("player"), userPublicKey.toBuffer()],
    programId
  );

  console.log(`User: ${userPublicKey.toString()}`);
  console.log(`Player PDA: ${playerPDA.toString()}`);

  // Check if player account exists
  const playerInfo = await connection.getAccountInfo(playerPDA);
  
  if (playerInfo) {
    console.log("✅ Player account exists!");
    console.log(`- Size: ${playerInfo.data.length} bytes`);
    console.log(`- Owner: ${playerInfo.owner.toString()}`);
    
    // Try to decode some basic info
    if (playerInfo.data.length > 50) {
      // Skip discriminator (8 bytes) + owner (32 bytes)
      // business_count is at offset 40 (u8)
      const businessCount = playerInfo.data.readUInt8(40);
      console.log(`- Business Count: ${businessCount}`);
      
      // total_invested at offset 48 (u64)
      const totalInvested = playerInfo.data.readBigUInt64LE(48);
      console.log(`- Total Invested: ${totalInvested} lamports (${Number(totalInvested) / 1e9} SOL)`);
    }
  } else {
    console.log("❌ Player account doesn't exist");
    console.log("💡 This means the createPlayer transaction didn't succeed");
  }

  // Check if any transactions were made by this user
  console.log("\n🔍 Checking recent transactions...");
  const signatures = await connection.getSignaturesForAddress(userPublicKey, { limit: 10 });
  
  if (signatures.length > 0) {
    console.log(`Found ${signatures.length} recent transactions:`);
    for (let i = 0; i < Math.min(signatures.length, 5); i++) {
      const sig = signatures[i];
      console.log(`- ${sig.signature} (${sig.confirmationStatus})`);
    }
  } else {
    console.log("No recent transactions found");
  }

  // Check if there are any businesses/NFTs
  console.log("\n🔍 Checking for NFTs...");
  try {
    const tokenAccounts = await connection.getParsedTokenAccountsByOwner(userPublicKey, {
      programId: new PublicKey("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
    });
    
    console.log(`Found ${tokenAccounts.value.length} token accounts`);
    for (const account of tokenAccounts.value.slice(0, 3)) {
      const mintAddress = account.account.data.parsed.info.mint;
      const amount = account.account.data.parsed.info.tokenAmount.uiAmount;
      console.log(`- Mint: ${mintAddress}, Amount: ${amount}`);
    }
  } catch (error) {
    console.log("Failed to fetch token accounts:", error.message);
  }
}

checkPlayer().catch(console.error);
// Проверка состояния аккаунта игрока
const anchor = require("@coral-xyz/anchor");
const { Connection, PublicKey } = require("@solana/web3.js");
const fs = require("fs");
const os = require("os");

async function debugPlayerAccount() {
  console.log("🔍 DEBUGGING PLAYER ACCOUNT STATE...");
  
  const connection = new Connection("https://api.devnet.solana.com", "confirmed");
  const playerPublicKey = new anchor.web3.PublicKey("DfDkPhcm93C4JyXVRdz8M9B7cP8aeZKS9DNxS5cTxEmE");
  
  // Create dummy wallet for provider
  const keypairPath = os.homedir() + "/.config/solana/id.json";
  const keypairData = JSON.parse(fs.readFileSync(keypairPath, "utf8"));
  const wallet = new anchor.Wallet(anchor.web3.Keypair.fromSecretKey(new Uint8Array(keypairData)));
  const provider = new anchor.AnchorProvider(connection, wallet, {});
  
  // Load program
  const idl = require("./app/frontend/src/solana_mafia.json");
  const program = new anchor.Program(idl, provider);
  
  // Get player PDA
  const [player] = PublicKey.findProgramAddressSync(
    [Buffer.from("player"), playerPublicKey.toBuffer()],
    program.programId
  );
  
  try {
    console.log(`Player wallet: ${playerPublicKey}`);
    console.log(`Player PDA: ${player}`);
    
    // Check if account exists first
    const accountInfo = await connection.getAccountInfo(player);
    if (!accountInfo) {
      console.log("❌ Player account does not exist!");
      return;
    }
    
    console.log(`✅ Player account exists (size: ${accountInfo.data.length} bytes)`);
    
    // Try to fetch player account 
    let playerAccount;
    try {
      playerAccount = await program.account.player.fetch(player);
    } catch (e) {
      console.log("❌ Failed to deserialize player account, trying raw access...");
      console.log("Account owner:", accountInfo.owner.toString());
      console.log("Account data preview:", accountInfo.data.slice(0, 32));
      return;
    }
    
    console.log("\n📊 PLAYER ACCOUNT DATA:");
    console.log(`Owner: ${playerAccount.owner}`);
    console.log(`Created at: ${new Date(playerAccount.createdAt * 1000)}`);
    console.log(`Total invested: ${playerAccount.totalInvested}`);
    console.log(`Business slots count: ${playerAccount.businessSlots.length}`);
    
    console.log("\n🏪 BUSINESS SLOTS:");
    playerAccount.businessSlots.forEach((slot, index) => {
      console.log(`Slot ${index}:`, {
        hasBusiness: !!slot.business,
        business: slot.business ? {
          businessType: slot.business.businessType?.toString(),
          isActive: slot.business.isActive,
          createdAt: new Date(slot.business.createdAt * 1000),
          baseInvestment: slot.business.baseInvestment?.toString(),
          upgradeLevel: slot.business.upgradeLevel
        } : null
      });
    });
    
    // Проверяем конкретно слот 0
    const slot0 = playerAccount.businessSlots[0];
    console.log("\n🎯 SLOT 0 DETAILED CHECK:");
    console.log("Raw slot data:", slot0);
    
    if (slot0?.business) {
      console.log("✅ Slot 0 has business");
      console.log("Business type:", slot0.business.businessType);
      console.log("Is active:", slot0.business.isActive);
    } else {
      console.log("❌ Slot 0 has NO business - this explains the crash!");
    }
    
  } catch (error) {
    console.error("❌ Failed to fetch player account:", error);
  }
}

debugPlayerAccount().catch(console.error);
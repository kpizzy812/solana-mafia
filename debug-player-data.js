const { Connection, PublicKey, Keypair } = require("@solana/web3.js");
const { AnchorProvider, Wallet, Program } = require("@coral-xyz/anchor");
const fs = require("fs");
const os = require("os");

async function debugPlayerData() {
  console.log("🔍 Debug: Проверяем данные игрока ончейн...");
  
  // Setup
  const connection = new Connection("https://api.devnet.solana.com", "confirmed");
  const keypairPath = os.homedir() + "/.config/solana/id.json";
  const keypairData = JSON.parse(fs.readFileSync(keypairPath, "utf8"));
  const wallet = new Wallet(Keypair.fromSecretKey(new Uint8Array(keypairData)));
  
  const provider = new AnchorProvider(connection, wallet, {});
  
  // Load IDL
  const idl = require("./app/frontend/src/solana_mafia.json");
  const program = new Program(idl, provider);
  
  console.log(`Program ID: ${program.programId}`);

  // Target player wallet
  const playerWallet = new PublicKey("2FRZFt4Ko2jYzGS221sizYC1v2hcizn8AjtgHxiJTzMU");
  
  // Find player PDA
  const [playerPDA] = PublicKey.findProgramAddressSync(
    [Buffer.from("player"), playerWallet.toBytes()],
    program.programId
  );
  
  console.log(`Player wallet: ${playerWallet}`);
  console.log(`Player PDA: ${playerPDA}`);

  try {
    // Fetch player data
    const playerData = await program.account.playerCompact.fetch(playerPDA);
    
    console.log("\n🎮 ДАННЫЕ ИГРОКА ОНЧЕЙН:");
    console.log(`Owner: ${playerData.owner}`);
    console.log(`Total invested: ${playerData.totalInvested}`);
    console.log(`Pending earnings: ${playerData.pendingEarnings}`);
    console.log(`Unlocked slots: ${playerData.unlockedSlotsCount}`);
    
    console.log("\n🏪 СЛОТЫ И БИЗНЕСЫ:");
    playerData.businessSlots.forEach((slot, index) => {
      console.log(`\n--- СЛОТ ${index} ---`);
      console.log(`  Raw slot:`, slot);
      console.log(`  Flags: ${slot.flags}`);
      console.log(`  Slot cost paid: ${slot.slotCostPaid}`);
      
      if (slot.business) {
        const business = slot.business;
        console.log(`  📊 BUSINESS:`);
        console.log(`    Type: ${getBusinessTypeName(business.businessType)}`);
        console.log(`    Base invested: ${business.baseInvestedAmount}`);
        console.log(`    Total invested: ${business.totalInvestedAmount}`);
        console.log(`    Upgrade level: ${business.upgradeLevel}`);
        console.log(`    Daily rate: ${business.dailyRate}`);
        console.log(`    Active: ${business.isActive}`);
        console.log(`    Created at: ${new Date(business.createdAt * 1000).toISOString()}`);
      }
    });
    
    console.log("\n🔍 ANALYSIS:");
    const activeBusiness = playerData.businessSlots
      .map((slot, index) => ({ slot, index }))
      .filter(({ slot }) => slot.business);
      
    console.log(`Total active businesses: ${activeBusiness.length}`);
    activeBusiness.forEach(({ slot, index }) => {
      console.log(`Business in slot ${index}: ${getBusinessTypeName(slot.business.businessType)} (Level ${slot.business.upgradeLevel})`);
    });
    
  } catch (error) {
    console.error("❌ Ошибка получения данных игрока:");
    console.error("Error:", error.message);
    if (error.logs) {
      console.error("Logs:", error.logs);
    }
  }
}

function getSlotTypeName(slotType) {
  switch (slotType) {
    case 0: return "Basic";
    case 1: return "Premium"; 
    case 2: return "VIP";
    case 3: return "Legendary";
    default: return `Unknown(${slotType})`;
  }
}

function getBusinessTypeName(businessType) {
  const types = ["TobaccoShop", "FuneralService", "CarWorkshop", "ItalianRestaurant", "GentlemenClub", "CharityFund"];
  return types[businessType] || `Unknown(${businessType})`;
}

debugPlayerData().catch(console.error);
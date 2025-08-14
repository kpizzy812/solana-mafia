// Проверка структуры IDL для понимания правильного порядка аккаунтов
const fs = require("fs");

function checkIdlStructure() {
  console.log("📋 CHECKING IDL STRUCTURE FOR ACCOUNT ORDER...");
  
  try {
    // Load IDL
    const idl = require("./app/frontend/src/solana_mafia.json");
    
    console.log(`\nProgram: ${idl.name} (address: ${idl.address})`);
    
    // Find sell_business instruction - trying different possible names
    const sellInstruction = idl.instructions.find(ix => 
      ix.name === "sellBusiness" || ix.name === "sell_business"
    );
    const upgradeInstruction = idl.instructions.find(ix => 
      ix.name === "upgradeBusiness" || ix.name === "upgrade_business"
    );
    
    console.log("Available instruction names:", idl.instructions.map(ix => ix.name));
    
    if (sellInstruction) {
      console.log("\n🔥 SELL_BUSINESS INSTRUCTION:");
      console.log("Expected account order from IDL:");
      sellInstruction.accounts.forEach((acc, i) => {
        console.log(`  ${i}: ${acc.name} (${acc.isMut ? 'mut' : 'immut'}, ${acc.isSigner ? 'signer' : 'not signer'})`);
        
        if (acc.pda && acc.pda.seeds) {
          console.log(`      PDA seeds: ${acc.pda.seeds.map(seed => {
            if (seed.kind === "const") {
              return `"${Buffer.from(seed.value).toString()}"`;
            } else if (seed.kind === "account") {
              return `${seed.path}.key()`;
            }
            return seed.kind;
          }).join(", ")}`);
        }
      });
      
      console.log("\nParameters:");
      sellInstruction.args.forEach((arg, i) => {
        console.log(`  ${i}: ${arg.name} (${arg.type})`);
      });
    } else {
      console.log("❌ sell_business instruction not found in IDL");
    }
    
    if (upgradeInstruction) {
      console.log("\n🔄 UPGRADE_BUSINESS INSTRUCTION (for comparison):");
      console.log("Expected account order from IDL:");
      upgradeInstruction.accounts.forEach((acc, i) => {
        console.log(`  ${i}: ${acc.name} (${acc.isMut ? 'mut' : 'immut'}, ${acc.isSigner ? 'signer' : 'not signer'})`);
      });
    }
    
    // Show all instructions for reference
    console.log("\n📚 ALL INSTRUCTIONS IN IDL:");
    idl.instructions.forEach((ix, i) => {
      console.log(`  ${i}: ${ix.name} (${ix.accounts.length} accounts, ${ix.args.length} args)`);
    });
    
    // Check account types
    console.log("\n🏗️ ACCOUNT TYPES:");
    if (idl.accounts) {
      idl.accounts.forEach((acc, i) => {
        const fields = acc.type?.fields || acc.type?.kind?.fields || [];
        console.log(`  ${i}: ${acc.name} (size: ${Array.isArray(fields) ? fields.length + ' fields' : 'unknown'})`);
      });
    }
    
    // Show events for reference
    console.log("\n📢 EVENTS:");
    if (idl.events) {
      idl.events.forEach((event, i) => {
        console.log(`  ${i}: ${event.name} (${event.fields.length} fields)`);
      });
    }
    
  } catch (error) {
    console.error("❌ Failed to check IDL structure:", error);
  }
}

checkIdlStructure();
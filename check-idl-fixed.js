// Исправленная проверка структуры IDL для понимания правильного порядка аккаунтов
const fs = require("fs");

function checkIdlStructure() {
  console.log("📋 CHECKING IDL STRUCTURE FOR ACCOUNT ORDER...");
  
  try {
    // Load IDL
    const idl = require("./app/frontend/src/solana_mafia.json");
    
    console.log(`\nProgram: ${idl.name || 'unknown'} (address: ${idl.address})`);
    console.log(`IDL version: ${idl.version || 'unknown'}`);
    
    // Show all instruction names first
    console.log("\n📚 ALL INSTRUCTIONS IN IDL:");
    idl.instructions.forEach((ix, i) => {
      console.log(`  ${i}: ${ix.name} (${ix.accounts.length} accounts, ${ix.args.length} args)`);
    });
    
    // Get sell_business (index 10) and upgrade_business (index 13)
    const sellInstruction = idl.instructions[10]; // sell_business
    const upgradeInstruction = idl.instructions[13]; // upgrade_business
    
    if (sellInstruction && sellInstruction.name === "sell_business") {
      console.log("\n🔥 SELL_BUSINESS INSTRUCTION:");
      console.log("Expected account order from IDL:");
      sellInstruction.accounts.forEach((acc, i) => {
        const mutability = acc.isMut ? 'mut' : 'immut';
        const signer = acc.isSigner ? 'signer' : 'not signer';
        console.log(`  ${i}: ${acc.name} (${mutability}, ${signer})`);
        
        // Show PDA info if available
        if (acc.pda && acc.pda.seeds) {
          const seeds = acc.pda.seeds.map(seed => {
            if (seed.kind === "const") {
              return `"${Buffer.from(seed.value).toString()}"`;
            } else if (seed.kind === "account") {
              return `${seed.path}.key()`;
            }
            return seed.kind;
          }).join(", ");
          console.log(`      PDA seeds: [${seeds}]`);
        }
      });
      
      console.log("\nParameters:");
      sellInstruction.args.forEach((arg, i) => {
        console.log(`  ${i}: ${arg.name} (${arg.type})`);
      });
    } else {
      console.log("❌ sell_business instruction not found at expected index 10");
      console.log(`Found at index 10: ${sellInstruction?.name}`);
    }
    
    if (upgradeInstruction && upgradeInstruction.name === "upgrade_business") {
      console.log("\n🔄 UPGRADE_BUSINESS INSTRUCTION (for comparison):");
      console.log("Expected account order from IDL:");
      upgradeInstruction.accounts.forEach((acc, i) => {
        const mutability = acc.isMut ? 'mut' : 'immut';
        const signer = acc.isSigner ? 'signer' : 'not signer';
        console.log(`  ${i}: ${acc.name} (${mutability}, ${signer})`);
      });
      
      console.log("\nParameters:");
      upgradeInstruction.args.forEach((arg, i) => {
        console.log(`  ${i}: ${arg.name} (${arg.type})`);
      });
    } else {
      console.log("❌ upgrade_business instruction not found at expected index 13");
      console.log(`Found at index 13: ${upgradeInstruction?.name}`);
    }
    
    // Compare the two instructions
    if (sellInstruction && upgradeInstruction) {
      console.log("\n🔍 COMPARISON:");
      console.log(`Sell business accounts: ${sellInstruction.accounts.length}`);
      console.log(`Upgrade business accounts: ${upgradeInstruction.accounts.length}`);
      console.log(`Difference: ${sellInstruction.accounts.length - upgradeInstruction.accounts.length} extra account(s) in sell`);
      
      // Find which accounts are different
      console.log("\n📊 ACCOUNT DIFFERENCES:");
      console.log("SELL BUSINESS accounts:");
      sellInstruction.accounts.forEach((acc, i) => {
        console.log(`  ${i}: ${acc.name}`);
      });
      
      console.log("UPGRADE BUSINESS accounts:");
      upgradeInstruction.accounts.forEach((acc, i) => {
        console.log(`  ${i}: ${acc.name}`);
      });
    }
    
    // Check for claim_earnings too (has treasury_pda and works)
    const claimInstruction = idl.instructions[1]; // claim_earnings
    if (claimInstruction && claimInstruction.name === "claim_earnings") {
      console.log("\n💰 CLAIM_EARNINGS INSTRUCTION (also has treasury_pda):");
      console.log("Expected account order from IDL:");
      claimInstruction.accounts.forEach((acc, i) => {
        const mutability = acc.isMut ? 'mut' : 'immut';
        const signer = acc.isSigner ? 'signer' : 'not signer';
        console.log(`  ${i}: ${acc.name} (${mutability}, ${signer})`);
      });
    }
    
  } catch (error) {
    console.error("❌ Failed to check IDL structure:", error);
  }
}

checkIdlStructure();
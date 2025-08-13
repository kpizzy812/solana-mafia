const { Connection } = require("@solana/web3.js");

async function checkTransaction() {
  console.log("🔍 Checking last transaction...");

  const connection = new Connection("https://api.devnet.solana.com", "confirmed");
  
  // Latest transaction signature from the previous output
  const signature = "5k8RXz7FLiwS34xMigB3UzqmrrjFDLMYX9mhwHbXoypNLaA9AUsBVoPXVLdnuf6ziv7twnBgkaMGYdE4W18r2kbr";
  
  try {
    const transaction = await connection.getParsedTransaction(signature, {
      maxSupportedTransactionVersion: 0
    });
    
    if (!transaction) {
      console.log("❌ Transaction not found");
      return;
    }
    
    console.log(`✅ Transaction found:`);
    console.log(`- Slot: ${transaction.slot}`);
    console.log(`- Block Time: ${new Date(transaction.blockTime * 1000).toISOString()}`);
    console.log(`- Success: ${transaction.meta.err === null}`);
    
    if (transaction.meta.err) {
      console.log(`❌ Transaction failed:`, transaction.meta.err);
    } else {
      console.log(`✅ Transaction succeeded`);
    }
    
    console.log(`\n📝 Transaction Logs:`);
    if (transaction.meta.logMessages) {
      transaction.meta.logMessages.forEach((log, i) => {
        if (log.includes('Error') || log.includes('failed') || log.includes('Program log:')) {
          console.log(`${i}: ${log}`);
        }
      });
    }
    
    console.log(`\n💰 Balance Changes:`);
    if (transaction.meta.preBalances && transaction.meta.postBalances) {
      transaction.transaction.message.accountKeys.forEach((account, i) => {
        const preBalance = transaction.meta.preBalances[i];
        const postBalance = transaction.meta.postBalances[i];
        const change = postBalance - preBalance;
        
        if (change !== 0) {
          console.log(`- ${account.pubkey}: ${change / 1e9} SOL`);
        }
      });
    }
    
    console.log(`\n🎯 Instructions:`);
    transaction.transaction.message.instructions.forEach((instruction, i) => {
      console.log(`${i}: Program ${instruction.programId} - ${JSON.stringify(instruction, null, 2)}`);
    });
    
  } catch (error) {
    console.error("❌ Failed to fetch transaction:", error);
  }
}

checkTransaction().catch(console.error);
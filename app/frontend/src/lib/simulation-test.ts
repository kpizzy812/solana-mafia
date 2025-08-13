import { Connection, PublicKey, Transaction } from '@solana/web3.js';

/**
 * Test transaction simulation on different RPC endpoints
 * to find one that works best with wallet preview
 */

const TEST_ENDPOINTS = [
  'https://api.devnet.solana.com',
  'https://devnet.helius-rpc.com/?api-key=demo', // Demo key, replace with real key
  // Add more endpoints as needed
];

export const testSimulationEndpoints = async (transaction: Transaction) => {
  console.log('🧪 Testing simulation on different RPC endpoints...');
  
  for (const endpoint of TEST_ENDPOINTS) {
    try {
      console.log(`Testing ${endpoint}...`);
      const testConnection = new Connection(endpoint, 'confirmed');
      
      const result = await testConnection.simulateTransaction(transaction, {
        sigVerify: false,
        commitment: 'confirmed'
      });
      
      if (!result.value.err) {
        console.log(`✅ ${endpoint} simulation successful!`);
        console.log(`Compute units: ${result.value.unitsConsumed}`);
        return { success: true, endpoint, result: result.value };
      } else {
        console.log(`❌ ${endpoint} simulation failed:`, result.value.err);
      }
    } catch (error) {
      console.log(`❌ ${endpoint} connection failed:`, error);
    }
  }
  
  return { success: false, endpoint: null, result: null };
};

/**
 * Enhanced transaction for better wallet preview
 */
export const prepareTransactionForPreview = (transaction: Transaction) => {
  // Add memo instruction for better description in wallet
  // This can help wallets show more context about the transaction
  
  console.log('📝 Preparing transaction for wallet preview...');
  console.log('Transaction details:', {
    instructions: transaction.instructions.length,
    feePayer: transaction.feePayer?.toString(),
    recentBlockhash: transaction.recentBlockhash?.slice(0, 8) + '...'
  });
  
  return transaction;
};
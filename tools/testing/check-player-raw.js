import { Connection, PublicKey } from '@solana/web3.js';

const connection = new Connection('https://api.devnet.solana.com');
const PROGRAM_ID = new PublicKey('HifXYhFJapXPeBgKKZu8gmdc7cZvfERJ9aEkchHxyBLS');
const USER_PUBKEY = new PublicKey('DfDkPhcm93C4JyXVRdz8M9B7cP8aeZKS9DNxS5cTxEmE');

(async () => {
  try {
    // Get player PDA
    const [playerPda] = PublicKey.findProgramAddressSync(
      [Buffer.from('player'), USER_PUBKEY.toBuffer()],
      PROGRAM_ID
    );
    
    console.log('🔍 Проверка аккаунта игрока через RPC...');
    console.log('User:', USER_PUBKEY.toString());
    console.log('Player PDA:', playerPda.toString());
    
    // Get account info
    const accountInfo = await connection.getAccountInfo(playerPda);
    
    if (!accountInfo) {
      console.log('❌ Account not found');
      return;
    }
    
    console.log('✅ Account found!');
    console.log('- Size:', accountInfo.data.length, 'bytes');
    console.log('- Owner:', accountInfo.owner.toString());
    console.log('- Lamports:', accountInfo.lamports);
    
    // Try to parse some basic data manually
    const data = accountInfo.data;
    console.log('\\n📊 Raw data analysis:');
    console.log('- First 32 bytes (likely owner):', data.subarray(0, 32).toString('hex'));
    
    // Look for business data patterns
    console.log('\\n🔍 Looking for business data patterns...');
    for (let i = 32; i < Math.min(data.length, 500); i += 4) {
      const value = data.readUInt32LE(i);
      if (value > 0 && value < 1000000000) { // Reasonable range for business data
        console.log(`Offset ${i}: ${value} (0x${value.toString(16)})`);
      }
    }
    
    // Check NFT tokens
    console.log('\\n🎯 Checking NFT token accounts...');
    const tokenAccounts = await connection.getTokenAccountsByOwner(USER_PUBKEY, {
      programId: new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
    });
    
    console.log(`Found ${tokenAccounts.value.length} token accounts:`);
    for (const account of tokenAccounts.value) {
      const accountData = account.account.data;
      const mint = new PublicKey(accountData.subarray(0, 32));
      const owner = new PublicKey(accountData.subarray(32, 64));
      const amount = accountData.readBigUInt64LE(64);
      
      if (amount > 0n) {
        console.log(`- Mint: ${mint.toString()}, Amount: ${amount}`);
        
        // Check if this is an NFT (amount = 1 and decimals = 0)
        try {
          const mintInfo = await connection.getAccountInfo(mint);
          if (mintInfo && mintInfo.data.length >= 82) {
            const decimals = mintInfo.data[44];
            const supply = mintInfo.data.readBigUInt64LE(36);
            if (decimals === 0 && supply === 1n) {
              console.log(`  → This is an NFT!`);
            }
          }
        } catch (e) {
          console.log(`  → Could not verify NFT status`);
        }
      }
    }
    
  } catch (error) {
    console.error('Error:', error);
  }
})();
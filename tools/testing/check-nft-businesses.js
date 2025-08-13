import { Connection, PublicKey } from '@solana/web3.js';

const connection = new Connection('https://api.devnet.solana.com');
const PROGRAM_ID = new PublicKey('HifXYhFJapXPeBgKKZu8gmdc7cZvfERJ9aEkchHxyBLS');
const USER_PUBKEY = new PublicKey('DfDkPhcm93C4JyXVRdz8M9B7cP8aeZKS9DNxS5cTxEmE');
const TOKEN_PROGRAM = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA');
const METADATA_PROGRAM = new PublicKey('metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s');

async function getNFTMetadata(mintAddress) {
  try {
    // Get metadata PDA
    const [metadataPda] = PublicKey.findProgramAddressSync(
      [
        Buffer.from('metadata'),
        METADATA_PROGRAM.toBuffer(),
        mintAddress.toBuffer(),
      ],
      METADATA_PROGRAM
    );
    
    const metadataInfo = await connection.getAccountInfo(metadataPda);
    if (!metadataInfo) return null;
    
    // Parse basic metadata (simplified)
    const name = metadataInfo.data.subarray(65, 97).toString().replace(/\0/g, '');
    const symbol = metadataInfo.data.subarray(97, 107).toString().replace(/\0/g, '');
    const uri = metadataInfo.data.subarray(107, 307).toString().replace(/\0/g, '');
    
    return { name, symbol, uri };
  } catch (error) {
    console.error('Error getting metadata:', error.message);
    return null;
  }
}

async function getBusinessDataFromNFT(mintAddress) {
  try {
    // Get business NFT PDA (based on your program structure)
    const [businessNftPda] = PublicKey.findProgramAddressSync(
      [Buffer.from('business_nft'), mintAddress.toBuffer()],
      PROGRAM_ID
    );
    
    const businessInfo = await connection.getAccountInfo(businessNftPda);
    if (!businessInfo) {
      console.log(`No business PDA found for NFT: ${mintAddress.toString()}`);
      return null;
    }
    
    console.log(`✅ Found business PDA for NFT: ${mintAddress.toString()}`);
    console.log(`  - PDA: ${businessNftPda.toString()}`);
    console.log(`  - Size: ${businessInfo.data.length} bytes`);
    
    // Parse business data (you'll need to adjust based on your struct)
    const data = businessInfo.data;
    return {
      pda: businessNftPda.toString(),
      dataSize: data.length,
      rawData: data.toString('hex').substring(0, 64) + '...'
    };
    
  } catch (error) {
    console.error('Error getting business data:', error.message);
    return null;
  }
}

(async () => {
  try {
    console.log('🎯 NFT-Based Business Ownership Check');
    console.log('User:', USER_PUBKEY.toString());
    console.log('');
    
    // Get all NFTs owned by user
    const tokenAccounts = await connection.getTokenAccountsByOwner(USER_PUBKEY, {
      programId: TOKEN_PROGRAM
    });
    
    console.log(`Found ${tokenAccounts.value.length} token accounts`);
    
    const nftBusinesses = [];
    
    for (const account of tokenAccounts.value) {
      const accountData = account.account.data;
      const mint = new PublicKey(accountData.subarray(0, 32));
      const amount = accountData.readBigUInt64LE(64);
      
      if (amount === 1n) { // Potential NFT
        console.log(`\\n🎨 Checking NFT: ${mint.toString()}`);
        
        // Check if it's really an NFT
        const mintInfo = await connection.getAccountInfo(mint);
        if (mintInfo && mintInfo.data.length >= 82) {
          const decimals = mintInfo.data[44];
          const supply = mintInfo.data.readBigUInt64LE(36);
          
          if (decimals === 0 && supply === 1n) {
            console.log('  ✅ Confirmed NFT (decimals=0, supply=1)');
            
            // Get metadata
            const metadata = await getNFTMetadata(mint);
            if (metadata) {
              console.log(`  📋 Name: "${metadata.name}"`);
              console.log(`  🏷️  Symbol: "${metadata.symbol}"`);
              if (metadata.uri) {
                console.log(`  🔗 URI: ${metadata.uri}`);
              }
              
              // Check if this is a business NFT from our program
              if (metadata.name.includes('Lucky') || metadata.name.includes('L0') || 
                  metadata.name.includes('L1') || metadata.name.includes('L2')) {
                console.log('  🏪 This looks like a business NFT!');
                
                // Try to get business data
                const businessData = await getBusinessDataFromNFT(mint);
                if (businessData) {
                  nftBusinesses.push({
                    mint: mint.toString(),
                    metadata,
                    businessData
                  });
                }
              }
            }
          }
        }
      }
    }
    
    console.log('\\n🏆 SUMMARY:');
    console.log(`Found ${nftBusinesses.length} business NFTs owned by user:`);
    
    nftBusinesses.forEach((business, i) => {
      console.log(`\\n${i + 1}. NFT: ${business.mint}`);
      console.log(`   Name: "${business.metadata.name}"`);
      console.log(`   Business PDA: ${business.businessData?.pda || 'Not found'}`);
    });
    
    if (nftBusinesses.length > 0) {
      console.log('\\n💡 SOLUTION:');
      console.log('The frontend should:');
      console.log('1. Scan user NFTs on page load');
      console.log('2. Identify business NFTs by name pattern or metadata');
      console.log('3. Load business data directly from blockchain');
      console.log('4. Display businesses immediately (no need to wait for indexer)');
    }
    
  } catch (error) {
    console.error('Error:', error);
  }
})();
import { Connection, PublicKey } from '@solana/web3.js';
import { WalletContextState } from '@solana/wallet-adapter-react';
import { AnchorProvider, Program } from '@coral-xyz/anchor';
import idl from '../solana_mafia.json';

const TOKEN_PROGRAM = new PublicKey('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA');
const METADATA_PROGRAM = new PublicKey('metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s');
// Program ID configuration from environment variables
const PROGRAM_ID_LOCALNET = process.env.NEXT_PUBLIC_PROGRAM_ID_LOCALNET || "3Ly6bEWRfKyVGwrRN27gHhBogo1K4HbZyk69KHW9AUx7";
const PROGRAM_ID_DEVNET = process.env.NEXT_PUBLIC_PROGRAM_ID_DEVNET || "6T6Dt16T5vUCDDAR7CP6nkbe3S1D5oiSSxMpQ4kiBgmN";
const NETWORK = process.env.NEXT_PUBLIC_SOLANA_NETWORK || "devnet";
const PROGRAM_ID_STRING = NETWORK === "localnet" ? PROGRAM_ID_LOCALNET : PROGRAM_ID_DEVNET;
const PROGRAM_ID = new PublicKey(PROGRAM_ID_STRING);

interface BusinessNFT {
  mint: string;
  name: string;
  symbol: string;
  uri: string;
  businessPda: string;
  businessData?: {
    pda: string;
    businessType: number;
    totalInvestedAmount: number;
    dailyRate: number;
    upgradeLevel: number;
    createdAt: number;
    serialNumber: number;
    isActive: boolean;
    slotIndex?: number;
    needsSync?: boolean;
  };
}

interface NFTMetadata {
  name: string;
  symbol: string;
  uri: string;
}

async function getNFTMetadata(connection: Connection, mintAddress: PublicKey): Promise<NFTMetadata | null> {
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
    
    // Parse basic metadata
    const name = metadataInfo.data.subarray(65, 97).toString().replace(/\0/g, '').trim();
    const symbol = metadataInfo.data.subarray(97, 107).toString().replace(/\0/g, '').trim();
    const uri = metadataInfo.data.subarray(107, 307).toString().replace(/\0/g, '').trim();
    
    return { name, symbol, uri };
  } catch (error) {
    console.error('Error getting NFT metadata:', error);
    return null;
  }
}

async function getBusinessDataFromNFT(connection: Connection, mintAddress: PublicKey): Promise<any> {
  try {
    // Get business NFT PDA
    const [businessNftPda] = PublicKey.findProgramAddressSync(
      [Buffer.from('business_nft'), mintAddress.toBuffer()],
      PROGRAM_ID
    );
    
    const businessInfo = await connection.getAccountInfo(businessNftPda);
    if (!businessInfo) return null;
    
    // Parse business data from BusinessNFT struct
    const data = businessInfo.data;
    
    // BusinessNFT struct layout (after 8-byte discriminator):
    // player: 32 bytes (offset 8)
    // business_type: 1 byte (offset 40) 
    // mint: 32 bytes (offset 41)
    // token_account: 32 bytes (offset 73)
    // total_invested_amount: 8 bytes (offset 105)
    // daily_rate: 2 bytes (offset 113)
    // upgrade_level: 1 byte (offset 115)
    // created_at: 8 bytes (offset 116)
    // serial_number: 8 bytes (offset 124)
    // is_burned: 1 byte (offset 132)
    // bump: 1 byte (offset 133)
    
    const businessType = data[40];
    const totalInvestedAmount = data.readBigUInt64LE(105);
    const dailyRate = data.readUInt16LE(113);
    const upgradeLevel = data[115];
    const createdAt = data.readBigInt64LE(116);
    const serialNumber = data.readBigUInt64LE(124);
    const isBurned = data[132] === 1;
    
    return {
      pda: businessNftPda.toString(),
      businessType,
      totalInvestedAmount: Number(totalInvestedAmount),
      dailyRate,
      upgradeLevel,
      createdAt: Number(createdAt),
      serialNumber: Number(serialNumber),
      isActive: !isBurned,
    };
    
  } catch (error) {
    console.error('Error getting business data from NFT:', error);
    return null;
  }
}

function isBusinessNFT(metadata: NFTMetadata): boolean {
  // Check if this is a business NFT based on name pattern
  const name = metadata.name.toLowerCase();
  return name.includes('lucky') || 
         name.includes('l0 ') || 
         name.includes('l1 ') || 
         name.includes('l2 ') ||
         name.includes('l3 ');
}

export async function getPlayerSlotData(connection: Connection, wallet: WalletContextState): Promise<Map<string, number>> {
  try {
    if (!wallet.publicKey) return new Map();
    
    // Create a minimal provider for reading data
    const provider = new AnchorProvider(connection, wallet as any, {});
    const program = new Program(idl as any, provider);
    
    // Get player PDA
    const [playerPda] = PublicKey.findProgramAddressSync(
      [Buffer.from('player'), wallet.publicKey.toBuffer()],
      PROGRAM_ID
    );
    
    console.log('Fetching player data from:', playerPda.toString());
    
    // Fetch player data using Anchor
    let playerData;
    try {
      playerData = await program.account.playerCompact.fetch(playerPda);
      console.log('✅ Player data fetched successfully:', playerData);
    } catch (fetchError) {
      console.log('❌ Player account not found or not accessible:', fetchError);
      return new Map(); // Return empty map if player doesn't exist yet
    }
    
    const slotMap = new Map<string, number>();
    
    // Parse business slots
    if (playerData.businessSlots && Array.isArray(playerData.businessSlots)) {
      playerData.businessSlots.forEach((slot: any, index: number) => {
        console.log(`Slot ${index}:`, {
          hasSlot: !!slot,
          hasBusiness: !!slot?.business,
          business: slot?.business
        });
        
        if (slot && slot.business && slot.business.nftMint) {
          try {
            // Business exists in this slot
            const mintString = slot.business.nftMint.toString();
            slotMap.set(mintString, index);
            console.log(`✅ Slot ${index} contains business with mint: ${mintString.slice(0, 8)}...`);
          } catch (err) {
            console.error(`Error parsing mint for slot ${index}:`, err, slot.business);
          }
        } else if (slot && slot.business) {
          console.log(`⚠️ Slot ${index} has business but no nftMint:`, slot.business);
        } else {
          console.log(`📭 Slot ${index} is empty`);
        }
      });
    } else {
      console.log('❌ No business slots found in player data');
    }
    
    return slotMap;
    
  } catch (error) {
    console.error('Error getting player slot data:', error);
    return new Map();
  }
}

// Check if NFT ownership matches business slot ownership
async function detectTransferredNFTs(connection: Connection, wallet: WalletContextState, businessNFTs: BusinessNFT[]): Promise<string[]> {
  const transferredNFTs: string[] = [];
  
  try {
    if (!wallet.publicKey || businessNFTs.length === 0) return transferredNFTs;
    
    // Get current player slot data from smart contract
    const slotMap = await getPlayerSlotData(connection, wallet);
    
    console.log('🔎 Transfer Detection Analysis:');
    console.log('- NFTs in wallet:', businessNFTs.length);
    console.log('- Businesses in slots:', slotMap.size);
    
    for (const nft of businessNFTs) {
      const isInSlot = slotMap.has(nft.mint);
      const slotIndex = slotMap.get(nft.mint);
      
      if (!isInSlot) {
        // NFT is in wallet but not assigned to any slot
        console.log(`🚨 Orphaned NFT detected: ${nft.mint.slice(0, 8)}... (not in any slot)`);
        console.log(`  - Name: ${nft.name}`);
        console.log(`  - Business Type: ${nft.businessData?.businessType}`);
        console.log(`  - This NFT needs ownership sync`);
        transferredNFTs.push(nft.mint);
      } else {
        console.log(`✅ NFT ${nft.mint.slice(0, 8)}... properly assigned to slot ${slotIndex}`);
      }
    }
    
    // Also check for ghost businesses (in slots but NFT not in wallet)
    const walletMints = new Set(businessNFTs.map(b => b.mint));
    for (const [mintAddress, slotIndex] of slotMap.entries()) {
      if (!walletMints.has(mintAddress)) {
        console.log(`👻 Ghost business detected in slot ${slotIndex}: ${mintAddress.slice(0, 8)}... (NFT not in wallet)`);
        console.log(`  - This business slot should be cleared during sync`);
      }
    }
    
    if (transferredNFTs.length > 0) {
      console.log(`🚨 Summary: ${transferredNFTs.length} NFTs need ownership sync`);
    } else {
      console.log('✅ All NFTs properly synchronized with business slots');
    }
    
  } catch (error) {
    console.error('Error detecting transferred NFTs:', error);
  }
  
  return transferredNFTs;
}

export async function loadBusinessNFTs(
  connection: Connection, 
  wallet: WalletContextState
): Promise<BusinessNFT[]> {
  if (!wallet.publicKey) {
    throw new Error('Wallet not connected');
  }

  console.log('🎯 Loading business NFTs for user:', wallet.publicKey.toString());

  try {
    // Get player slot data first
    const slotMap = await getPlayerSlotData(connection, wallet);
    console.log('Slot mapping:', slotMap);
    
    // Get all token accounts owned by user
    const tokenAccounts = await connection.getTokenAccountsByOwner(wallet.publicKey, {
      programId: TOKEN_PROGRAM
    });

    console.log(`Found ${tokenAccounts.value.length} token accounts`);

    const businessNFTs: BusinessNFT[] = [];

    for (const account of tokenAccounts.value) {
      const accountData = account.account.data;
      const mint = new PublicKey(accountData.subarray(0, 32));
      const amount = accountData.readBigUInt64LE(64);

      // Check if this is an NFT (amount = 1)
      if (amount === 1n) {
        // Verify it's really an NFT
        const mintInfo = await connection.getAccountInfo(mint);
        if (mintInfo && mintInfo.data.length >= 82) {
          const decimals = mintInfo.data[44];
          const supply = mintInfo.data.readBigUInt64LE(36);

          if (decimals === 0 && supply === 1n) {
            // Get metadata
            const metadata = await getNFTMetadata(connection, mint);
            if (metadata && isBusinessNFT(metadata)) {
              console.log(`✅ Found business NFT: ${metadata.name}`);

              // Get business data
              const businessData = await getBusinessDataFromNFT(connection, mint);
              
              // Add slot index from player data
              if (businessData && slotMap.has(mint.toString())) {
                businessData.slotIndex = slotMap.get(mint.toString());
                console.log(`NFT ${mint.toString().slice(0, 8)} is in slot ${businessData.slotIndex}`);
              }

              businessNFTs.push({
                mint: mint.toString(),
                name: metadata.name,
                symbol: metadata.symbol,
                uri: metadata.uri,
                businessPda: businessData?.pda || '',
                businessData
              });
            }
          }
        }
      }
    }

    // Detect potentially transferred NFTs that need ownership sync
    const transferredNFTs = await detectTransferredNFTs(connection, wallet, businessNFTs);
    
    if (transferredNFTs.length > 0) {
      console.log(`🚨 Detected ${transferredNFTs.length} transferred NFTs that need ownership sync`);
      console.log('  ℹ️ These NFTs are in your wallet but not assigned to business slots');
      console.log('  ℹ️ Auto-sync will handle this automatically on wallet connect');
      
      // Add transfer detection flag to NFT data
      transferredNFTs.forEach(transferredMint => {
        const nft = businessNFTs.find(b => b.mint === transferredMint);
        if (nft && nft.businessData) {
          nft.businessData.needsSync = true;
        }
      });
    }

    console.log(`🏆 Found ${businessNFTs.length} business NFTs`);
    return businessNFTs;

  } catch (error) {
    console.error('Error loading business NFTs:', error);
    throw error;
  }
}

// Hook for React components
export const useBusinessNFTs = () => {
  // You can implement this as a React hook that:
  // 1. Loads NFTs on wallet connection
  // 2. Caches results
  // 3. Provides loading states
  // 4. Refreshes on demand
};
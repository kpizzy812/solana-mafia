import { Connection, PublicKey } from '@solana/web3.js';
import { AnchorProvider, Program } from '@coral-xyz/anchor';
import fs from 'fs';

const connection = new Connection('https://api.devnet.solana.com');
const PROGRAM_ID = new PublicKey('HifXYhFJapXPeBgKKZu8gmdc7cZvfERJ9aEkchHxyBLS');
const USER_PUBKEY = new PublicKey('DfDkPhcm93C4JyXVRdz8M9B7cP8aeZKS9DNxS5cTxEmE');

// Load IDL
const idl = JSON.parse(fs.readFileSync('./target/idl/solana_mafia.json', 'utf8'));

// Create dummy wallet for read-only operations
const dummyWallet = {
  publicKey: USER_PUBKEY,
  signTransaction: async () => { throw new Error('Read-only'); },
  signAllTransactions: async () => { throw new Error('Read-only'); }
};

const provider = new AnchorProvider(connection, dummyWallet, {});
const program = new Program(idl, PROGRAM_ID, provider);

(async () => {
  try {
    // Get player PDA
    const [playerPda] = PublicKey.findProgramAddressSync(
      [Buffer.from('player'), USER_PUBKEY.toBuffer()],
      PROGRAM_ID
    );
    
    console.log('🔍 Детальная проверка аккаунта игрока...');
    console.log('User:', USER_PUBKEY.toString());
    console.log('Player PDA:', playerPda.toString());
    
    // Fetch player account
    const playerAccount = await program.account.player.fetch(playerPda);
    
    console.log('\n📊 Информация об игроке:');
    console.log('- Owner:', playerAccount.owner.toString());
    console.log('- Slots unlocked:', playerAccount.slotsUnlocked);
    console.log('- Total earnings:', playerAccount.totalEarnings.toString());
    console.log('- Earnings balance:', playerAccount.earningsBalance.toString());
    console.log('- Total invested:', playerAccount.totalInvested.toString());
    
    console.log('\n🏪 Слоты бизнесов:');
    for (let i = 0; i < playerAccount.slotsUnlocked; i++) {
      const business = playerAccount.businesses[i];
      if (business && business.businessType !== null && business.businessType !== undefined) {
        console.log(`Слот ${i}:`);
        console.log(`  - Type: ${business.businessType}`);
        console.log(`  - Level: ${business.level}`);
        console.log(`  - Cost: ${business.cost.toString()}`);
        console.log(`  - Earnings per hour: ${business.earningsPerHour.toString()}`);
        console.log(`  - Created at: ${new Date(business.createdAt.toNumber() * 1000)}`);
        console.log(`  - Is active: ${business.isActive}`);
        if (business.nftMint) {
          console.log(`  - NFT Mint: ${business.nftMint.toString()}`);
        }
      } else {
        console.log(`Слот ${i}: пустой`);
      }
    }
    
  } catch (error) {
    console.error('Error:', error);
  }
})();
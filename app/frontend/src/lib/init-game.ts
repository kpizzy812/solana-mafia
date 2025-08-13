import { Connection, PublicKey, SystemProgram } from '@solana/web3.js';
import { AnchorProvider, Program } from '@coral-xyz/anchor';
import { WalletContextState } from '@solana/wallet-adapter-react';
import { getProgram, getGameStatePDA, getGameConfigPDA, getTreasuryPDA, PROGRAM_ID } from './solana';

// Initialize game state and config (admin only)
export const initializeGame = async (wallet: WalletContextState) => {
  if (!wallet.publicKey) {
    throw new Error('Wallet not connected');
  }

  const program = getProgram(wallet);
  
  // Get PDAs
  const [gameState, gameStateBump] = getGameStatePDA();
  const [gameConfig, gameConfigBump] = getGameConfigPDA();
  const [treasury, treasuryBump] = getTreasuryPDA();

  console.log('Initializing game with PDAs:');
  console.log('GameState:', gameState.toString());
  console.log('GameConfig:', gameConfig.toString());
  console.log('Treasury:', treasury.toString());
  console.log('Authority:', wallet.publicKey.toString());

  try {
    // Check if accounts already exist
    try {
      await program.account.gameState.fetch(gameState);
      console.log('GameState already exists');
      return { success: true, message: 'Game already initialized' };
    } catch (error) {
      console.log('GameState does not exist, initializing...');
    }

    // Initialize game state
    const tx = await program.methods
      .initialize(wallet.publicKey) // pass treasury_wallet parameter
      .accounts({
        authority: wallet.publicKey,
        gameState: gameState,
        gameConfig: gameConfig,
        treasuryPda: treasury,
        systemProgram: SystemProgram.programId,
      })
      .rpc();

    console.log('Game initialized! Transaction:', tx);
    return { success: true, message: 'Game initialized successfully', tx };

  } catch (error) {
    console.error('Failed to initialize game:', error);
    throw error;
  }
};
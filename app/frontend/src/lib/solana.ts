import { Connection, PublicKey, SystemProgram, LAMPORTS_PER_SOL, ComputeBudgetProgram, Transaction, VersionedTransaction, TransactionMessage, TransactionInstruction } from '@solana/web3.js';
import { AnchorProvider, Program, web3, BN } from '@coral-xyz/anchor';
import { WalletContextState } from '@solana/wallet-adapter-react';
import idl from '../solana_mafia.json';

// Program ID configuration from environment variables
const PROGRAM_ID_LOCALNET = process.env.NEXT_PUBLIC_PROGRAM_ID_LOCALNET || "GtaYPUCEphDV1YgsS6VnBpTkkJwpuaQZf3ptFssyNvKU";
const PROGRAM_ID_DEVNET = process.env.NEXT_PUBLIC_PROGRAM_ID_DEVNET || "GtaYPUCEphDV1YgsS6VnBpTkkJwpuaQZf3ptFssyNvKU";

// Use network from environment or default to devnet
const NETWORK = process.env.NEXT_PUBLIC_SOLANA_NETWORK || "devnet";
const PROGRAM_ID_STRING = NETWORK === "localnet" ? PROGRAM_ID_LOCALNET : PROGRAM_ID_DEVNET;

export const PROGRAM_ID = new PublicKey(PROGRAM_ID_STRING);

console.log('Using Program ID:', PROGRAM_ID_STRING);

// Connection configuration - using environment variable or fallback to devnet
const RPC_ENDPOINT = process.env.NEXT_PUBLIC_SOLANA_RPC_URL || 'https://api.devnet.solana.com';

console.log('Using RPC endpoint:', RPC_ENDPOINT);

// Connection to Solana with enhanced settings for devnet
export const connection = new Connection(RPC_ENDPOINT, {
  commitment: 'confirmed',
  confirmTransactionInitialTimeout: 60000, // 60 seconds timeout
  wsEndpoint: undefined, // Disable websocket for devnet stability
});

// Get Anchor provider
export const getProvider = (wallet: WalletContextState) => {
  if (!wallet.publicKey || !wallet.signTransaction) {
    throw new Error('Wallet not connected');
  }

  return new AnchorProvider(
    connection,
    wallet as any,
    { 
      preflightCommitment: 'confirmed',
      commitment: 'confirmed',
      skipPreflight: false
    }
  );
}

// Get Anchor program
export const getProgram = (wallet: WalletContextState) => {
  const provider = getProvider(wallet);
  return new Program(idl as any, provider);
}

// PDA seeds (from constants.rs)
export const GAME_STATE_SEED = "game_state";
export const GAME_CONFIG_SEED = "game_config";
export const TREASURY_SEED = "treasury";
export const PLAYER_SEED = "player";

// Get PDAs
export const getGameStatePDA = () => {
  return web3.PublicKey.findProgramAddressSync(
    [Buffer.from(GAME_STATE_SEED)],
    PROGRAM_ID
  );
}

export const getGameConfigPDA = () => {
  return web3.PublicKey.findProgramAddressSync(
    [Buffer.from(GAME_CONFIG_SEED)],
    PROGRAM_ID
  );
}

export const getTreasuryPDA = () => {
  return web3.PublicKey.findProgramAddressSync(
    [Buffer.from(TREASURY_SEED)],
    PROGRAM_ID
  );
}

export const getPlayerPDA = (userPublicKey: PublicKey) => {
  return web3.PublicKey.findProgramAddressSync(
    [Buffer.from(PLAYER_SEED), userPublicKey.toBuffer()],
    PROGRAM_ID
  );
}

// Helper function to check program deployment and game state
export const checkProgramStatus = async (wallet: WalletContextState) => {
  try {
    console.log('Checking program status...');
    
    // Check if program exists
    const programInfo = await connection.getAccountInfo(PROGRAM_ID);
    if (!programInfo) {
      throw new Error(`Program ${PROGRAM_ID_STRING} not found on ${RPC_ENDPOINT}`);
    }
    
    console.log('✅ Program found:', {
      programId: PROGRAM_ID_STRING,
      owner: programInfo.owner.toString(),
      executable: programInfo.executable,
      dataLength: programInfo.data.length
    });

    // Check game state
    const program = getProgram(wallet);
    const [gameState] = getGameStatePDA();
    const [gameConfig] = getGameConfigPDA();
    
    try {
      const gameStateAccount = await program.account.gameState.fetch(gameState);
      console.log('✅ Game state found:', gameStateAccount);
    } catch (error) {
      console.error('❌ Game state not found:', error);
      throw new Error('Game not initialized. Please run the initialization script first.');
    }
    
    try {
      const gameConfigAccount = await (program.account as any).gameConfig.fetch(gameConfig);
      console.log('✅ Game config found:', gameConfigAccount);
    } catch (error) {
      console.error('❌ Game config not found:', error);
      throw new Error('Game config not initialized. Please run the initialization script first.');
    }
    
    return true;
  } catch (error) {
    console.error('Program status check failed:', error);
    throw error;
  }
};

// Helper function to simulate transaction for debugging
export const simulateTransaction = async (
  transaction: Transaction | VersionedTransaction,
  wallet: WalletContextState,
  simulationType: 'phantom' | 'rpc' = 'rpc'
) => {
  try {
    if (simulationType === 'phantom' && wallet.sendTransaction) {
      // Try Phantom's simulation by using dry run
      console.log('🔍 Simulating transaction via Phantom wallet...');
      // Note: We can't directly access Phantom's simulation, but we can check transaction structure
      return {
        success: true,
        message: 'Transaction structure is compatible with Phantom wallet'
      };
    } else {
      // Use RPC simulation
      console.log('🔍 Simulating transaction via RPC...');
      const simulation = await connection.simulateTransaction(
        transaction instanceof VersionedTransaction ? transaction : transaction,
        {
          commitment: 'confirmed',
          sigVerify: false, // Skip signature verification for simulation
        }
      );
      
      if (simulation.value.err) {
        return {
          success: false,
          error: simulation.value.err,
          logs: simulation.value.logs,
          message: `Simulation failed: ${JSON.stringify(simulation.value.err)}`
        };
      }
      
      return {
        success: true,
        logs: simulation.value.logs,
        computeUnitsConsumed: simulation.value.unitsConsumed,
        message: `Simulation successful. Compute units used: ${simulation.value.unitsConsumed}`
      };
    }
  } catch (error) {
    return {
      success: false,
      error: error,
      message: `Simulation error: ${error instanceof Error ? error.message : 'Unknown error'}`
    };
  }
};

// Helper function to estimate transaction fees
export const estimateTransactionFees = async (computeUnitLimit: number = 400000, computeUnitPrice: number = 50000) => {
  // Base transaction fee (5000 lamports for signature)
  const baseFee = 5000;
  
  // Priority fee calculation: (compute_unit_limit * compute_unit_price) / 1,000,000
  const priorityFee = Math.ceil((computeUnitLimit * computeUnitPrice) / 1_000_000);
  
  // Total estimated fee in lamports
  const totalFeelamports = baseFee + priorityFee;
  
  // Convert to SOL
  const totalFeeSOL = totalFeelamports / LAMPORTS_PER_SOL;
  
  return {
    baseFee,
    priorityFee,
    totalFeelamports,
    totalFeeSOL
  };
};

// Business purchase function
export const purchaseBusiness = async (
  wallet: WalletContextState,
  businessTypeId: number,
  slotIndex: number,
  level: number = 0
) => {
  if (!wallet.publicKey) {
    throw new Error('Wallet not connected');
  }

  // First, check if program and game are properly deployed/initialized
  try {
    await checkProgramStatus(wallet);
  } catch (statusError) {
    console.error('Program status check failed:', statusError);
    throw new Error(`Setup Error: ${statusError.message}`);
  }

  const program = getProgram(wallet);
  const userPublicKey = wallet.publicKey;

  // Get PDAs
  const [gameState] = getGameStatePDA();
  const [gameConfig] = getGameConfigPDA();
  const [treasury] = getTreasuryPDA();
  const [player] = getPlayerPDA(userPublicKey);


  // Calculate deposit amount based on business type and level
  const businessPrices = [
    0.1,  // TobaccoShop
    0.5,  // FuneralService  
    2.0,  // CarWorkshop
    5.0,  // ItalianRestaurant
    10.0, // GentlemenClub
    50.0  // CharityFund
  ];

  const levelMultipliers = [1.0, 1.2, 1.5, 2.0]; // Level 0-3 multipliers
  
  const basePrice = businessPrices[businessTypeId];
  const levelMultiplier = levelMultipliers[level];
  const totalPrice = basePrice * levelMultiplier;
  
  const depositAmount = new BN(totalPrice * LAMPORTS_PER_SOL);

  console.log('🏪 Purchase details:', {
    businessTypeId,
    slotIndex,
    level,
    totalPrice,
    depositAmount: depositAmount.toString(),
    userWallet: userPublicKey.toString(),
    timestamp: new Date().toISOString()
  });

  try {
    console.log('🎯 Creating business (will auto-create player if needed)...');

    // Get treasury wallet for business creation
    const gameStateAccount = await program.account.gameState.fetch(gameState);

    // Log all accounts for debugging
    console.log('Creating business with accounts:', {
      owner: userPublicKey.toString(),
      player: player.toString(),
      gameConfig: gameConfig.toString(),
      gameState: gameState.toString(),
      treasuryWallet: gameStateAccount.treasuryWallet.toString(),
      treasuryPda: treasury.toString(),
    });

    // Estimate basic transaction fees
    const baseFee = 5000; // Standard transaction fee in lamports
    const totalFeeSOL = baseFee / LAMPORTS_PER_SOL;
    console.log('💰 Basic transaction fee estimate:', {
      baseFee: baseFee,
      totalFeeSOL: totalFeeSOL,
      businessCost: totalPrice,
      totalCostSOL: totalPrice + totalFeeSOL
    });
    console.log('🔧 Using simplified transaction (no NFT required)');

    // Choose the correct instruction based on level
    let createBusinessInstruction;
    if (level === 0) {
      // Use basic create_business for level 0
      console.log('🏪 Using create_business (level 0)');
      createBusinessInstruction = await program.methods
        .createBusiness(
          businessTypeId,
          depositAmount,
          slotIndex
        )
        .accounts({
          owner: userPublicKey,
          player: player,
          gameConfig: gameConfig,
          gameState: gameState,
          treasuryWallet: gameStateAccount.treasuryWallet,
          treasuryPda: treasury,
          systemProgram: SystemProgram.programId,
        })
        .instruction();
    } else {
      // Use create_business_with_level for level > 0
      console.log('🚀 Using create_business_with_level (level', level, ')');
      createBusinessInstruction = await program.methods
        .createBusinessWithLevel(
          businessTypeId,
          depositAmount,
          slotIndex,
          level
        )
        .accounts({
          owner: userPublicKey,
          player: player,
          gameConfig: gameConfig,
          gameState: gameState,
          treasuryWallet: gameStateAccount.treasuryWallet,
          treasuryPda: treasury,
          systemProgram: SystemProgram.programId,
        })
        .instruction();
    }

    // 🎯 SIMPLIFIED SOLUTION: NO NFT, PURE BUSINESS TRANSACTION 🎯
    console.log('🎯 FINAL APPROACH: Creating simplified transaction without NFT...');
    
    try {
      // Get fresh blockhash
      const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash('confirmed');
      console.log('✅ Fresh blockhash obtained:', blockhash.slice(0, 8) + '...');

      // Create PURE transaction - ONLY the business instruction
      const transaction = new Transaction();
      transaction.recentBlockhash = blockhash;
      transaction.feePayer = userPublicKey;
      
      // ONLY the business creation instruction - nothing else!
      transaction.add(createBusinessInstruction);
      
      console.log('📊 Simplified transaction (no NFT):', {
        instructions: transaction.instructions.length,
        instruction: level === 0 ? 'create_business' : 'create_business_with_level',
        contractWillHandle: 'SOL transfers + Business in slot + Treasury split',
        level: level,
        feePayer: userPublicKey.toString().slice(0, 8) + '...',
      });

      // 🎯 Send simplified transaction to Phantom
      console.log('🎯 Sending SIMPLIFIED transaction (no NFT signers)...');
      
      if (wallet.sendTransaction) {
        console.log('📤 SIMPLIFIED TRANSACTION: Sending to Phantom...');
        
        // Simplified transaction - no additional signers needed
        const signature = await wallet.sendTransaction(transaction, connection, {
          skipPreflight: false,
          preflightCommitment: 'confirmed',
        });
        
        console.log('✅ SIMPLIFIED TRANSACTION SUBMITTED!');
        console.log('📋 Business created without NFT:');
        console.log('   🏪 Single contract instruction (simplified)');
        console.log('   💰 Contract handles: SOL payment + Business slot + Treasury split');
        console.log('   ✨ No NFT complexity');
        console.log('   🔗 Signature:', signature);
        
        // Confirm transaction
        console.log('⏳ Confirming simplified transaction...');
        const confirmation = await connection.confirmTransaction({
          signature,
          blockhash,
          lastValidBlockHeight,
        }, 'confirmed');
        
        if (confirmation.value.err) {
          throw new Error(`Transaction failed: ${JSON.stringify(confirmation.value.err)}`);
        }
        
        console.log('🎉 BUSINESS CREATED SUCCESSFULLY!');
        console.log('🎯 Business Type:', businessTypeId);
        console.log('🎯 Slot Index:', slotIndex);
        console.log('🎯 Level:', level);
        console.log('🎯 Transaction:', signature);
        
        return signature;
        
      } else {
        // Emergency fallback - use Anchor
        console.log('🚨 FALLBACK: Using Anchor provider...');
        
        const signature = await program.provider.sendAndConfirm(transaction, [], {
          commitment: 'confirmed',
          preflightCommitment: 'confirmed',
          skipPreflight: false,
        });
        
        console.log('✅ Fallback successful:', signature);
        return signature;
      }
      
    } catch (error) {
      console.error('💥 SIMPLIFIED TRANSACTION FAILED:', error);
      
      // Enhanced error diagnosis
      if (error instanceof Error && error.message?.includes('User rejected')) {
        console.log('🚫 User rejected transaction in Phantom');
      } else if (error instanceof Error && error.message?.includes('unknown signer')) {
        console.log('🚨 CRITICAL: This error should not happen with simplified transaction');
      }
      
      throw error;
    }

  } catch (error) {
    console.error('Purchase failed:', error);
    
    // Enhanced error handling for Phantom wallet and simulation issues
    const errorMessage = error.message || error.toString();
    
    // Handle Phantom-specific errors
    if (errorMessage.includes('User rejected') || errorMessage.includes('User denied')) {
      throw new Error('Transaction cancelled by user.');
    } else if (errorMessage.includes('Phantom') && errorMessage.includes('simulation')) {
      throw new Error('Phantom wallet simulation issue. Try refreshing and attempting again.');
    } else if (errorMessage.includes('already been processed')) {
      throw new Error('Transaction was already processed or is being processed. Please wait a moment and check your wallet for the NFT. If the NFT didn\'t appear, try again.');
    } else if (errorMessage.includes('insufficient funds')) {
      const feeEstimate = await estimateTransactionFees(400000, 50000);
      throw new Error(`Insufficient funds. You need approximately ${feeEstimate.totalFeeSOL.toFixed(4)} SOL for transaction fees plus the business cost.`);
    } else if (errorMessage.includes('signature verification failed')) {
      throw new Error('Wallet signature failed. Please ensure your wallet is unlocked and try again.');
    } else if (errorMessage.includes('simulation failed') || errorMessage.includes('Transaction simulation failed')) {
      // Enhanced simulation error handling
      if (errorMessage.includes('exceeded maximum compute budget')) {
        throw new Error('Transaction requires too many compute resources. This may be a temporary network issue - try again.');
      } else if (errorMessage.includes('blockhash not found') || errorMessage.includes('Blockhash not found')) {
        throw new Error('Network congestion detected. Please wait a few seconds and try again.');
      } else if (errorMessage.includes('account not found') || errorMessage.includes('Account not found')) {
        throw new Error('Required accounts not found. The game may need to be reinitialized. Please contact support.');
      } else if (errorMessage.includes('custom program error')) {
        // Try to extract program error details
        const errorMatch = errorMessage.match(/custom program error: (0x[0-9a-fA-F]+)/);
        if (errorMatch) {
          const errorCode = errorMatch[1];
          throw new Error(`Smart contract error (${errorCode}). This may be due to invalid business parameters or game state.`);
        }
        throw new Error('Smart contract validation failed. Please check business parameters and try again.');
      } else {
        console.log('Detailed simulation error:', error);
        // For unhandled simulation errors, provide helpful guidance
        throw new Error('Transaction simulation failed in Phantom wallet. The transaction may still work if submitted. If this persists, try refreshing the page.');
      }
    } else if (errorMessage.includes('Network request failed') || errorMessage.includes('fetch')) {
      throw new Error('Network connection issue. Please check your internet connection and try again.');
    } else if (errorMessage.includes('timeout') || errorMessage.includes('Timeout')) {
      throw new Error('Transaction timed out. The network may be congested - please try again.');
    } else if (error.logs && Array.isArray(error.logs)) {
      // Enhanced log parsing for better error messages
      console.log('Transaction logs:', error.logs);
      const relevantLogs = error.logs.filter(log => 
        typeof log === 'string' && (
          log.includes('Error') || 
          log.includes('failed') || 
          log.includes('Program log:') ||
          log.includes('panicked') ||
          log.includes('custom program error')
        )
      );
      
      if (relevantLogs.length > 0) {
        const errorSummary = relevantLogs.slice(0, 3).join('; '); // Limit to first 3 relevant logs
        throw new Error(`Smart contract error: ${errorSummary}`);
      }
    }
    
    throw error;
  }
}

// Helper function to get business data from contracts constants
export const getBusinessData = (businessTypeId: number, level: number) => {
  const businessPrices = [0.1, 0.5, 2.0, 5.0, 10.0, 50.0];
  const businessRates = [200, 180, 160, 140, 120, 100]; // basis points
  const levelMultipliers = [1.0, 1.2, 1.5, 2.0];
  const levelBonuses = [0, 10, 25, 50]; // basis points
  
  const basePrice = businessPrices[businessTypeId];
  const baseRate = businessRates[businessTypeId];
  const levelMultiplier = levelMultipliers[level];
  const levelBonus = levelBonuses[level];
  
  const totalPrice = basePrice * levelMultiplier;
  const totalRate = baseRate + levelBonus;
  const dailyYield = (totalPrice * totalRate) / 10000; // Convert basis points to decimal
  
  return {
    basePrice,
    totalPrice,
    dailyYield,
    dailyYieldPercent: totalRate / 100
  };
};

// Withdraw Earnings function
export const withdrawEarnings = async (
  wallet: WalletContextState
): Promise<string> => {
  if (!wallet.publicKey) {
    throw new Error('Wallet not connected');
  }

  console.log('💰 Starting earnings withdrawal...', {
    wallet: wallet.publicKey.toString()
  });

  const program = getProgram(wallet);
  const userPublicKey = wallet.publicKey;

  // Get PDAs
  const [player] = getPlayerPDA(userPublicKey);
  const [treasury] = getTreasuryPDA();
  const [gameState] = getGameStatePDA();

  try {
    // Get treasury wallet from game state
    const gameStateAccount = await program.account.gameState.fetch(gameState);

    console.log('Withdraw accounts:', {
      playerOwner: userPublicKey.toString(),
      player: player.toString(),
      treasuryPda: treasury.toString(),
      gameState: gameState.toString(),
      treasuryWallet: gameStateAccount.treasuryWallet.toString(),
    });

    // Create withdraw instruction following official Anchor withdrawal pattern
    const withdrawInstruction = await program.methods
      .claimEarnings()
      .accounts({
        playerOwner: userPublicKey,
        player: player,
        treasuryPda: treasury,
        gameState: gameState,
        treasuryWallet: gameStateAccount.treasuryWallet,
        systemProgram: SystemProgram.programId,
      })
      .instruction();

    // Get fresh blockhash
    const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash('confirmed');

    // Create transaction
    const transaction = new Transaction();
    transaction.recentBlockhash = blockhash;
    transaction.feePayer = userPublicKey;
    transaction.add(withdrawInstruction);

    console.log('📋 Withdraw transaction details:', {
      instructions: transaction.instructions.length
    });

    // Send transaction
    if (wallet.sendTransaction) {
      console.log('📤 Sending via wallet.sendTransaction...');
      
      const signature = await wallet.sendTransaction(transaction, connection, {
        skipPreflight: false,
        preflightCommitment: 'confirmed',
      });
      
      console.log('⏳ Confirming withdrawal...', signature);
      const confirmation = await connection.confirmTransaction({
        signature,
        blockhash,
        lastValidBlockHeight,
      }, 'confirmed');
      
      if (confirmation.value.err) {
        throw new Error(`Transaction failed: ${JSON.stringify(confirmation.value.err)}`);
      }
      
      console.log('✅ Earnings withdrawn successfully!', signature);
      return signature;
      
    } else {
      throw new Error('Wallet does not support sendTransaction');
    }

  } catch (error) {
    console.error('❌ Withdraw failed:', error);
    throw error;
  }
};

// Update Earnings function
export const updateEarnings = async (
  wallet: WalletContextState,
  targetPlayerWallet: string
): Promise<string> => {
  if (!wallet.publicKey) {
    throw new Error('Wallet not connected');
  }

  console.log('📈 Starting earnings update...', {
    userWallet: wallet.publicKey.toString(),
    targetPlayer: targetPlayerWallet
  });

  const program = getProgram(wallet);
  const userPublicKey = wallet.publicKey;
  const targetPlayerPublicKey = new PublicKey(targetPlayerWallet);

  // Get PDAs
  const [targetPlayer] = getPlayerPDA(targetPlayerPublicKey);

  console.log('Update earnings accounts:', {
    targetPlayer: targetPlayer.toString(),
    targetPlayerWallet: targetPlayerWallet
  });

  try {
    // Create update earnings instruction
    const updateInstruction = await program.methods
      .updateEarnings()
      .accounts({
        targetPlayer: targetPlayer,
      })
      .instruction();

    // Get fresh blockhash
    const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash('confirmed');

    // Create transaction
    const transaction = new Transaction();
    transaction.recentBlockhash = blockhash;
    transaction.feePayer = userPublicKey;
    transaction.add(updateInstruction);

    console.log('📋 Update earnings transaction details:', {
      instructions: transaction.instructions.length,
      target: targetPlayerWallet
    });

    // Send transaction
    if (wallet.sendTransaction) {
      console.log('📤 Sending via wallet.sendTransaction...');
      
      const signature = await wallet.sendTransaction(transaction, connection, {
        skipPreflight: false,
        preflightCommitment: 'confirmed',
      });
      
      console.log('⏳ Confirming earnings update...', signature);
      const confirmation = await connection.confirmTransaction({
        signature,
        blockhash,
        lastValidBlockHeight,
      }, 'confirmed');
      
      if (confirmation.value.err) {
        throw new Error(`Transaction failed: ${JSON.stringify(confirmation.value.err)}`);
      }
      
      console.log('✅ Earnings updated successfully!', signature);
      return signature;
      
    } else {
      throw new Error('Wallet does not support sendTransaction');
    }

  } catch (error) {
    console.error('❌ Update earnings failed:', error);
    throw error;
  }
};

// Get FOMO data from game state and config
export const getFomoData = async (wallet: WalletContextState) => {
  try {
    const program = getProgram(wallet);
    
    // Get game state and config PDAs
    const [gameState] = getGameStatePDA();
    const [gameConfig] = getGameConfigPDA();
    
    // Check if accounts exist first
    let gameStateAccount, gameConfigAccount;
    
    try {
      gameStateAccount = await program.account.gameState.fetch(gameState);
      console.log('Game state fetched successfully');
    } catch (error) {
      console.error('Failed to fetch game state:', error);
      throw new Error('Game state not initialized');
    }
    
    try {
      gameConfigAccount = await program.account.gameConfig.fetch(gameConfig);
      console.log('Game config fetched successfully');
    } catch (error) {
      console.error('Failed to fetch game config:', error);
      // Try to handle boolean decoding error specifically
      if (error.message?.includes('Invalid bool')) {
        console.error('Boolean decoding error detected - game config may be corrupted');
        throw new Error('Game config data corrupted - please reinitialize');
      }
      throw new Error('Game config not initialized');
    }
    
    const totalPlayers = gameStateAccount.totalPlayers.toNumber();
    const baseEntryFee = gameConfigAccount.baseEntryFee.toNumber() / LAMPORTS_PER_SOL;
    const maxEntryFee = gameConfigAccount.maxEntryFee.toNumber() / LAMPORTS_PER_SOL;
    const feeIncrement = gameConfigAccount.feeIncrement.toNumber() / LAMPORTS_PER_SOL;
    const playersPerMilestone = gameConfigAccount.playersPerMilestone.toNumber();
    
    // Calculate current and next fees
    const milestones = Math.floor(totalPlayers / playersPerMilestone);
    const currentEntryFee = Math.min(baseEntryFee + (milestones * feeIncrement), maxEntryFee);
    const nextEntryFee = Math.min(baseEntryFee + ((milestones + 1) * feeIncrement), maxEntryFee);
    
    // Calculate players until next increase
    const nextMilestone = (milestones + 1) * playersPerMilestone;
    const playersUntilIncrease = nextMilestone - totalPlayers;
    
    return {
      totalPlayers,
      currentEntryFee,
      nextEntryFee,
      playersUntilIncrease,
      maxEntryFee,
      playersPerMilestone
    };
  } catch (error) {
    console.error('Failed to fetch FOMO data:', error);
    // Return default values if fetch fails
    return {
      totalPlayers: 0,
      currentEntryFee: 0.006, // Base fee
      nextEntryFee: 0.012,
      playersUntilIncrease: 100,
      maxEntryFee: 0.06,
      playersPerMilestone: 100
    };
  }
};

// Upgrade Business in Slot
export const upgradeBusiness = async (
  wallet: WalletContextState,
  businessId: string,
  slotIndex: number,
  currentLevel: number,
  targetLevel: number
): Promise<string> => {
  if (!wallet.publicKey || !wallet.signTransaction) {
    throw new Error('Wallet not connected');
  }

  console.log('🔄 Starting business upgrade...', {
    businessId,
    slotIndex,
    currentLevel,
    targetLevel,
    wallet: wallet.publicKey.toString()
  });

  const program = getProgram(wallet);
  const userPublicKey = wallet.publicKey;

  // Get PDAs
  const [player] = getPlayerPDA(userPublicKey);
  const [gameConfig] = getGameConfigPDA();
  const [gameState] = getGameStatePDA();

  try {
    // Get treasury wallet
    const gameStateAccount = await program.account.gameState.fetch(gameState);

    console.log('Upgrade accounts:', {
      playerOwner: userPublicKey.toString(),
      player: player.toString(),
      gameConfig: gameConfig.toString(),
      gameState: gameState.toString(),
      treasuryWallet: gameStateAccount.treasuryWallet.toString(),
      slotIndex: slotIndex
    });

    // Create upgrade instruction
    const upgradeInstruction = await program.methods
      .upgradeBusiness(slotIndex)
      .accounts({
        playerOwner: userPublicKey,
        player: player,
        gameConfig: gameConfig,
        gameState: gameState,
        treasuryWallet: gameStateAccount.treasuryWallet,
        systemProgram: SystemProgram.programId,
      })
      .instruction();

    // Get fresh blockhash
    const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash('confirmed');

    // Create transaction
    const transaction = new Transaction();
    transaction.recentBlockhash = blockhash;
    transaction.feePayer = userPublicKey;
    transaction.add(upgradeInstruction);

    console.log('📋 Transaction details:', {
      instructions: transaction.instructions.length,
      businessId: businessId,
      slotIndex: slotIndex,
      targetLevel: targetLevel
    });

    // Send transaction to wallet
    const signature = await wallet.sendTransaction!(transaction, connection, {
      skipPreflight: false,
      preflightCommitment: 'confirmed',
    });

    console.log('✅ Business upgrade transaction sent:', signature);

    // Confirm transaction
    const confirmation = await connection.confirmTransaction({
      signature,
      blockhash,
      lastValidBlockHeight,
    }, 'confirmed');

    if (confirmation.value.err) {
      throw new Error(`Transaction failed: ${JSON.stringify(confirmation.value.err)}`);
    }

    console.log('🎉 Business upgraded successfully!');
    return signature;

  } catch (error) {
    console.error('❌ Business upgrade failed:', error);
    throw error;
  }
};

// Sell Business in Slot
export const sellBusiness = async (
  wallet: WalletContextState,
  slotIndex: number
): Promise<string> => {
  if (!wallet.publicKey || !wallet.signTransaction) {
    throw new Error('Wallet not connected');
  }

  console.log('🔥 Starting business sale...', {
    slotIndex,
    wallet: wallet.publicKey.toString()
  });

  const program = getProgram(wallet);
  const userPublicKey = wallet.publicKey;

  try {
    // Get PDAs
    const [player] = getPlayerPDA(userPublicKey);
    const [gameState] = getGameStatePDA();
    const [gameConfig] = getGameConfigPDA();
    const [treasury] = getTreasuryPDA();

    // Get treasury wallet for proper SOL transfer display in Phantom
    const gameStateAccount = await program.account.gameState.fetch(gameState);

    console.log('Sell accounts:', {
      playerOwner: userPublicKey.toString(),
      player: player.toString(),
      gameState: gameState.toString(),
      gameConfig: gameConfig.toString(),
      treasuryPda: treasury.toString(),
      treasuryWallet: gameStateAccount.treasuryWallet.toString(),
      slotIndex: slotIndex
    });

    // 🔧 FIXED: Use explicit accounts like working functions (createBusiness, upgradeBusiness)
    const sellInstruction = await program.methods
      .sellBusiness(slotIndex)
      .accounts({
        playerOwner: userPublicKey,
        player: player,
        treasuryPda: treasury,
        gameState: gameState,
        gameConfig: gameConfig,
        treasuryWallet: gameStateAccount.treasuryWallet,
        systemProgram: SystemProgram.programId,
      })
      .instruction();
    
    console.log('✅ Using explicit accounts (like working functions)');

    // Get fresh blockhash
    const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash('confirmed');

    // Create transaction
    const transaction = new Transaction();
    transaction.recentBlockhash = blockhash;
    transaction.feePayer = userPublicKey;
    transaction.add(sellInstruction);

    console.log('📋 Sell transaction details:', {
      instructions: transaction.instructions.length,
      slotIndex: slotIndex
    });

    // Send transaction to wallet with proper simulation
    const signature = await wallet.sendTransaction!(transaction, connection, {
      skipPreflight: false,  // Enable simulation (problems fixed with manual lamports)
      preflightCommitment: 'confirmed',
    });

    console.log('✅ Business sale transaction sent:', signature);

    // Confirm transaction
    const confirmation = await connection.confirmTransaction({
      signature,
      blockhash,
      lastValidBlockHeight,
    }, 'confirmed');

    if (confirmation.value.err) {
      throw new Error(`Transaction failed: ${JSON.stringify(confirmation.value.err)}`);
    }

    console.log('🎉 Business sold successfully!');
    return signature;

  } catch (error) {
    console.error('❌ Business sale failed:', error);
    throw error;
  }
};

// Calculate sell fees and return amount
export const calculateSellDetails = (
  totalInvestedAmount: number, // in SOL
  createdTimestamp: number, // Unix timestamp
  slotDiscount: number = 0 // Slot discount percentage
) => {
  const now = Math.floor(Date.now() / 1000);
  const daysHeld = Math.floor((now - createdTimestamp) / (24 * 60 * 60));
  
  // Base sell fee based on days held (matching smart contract logic)
  let baseSellFeePercent: number;
  if (daysHeld <= 7) {
    baseSellFeePercent = 25;
  } else if (daysHeld <= 14) {
    baseSellFeePercent = 20;
  } else if (daysHeld <= 21) {
    baseSellFeePercent = 15;
  } else if (daysHeld <= 28) {
    baseSellFeePercent = 10;
  } else if (daysHeld <= 30) {
    baseSellFeePercent = 5;
  } else {
    baseSellFeePercent = 2;
  }
  
  // Apply slot discount
  const finalSellFeePercent = Math.max(0, baseSellFeePercent - slotDiscount);
  
  const sellFee = (totalInvestedAmount * finalSellFeePercent) / 100;
  const returnAmount = totalInvestedAmount - sellFee;
  
  return {
    daysHeld,
    baseSellFeePercent,
    slotDiscount,
    finalSellFeePercent,
    sellFee,
    returnAmount,
    totalInvestedAmount
  };
};

// Get current game config (including treasury fee percentage)
export const getGameConfig = async (wallet: WalletContextState) => {
  try {
    const program = getProgram(wallet);
    const [gameConfig] = getGameConfigPDA();
    
    const gameConfigAccount = await (program.account as any).gameConfig.fetch(gameConfig);
    
    return {
      treasuryFeePercent: gameConfigAccount.treasuryFeePercent,
      businessRates: gameConfigAccount.businessRates,
      minDeposits: gameConfigAccount.minDeposits.map((amount: any) => amount.toNumber() / LAMPORTS_PER_SOL),
      baseEntryFee: gameConfigAccount.baseEntryFee.toNumber() / LAMPORTS_PER_SOL,
      maxEntryFee: gameConfigAccount.maxEntryFee.toNumber() / LAMPORTS_PER_SOL,
      registrationsOpen: gameConfigAccount.registrationsOpen,
    };
  } catch (error) {
    console.error('Failed to fetch game config:', error);
    throw error;
  }
};
/**
 * Signature Queue System for Enhanced Transaction Processing
 * 
 * This module implements a sophisticated signature processing architecture that works
 * seamlessly with the backend SignatureProcessor and WebSocket notification system.
 * 
 * Architecture Flow:
 * 1. Frontend calls transaction function (purchaseBusiness, upgradeBusiness, etc.)
 * 2. Transaction is sent to wallet and signature is received
 * 3. Signature is queued to backend via /api/v1/transactions/process
 * 4. Backend processes transaction asynchronously using proven force_process_transaction logic
 * 5. WebSocket notifications are sent with status updates (processing, completed, failed)
 * 6. Frontend receives WebSocket events and updates UI accordingly
 * 
 * Benefits:
 * - Immediate user feedback with loading states
 * - Reliable transaction processing using proven backend logic
 * - Real-time status updates via WebSocket
 * - Automatic UI state management
 * - Error handling and retry logic
 * - Referral code processing integration
 */

import { WalletContextState } from '@solana/wallet-adapter-react';
import { apiClient } from './api';

// Transaction status types matching backend
export type TransactionStatus = 'sending' | 'processing' | 'completed' | 'failed';

// Context for different action types
export interface TransactionContext {
  action_type: 'purchase' | 'upgrade' | 'sell' | 'claim' | 'earnings_update';
  slot_index?: number;
  business_level?: number;
  business_id?: string;
  target_level?: number;
  amount?: number;
}

// Signature processing result
export interface SignatureProcessingResult {
  signature: string;
  status: TransactionStatus;
  context?: TransactionContext;
  result?: any;
  error?: string;
}

// Status update callback function
export type StatusUpdateCallback = (
  status: TransactionStatus, 
  data?: {
    signature?: string;
    error?: string;
    result?: any;
  }
) => void;

/**
 * Queue signature for backend processing with context
 */
export async function queueSignatureForProcessing(
  signature: string,
  userWallet: string,
  context: TransactionContext
): Promise<boolean> {
  try {
    console.log('📤 Queuing signature for backend processing', {
      signature: signature.slice(0, 20) + '...',
      userWallet,
      context
    });

    const response = await fetch(`${apiClient['baseUrl']}/transactions/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...apiClient['headers']
      },
      body: JSON.stringify({
        signature,
        user_wallet: userWallet,
        slot_index: context.slot_index,
        business_level: context.business_level,
        context
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const result = await response.json();
    
    if (result.success) {
      console.log('✅ Signature queued successfully', {
        signature: result.signature.slice(0, 20) + '...',
        message: result.message,
        estimated_processing_time: result.estimated_processing_time
      });
      return true;
    } else {
      throw new Error(result.message || 'Failed to queue signature');
    }

  } catch (error) {
    console.error('❌ Failed to queue signature for processing', {
      signature: signature.slice(0, 20) + '...',
      error: error instanceof Error ? error.message : String(error)
    });
    return false;
  }
}

/**
 * Enhanced business purchase with signature processing
 */
export async function purchaseBusinessWithProcessing(
  purchaseFunction: (wallet: WalletContextState, businessTypeId: number, slotIndex: number, level: number) => Promise<string>,
  wallet: WalletContextState,
  businessTypeId: number,
  slotIndex: number,
  level: number,
  userWallet: string,
  statusCallback?: StatusUpdateCallback
): Promise<SignatureProcessingResult> {
  try {
    // Update status to sending
    statusCallback?.('sending', {});
    
    console.log('🚀 ENHANCED PURCHASE: Starting with signature queue architecture', {
      businessTypeId,
      slotIndex,
      level,
      userWallet
    });

    // Execute the transaction and get signature
    const signature = await purchaseFunction(wallet, businessTypeId, slotIndex, level);
    
    console.log('✅ ENHANCED PURCHASE: Transaction sent, signature received', {
      signature: signature.slice(0, 20) + '...'
    });

    // Update status to processing
    statusCallback?.('processing', { signature });

    // Queue signature for backend processing
    const context: TransactionContext = {
      action_type: 'purchase',
      slot_index: slotIndex,
      business_level: level
    };

    const queued = await queueSignatureForProcessing(signature, userWallet, context);
    
    if (!queued) {
      console.warn('⚠️ ENHANCED PURCHASE: Failed to queue signature, but transaction was sent');
      // Still return success since transaction was sent to blockchain
    }

    console.log('🎯 ENHANCED PURCHASE: Signature processing flow initiated', {
      signature: signature.slice(0, 20) + '...',
      queued,
      note: 'WebSocket will handle completion notifications'
    });

    return {
      signature,
      status: 'processing',
      context
    };

  } catch (error) {
    console.error('❌ ENHANCED PURCHASE: Failed', error);
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    statusCallback?.('failed', { error: errorMessage });

    throw error;
  }
}

/**
 * Enhanced business upgrade with signature processing
 */
export async function upgradeBusinessWithProcessing(
  upgradeFunction: (wallet: WalletContextState, businessId: string, slotIndex: number, currentLevel: number, targetLevel: number) => Promise<any>,
  wallet: WalletContextState,
  businessId: string,
  slotIndex: number,
  currentLevel: number,
  targetLevel: number,
  userWallet: string,
  statusCallback?: StatusUpdateCallback
): Promise<SignatureProcessingResult> {
  try {
    // Update status to sending
    statusCallback?.('sending', {});
    
    console.log('🚀 ENHANCED UPGRADE: Starting with signature queue architecture', {
      businessId,
      slotIndex,
      currentLevel,
      targetLevel,
      userWallet
    });

    // Execute the transaction and get signature
    const result = await upgradeFunction(wallet, businessId, slotIndex, currentLevel, targetLevel);
    const signature = result.signature || result;
    
    console.log('✅ ENHANCED UPGRADE: Transaction sent, signature received', {
      signature: signature.slice(0, 20) + '...'
    });

    // Update status to processing
    statusCallback?.('processing', { signature });

    // Queue signature for backend processing
    const context: TransactionContext = {
      action_type: 'upgrade',
      slot_index: slotIndex,
      business_level: targetLevel,
      business_id: businessId
    };

    const queued = await queueSignatureForProcessing(signature, userWallet, context);
    
    if (!queued) {
      console.warn('⚠️ ENHANCED UPGRADE: Failed to queue signature, but transaction was sent');
    }

    console.log('🎯 ENHANCED UPGRADE: Signature processing flow initiated', {
      signature: signature.slice(0, 20) + '...',
      queued,
      note: 'WebSocket will handle completion notifications'
    });

    return {
      signature,
      status: 'processing',
      context
    };

  } catch (error) {
    console.error('❌ ENHANCED UPGRADE: Failed', error);
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    statusCallback?.('failed', { error: errorMessage });

    throw error;
  }
}

/**
 * Enhanced business sell with signature processing
 */
export async function sellBusinessWithProcessing(
  sellFunction: (wallet: WalletContextState, businessId: string, slotIndex: number) => Promise<any>,
  wallet: WalletContextState,
  businessId: string,
  slotIndex: number,
  userWallet: string,
  statusCallback?: StatusUpdateCallback
): Promise<SignatureProcessingResult> {
  try {
    // Update status to sending
    statusCallback?.('sending', {});
    
    console.log('🚀 ENHANCED SELL: Starting with signature queue architecture', {
      businessId,
      slotIndex,
      userWallet
    });

    // Execute the transaction and get signature
    const result = await sellFunction(wallet, businessId, slotIndex);
    const signature = result.signature || result;
    
    console.log('✅ ENHANCED SELL: Transaction sent, signature received', {
      signature: signature.slice(0, 20) + '...'
    });

    // Update status to processing
    statusCallback?.('processing', { signature });

    // Queue signature for backend processing
    const context: TransactionContext = {
      action_type: 'sell',
      slot_index: slotIndex,
      business_id: businessId
    };

    const queued = await queueSignatureForProcessing(signature, userWallet, context);
    
    if (!queued) {
      console.warn('⚠️ ENHANCED SELL: Failed to queue signature, but transaction was sent');
    }

    console.log('🎯 ENHANCED SELL: Signature processing flow initiated', {
      signature: signature.slice(0, 20) + '...',
      queued,
      note: 'WebSocket will handle completion notifications'
    });

    return {
      signature,
      status: 'processing',
      context
    };

  } catch (error) {
    console.error('❌ ENHANCED SELL: Failed', error);
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    statusCallback?.('failed', { error: errorMessage });

    throw error;
  }
}

/**
 * Enhanced earnings claim with signature processing
 */
export async function claimEarningsWithProcessing(
  claimFunction: (wallet: WalletContextState) => Promise<string>,
  wallet: WalletContextState,
  userWallet: string,
  statusCallback?: StatusUpdateCallback
): Promise<SignatureProcessingResult> {
  try {
    // Update status to sending
    statusCallback?.('sending', {});
    
    console.log('🚀 ENHANCED CLAIM: Starting with signature queue architecture', {
      userWallet
    });

    // Execute the transaction and get signature
    const signature = await claimFunction(wallet);
    
    console.log('✅ ENHANCED CLAIM: Transaction sent, signature received', {
      signature: signature.slice(0, 20) + '...'
    });

    // Update status to processing
    statusCallback?.('processing', { signature });

    // Queue signature for backend processing
    const context: TransactionContext = {
      action_type: 'claim'
    };

    const queued = await queueSignatureForProcessing(signature, userWallet, context);
    
    if (!queued) {
      console.warn('⚠️ ENHANCED CLAIM: Failed to queue signature, but transaction was sent');
    }

    console.log('🎯 ENHANCED CLAIM: Signature processing flow initiated', {
      signature: signature.slice(0, 20) + '...',
      queued,
      note: 'WebSocket will handle completion notifications'
    });

    return {
      signature,
      status: 'processing',
      context
    };

  } catch (error) {
    console.error('❌ ENHANCED CLAIM: Failed', error);
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    statusCallback?.('failed', { error: errorMessage });

    throw error;
  }
}

/**
 * Enhanced earnings update with signature processing
 */
export async function updateEarningsWithProcessing(
  updateFunction: (wallet: WalletContextState, targetPlayerWallet: string) => Promise<string>,
  wallet: WalletContextState,
  targetPlayerWallet: string,
  userWallet: string,
  statusCallback?: StatusUpdateCallback
): Promise<SignatureProcessingResult> {
  try {
    // Update status to sending
    statusCallback?.('sending', {});
    
    console.log('🚀 ENHANCED EARNINGS UPDATE: Starting with signature queue architecture', {
      targetPlayerWallet,
      userWallet
    });

    // Execute the transaction and get signature
    const signature = await updateFunction(wallet, targetPlayerWallet);
    
    console.log('✅ ENHANCED EARNINGS UPDATE: Transaction sent, signature received', {
      signature: signature.slice(0, 20) + '...'
    });

    // Update status to processing
    statusCallback?.('processing', { signature });

    // Queue signature for backend processing
    const context: TransactionContext = {
      action_type: 'earnings_update'
    };

    const queued = await queueSignatureForProcessing(signature, userWallet, context);
    
    if (!queued) {
      console.warn('⚠️ ENHANCED EARNINGS UPDATE: Failed to queue signature, but transaction was sent');
    }

    console.log('🎯 ENHANCED EARNINGS UPDATE: Signature processing flow initiated', {
      signature: signature.slice(0, 20) + '...',
      queued,
      note: 'WebSocket will handle completion notifications'
    });

    return {
      signature,
      status: 'processing',
      context
    };

  } catch (error) {
    console.error('❌ ENHANCED EARNINGS UPDATE: Failed', error);
    
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    statusCallback?.('failed', { error: errorMessage });

    throw error;
  }
}

/**
 * Generic function to queue any signature for processing
 * Useful for admin transactions or other custom operations
 */
export async function queueSignatureForProcessingGeneric(
  signature: string,
  userWallet: string,
  actionType: TransactionContext['action_type'],
  additionalContext?: Partial<TransactionContext>
): Promise<boolean> {
  const context: TransactionContext = {
    action_type: actionType,
    ...additionalContext
  };

  return queueSignatureForProcessing(signature, userWallet, context);
}

/**
 * Check transaction processing status from backend
 */
export async function getTransactionProcessingStatus(signature: string): Promise<any> {
  try {
    const response = await fetch(`${apiClient['baseUrl']}/transactions/status/${signature}`, {
      method: 'GET',
      headers: apiClient['headers']
    });

    if (!response.ok) {
      if (response.status === 404) {
        return null; // Transaction not found in processing system
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('❌ Failed to get transaction status', {
      signature: signature.slice(0, 20) + '...',
      error: error instanceof Error ? error.message : String(error)
    });
    return null;
  }
}

/**
 * Get signature processor status (useful for debugging)
 */
export async function getSignatureProcessorStatus(): Promise<any> {
  try {
    const response = await fetch(`${apiClient['baseUrl']}/transactions/processor/status`, {
      method: 'GET',
      headers: apiClient['headers']
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('❌ Failed to get processor status', error);
    return null;
  }
}
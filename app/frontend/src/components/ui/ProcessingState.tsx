/**
 * Processing State Component
 * 
 * Shows different states for transaction processing in the new signature-based architecture:
 * - sending: Transaction being sent to blockchain
 * - processing: Transaction being processed by SignatureProcessor  
 * - completed: Successfully processed and database updated
 * - failed: Processing failed with error message
 */

'use client';

import React from 'react';
import { Loader2, CheckCircle, XCircle, Send, Clock, ExternalLink } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface ProcessingStateProps {
  status: 'sending' | 'processing' | 'completed' | 'failed';
  signature?: string;
  error?: string;
  context?: {
    slot_index?: number;
    business_level?: number;
    business_type?: string;
  };
  className?: string;
  onRetry?: () => void;
  showSignature?: boolean;
}

export const ProcessingState: React.FC<ProcessingStateProps> = ({
  status,
  signature,
  error,
  context,
  className,
  onRetry,
  showSignature = true
}) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'sending':
        return {
          icon: <Send className="w-4 h-4 animate-pulse" />,
          title: 'Sending Transaction',
          subtitle: 'Please confirm in your wallet...',
          color: 'text-blue-500',
          bgColor: 'bg-blue-50 border-blue-200',
          darkBgColor: 'dark:bg-blue-900/20 dark:border-blue-800'
        };
        
      case 'processing':
        return {
          icon: <Loader2 className="w-4 h-4 animate-spin" />,
          title: 'Processing Transaction',
          subtitle: 'Updating blockchain data... (30-60s)',
          color: 'text-orange-500',
          bgColor: 'bg-orange-50 border-orange-200', 
          darkBgColor: 'dark:bg-orange-900/20 dark:border-orange-800'
        };
        
      case 'completed':
        return {
          icon: <CheckCircle className="w-4 h-4" />,
          title: 'Transaction Complete',
          subtitle: 'Successfully processed and updated!',
          color: 'text-green-500',
          bgColor: 'bg-green-50 border-green-200',
          darkBgColor: 'dark:bg-green-900/20 dark:border-green-800'
        };
        
      case 'failed':
        return {
          icon: <XCircle className="w-4 h-4" />,
          title: 'Processing Failed', 
          subtitle: error || 'An error occurred during processing',
          color: 'text-red-500',
          bgColor: 'bg-red-50 border-red-200',
          darkBgColor: 'dark:bg-red-900/20 dark:border-red-800'
        };
    }
  };

  const config = getStatusConfig();
  
  const formatSignature = (sig: string) => {
    return `${sig.substring(0, 8)}...${sig.substring(sig.length - 8)}`;
  };

  const getSolanaExplorerUrl = (sig: string) => {
    const network = process.env.NEXT_PUBLIC_SOLANA_NETWORK === 'localnet' ? 'localnet' : 'devnet';
    if (network === 'localnet') {
      return `https://explorer.solana.com/tx/${sig}?cluster=custom&customUrl=http://localhost:8899`;
    }
    return `https://explorer.solana.com/tx/${sig}?cluster=devnet`;
  };

  return (
    <div className={cn(
      'border rounded-lg p-3 transition-all duration-200',
      config.bgColor,
      config.darkBgColor,
      className
    )}>
      <div className="flex items-start gap-3">
        {/* Status Icon */}
        <div className={cn('flex-shrink-0 mt-0.5', config.color)}>
          {config.icon}
        </div>
        
        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className={cn('font-medium text-sm', config.color)}>
              {config.title}
            </h4>
            
            {/* Context Badge */}
            {context?.slot_index !== undefined && (
              <span className="px-2 py-0.5 text-xs bg-gray-100 dark:bg-gray-800 rounded-md">
                Slot {context.slot_index}
              </span>
            )}
            
            {context?.business_level !== undefined && context.business_level > 0 && (
              <span className="px-2 py-0.5 text-xs bg-purple-100 dark:bg-purple-900 rounded-md text-purple-700 dark:text-purple-300">
                Level {context.business_level}
              </span>
            )}
          </div>
          
          <p className="text-xs text-gray-600 dark:text-gray-400 mt-1">
            {config.subtitle}
          </p>
          
          {/* Signature Display */}
          {signature && showSignature && (
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs text-gray-500">Transaction:</span>
              <code className="text-xs bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded font-mono">
                {formatSignature(signature)}
              </code>
              <a
                href={getSolanaExplorerUrl(signature)}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-500 hover:text-blue-600 flex items-center gap-1"
              >
                <ExternalLink className="w-3 h-3" />
                Explorer
              </a>
            </div>
          )}
          
          {/* Retry Button for Failed State */}
          {status === 'failed' && onRetry && (
            <button
              onClick={onRetry}
              className="mt-2 text-xs bg-red-100 hover:bg-red-200 dark:bg-red-900 dark:hover:bg-red-800 text-red-700 dark:text-red-300 px-3 py-1 rounded transition-colors"
            >
              Try Again
            </button>
          )}
        </div>
        
        {/* Progress Indicator */}
        {status === 'processing' && (
          <div className="flex-shrink-0">
            <div className="flex space-x-1">
              <div className="w-1 h-1 bg-orange-400 rounded-full animate-pulse"></div>
              <div className="w-1 h-1 bg-orange-400 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }}></div>
              <div className="w-1 h-1 bg-orange-400 rounded-full animate-pulse" style={{ animationDelay: '0.4s' }}></div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Business Card Processing Overlay
 * 
 * Overlays processing state on top of business cards during transactions
 */
export interface BusinessProcessingOverlayProps {
  status: 'sending' | 'processing' | 'completed' | 'failed';
  signature?: string;
  error?: string;
  onRetry?: () => void;
  className?: string;
}

export const BusinessProcessingOverlay: React.FC<BusinessProcessingOverlayProps> = ({
  status,
  signature,
  error,
  onRetry,
  className
}) => {
  if (status === 'completed') {
    // Don't show overlay for completed state - let the updated business card show
    return null;
  }

  return (
    <div className={cn(
      'absolute inset-0 bg-white/90 dark:bg-gray-900/90 backdrop-blur-sm',
      'flex items-center justify-center rounded-lg',
      className
    )}>
      <ProcessingState
        status={status}
        signature={signature}
        error={error}
        onRetry={onRetry}
        showSignature={false}
        className="bg-transparent border-none p-2"
      />
    </div>
  );
};

/**
 * Processing States Hook
 * 
 * Manages processing states for multiple items (e.g., business slots)
 */
export interface ProcessingStatesHook {
  states: Record<number, ProcessingStateProps>;
  setProcessingState: (slotIndex: number, state: Partial<ProcessingStateProps>) => void;
  clearProcessingState: (slotIndex: number) => void;
  clearAllProcessingStates: () => void;
}

export const useProcessingStates = (): ProcessingStatesHook => {
  const [states, setStates] = React.useState<Record<number, ProcessingStateProps>>({});

  const setProcessingState = React.useCallback((slotIndex: number, state: Partial<ProcessingStateProps>) => {
    setStates(prev => ({
      ...prev,
      [slotIndex]: {
        ...prev[slotIndex],
        ...state,
        status: state.status || prev[slotIndex]?.status || 'sending'
      }
    }));
  }, []);

  const clearProcessingState = React.useCallback((slotIndex: number) => {
    setStates(prev => {
      const newStates = { ...prev };
      delete newStates[slotIndex];
      return newStates;
    });
  }, []);

  const clearAllProcessingStates = React.useCallback(() => {
    setStates({});
  }, []);

  return {
    states,
    setProcessingState,
    clearProcessingState,
    clearAllProcessingStates
  };
};

/**
 * Example usage:
 * 
 * ```tsx
 * const { states, setProcessingState, clearProcessingState } = useProcessingStates();
 * 
 * const handlePurchase = async (businessType: number, slotIndex: number, level: number) => {
 *   try {
 *     // Set sending state
 *     setProcessingState(slotIndex, { 
 *       status: 'sending',
 *       context: { slot_index: slotIndex, business_level: level } 
 *     });
 * 
 *     // Use signature-queue integration
 *     const result = await purchaseBusinessWithProcessing(
 *       purchaseBusiness,
 *       businessType,
 *       slotIndex,
 *       level,
 *       wallet.publicKey.toString(),
 *       (status, data) => {
 *         setProcessingState(slotIndex, { 
 *           status, 
 *           signature: data?.signature,
 *           error: data?.error 
 *         });
 *       }
 *     );
 * 
 *   } catch (error) {
 *     setProcessingState(slotIndex, { 
 *       status: 'failed', 
 *       error: error.message,
 *       onRetry: () => handlePurchase(businessType, slotIndex, level)
 *     });
 *   }
 * };
 * 
 * // In render:
 * <div className="relative">
 *   <BusinessCard {...businessProps} />
 *   {states[slotIndex] && (
 *     <BusinessProcessingOverlay {...states[slotIndex]} />
 *   )}
 * </div>
 * ```
 */
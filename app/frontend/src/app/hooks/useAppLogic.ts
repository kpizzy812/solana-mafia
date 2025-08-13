/**
 * Main application logic hook
 */

import React, { useState, useCallback } from 'react';
import toast from 'react-hot-toast';
import { usePlayerData } from '@/hooks/usePlayerData';
import { useWalletBalance } from '@/hooks/useWalletBalance';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useLanguage } from '@/hooks/useLanguage';
import { useWalletConnect } from '@/hooks/useWalletConnect';
import { purchaseBusiness, sellBusiness, withdrawEarnings, upgradeBusiness, updateEarnings } from '../../lib/solana';
import { calculateDailyYield, lamportsToSOL, apiClient, syncPlayerFromBlockchain } from '../../lib/api';
import { useReferralCode, useReferralActions } from '@/stores/useReferralStore';
import { retryPlayerDataFetch } from '../../lib/utils';
import { 
  purchaseBusinessWithProcessing, 
  upgradeBusinessWithProcessing,
  sellBusinessWithProcessing,
  claimEarningsWithProcessing,
  updateEarningsWithProcessing,
  queueSignatureForProcessing 
} from '@/lib/signature-queue';
import { SlotType } from '@/data/slots';
import { BUSINESS_TYPES } from '@/data/businesses';
import { SlotData, PlayerStats, BusinessData } from '../types';

export const useAppLogic = (wallet: any, connected: boolean, publicKey: any) => {
  // 🌐 Centralized language management with localStorage caching
  const { language, setLanguage, isLoaded: languageLoaded } = useLanguage();
  
  const [isPurchaseModalOpen, setIsPurchaseModalOpen] = useState(false);
  const [isWithdrawModalOpen, setIsWithdrawModalOpen] = useState(false);
  const [isUpdatingEarnings, setIsUpdatingEarnings] = useState(false);
  
  // Referral system hooks
  const referralCode = useReferralCode();
  const { markAsUsed, processUrl } = useReferralActions();
  
  // Processing states for business transactions
  const [businessProcessingStates, setBusinessProcessingStates] = useState<Record<number, {
    status: 'sending' | 'processing' | 'completed' | 'failed';
    signature?: string;
    error?: string;
  }>>({});

  const { data, loading, error, refetch } = usePlayerData();
  const { balance: walletBalance, loading: balanceLoading } = useWalletBalance();
  
  // Wallet connection and referral code management
  const { 
    userReferralCode, 
    isConnecting: isWalletConnecting, 
    error: walletConnectError,
    isNewUser,
    refetch: refetchWalletConnect
  } = useWalletConnect();

  // Process referral code after successful business purchase
  const processReferralCode = useCallback(async (walletAddress: string) => {
    if (!referralCode.hasCode) {
      console.log('🔗 No referral code to process');
      return;
    }

    try {
      console.log('🔗 Processing referral code after business purchase', {
        referralCode: referralCode.code,
        wallet: walletAddress
      });

      const response = await apiClient.post('/referrals/web/process', {
        referral_code: referralCode.code,
        wallet_address: walletAddress
      });

      if (response.success) {
        console.log('✅ Referral code processed successfully', response);
        
        // Mark referral code as used
        markAsUsed();
        
        // Show success toast
        toast.success(
          `Referral bonus activated! ${response.prestige_awarded_to_referrer || 0} prestige points awarded to referrer!`,
          { duration: 5000 }
        );
        
        console.log('🎉 Referral processing result:', {
          referrer: response.referrer_wallet,
          relations: response.referral_relations_created,
          prestige: response.prestige_awarded_to_referrer,
          levelUp: response.referrer_level_up,
          commissions: response.commission_rates
        });
      } else {
        console.warn('⚠️ Referral processing failed:', response.message);
      }
    } catch (error) {
      console.error('❌ Failed to process referral code:', error);
      // Don't show error toast as this is a bonus feature
    }
  }, [referralCode.hasCode, referralCode.code, markAsUsed]);

  // WebSocket signature processing event handler
  const handleSignatureProcessingUpdate = useCallback((event: any) => {
    console.log('🎯 WebSocket signature processing update:', event);
    
    // Find the slot index from the context or business processing states
    const slotIndex = event.context?.slot_index;
    
    // 🔧 ФИКС: Обрабатываем как business operations (с slotIndex), так и earnings operations (без slotIndex)
    if (slotIndex !== undefined) {
      // Business operations (purchase, upgrade, sell) - update business processing state
      setBusinessProcessingStates(prev => ({
        ...prev,
        [slotIndex]: {
          status: event.status === 'completed' ? 'completed' : 
                 event.status === 'failed' ? 'failed' : 'processing',
          signature: event.signature,
          error: event.status === 'failed' ? 'Transaction failed' : undefined
        }
      }));
    }

    // Handle completion for ALL transaction types (business + earnings)
    if (event.status === 'completed') {
      console.log('✅ WebSocket: Transaction completed, closing modals and updating UI');
      
      // Get action type for processing
      const actionType = event.context?.action_type || 'transaction';
      
      // 🔗 REFERRAL PROCESSING: If this was a business purchase, process referral code
      if (actionType === 'purchase' && publicKey) {
        console.log('🔗 Business purchase completed, processing referral code...');
        processReferralCode(publicKey.toString()).catch(error => {
          console.error('Failed to process referral code:', error);
        });
      }
      
      // 🔥 КРИТИЧЕСКИЙ ФИКС: Обновляем данные сразу после завершения ЛЮБОЙ транзакции!
      console.log('🔄 Triggering refetch() to update UI data...');
      refetch();
      
      // Close modals after successful completion
      setTimeout(() => {
        setIsPurchaseModalOpen(false);
        setIsWithdrawModalOpen(false);
        
        // Clear processing state for business slots only
        if (slotIndex !== undefined) {
          setTimeout(() => {
            setBusinessProcessingStates(prev => {
              const newState = { ...prev };
              delete newState[slotIndex];
              return newState;
            });
          }, 3000);
        }
      }, 1500);
      
      // Handle success toasts for different operation types
      let successMessage = 'Transaction completed successfully!';
      
      switch (actionType) {
        case 'purchase':
          successMessage = 'Business purchased successfully! 🏢';
          break;
        case 'upgrade':
          successMessage = 'Business upgraded successfully! ⬆️';
          break;
        case 'sell':
          successMessage = 'Business sold successfully! 💰';
          break;
        case 'claim':
          successMessage = 'Earnings claimed successfully! 💰';
          break;
        case 'earnings_update':
          successMessage = 'Earnings updated successfully! 📈';
          break;
      }
      
      // Show success toast
      setTimeout(() => {
        toast.success(successMessage, { id: 'transaction-success' });
      }, 500);
    } else if (event.status === 'failed') {
      // Handle failure for all transaction types
      const actionType = event.context?.action_type || 'transaction';
      let errorMessage = `${actionType} failed: ${event.result?.error || 'Unknown error'}`;
      
      setTimeout(() => {
        toast.error(errorMessage, { id: 'transaction-error' });
      }, 500);
    }
  }, [refetch, publicKey, processReferralCode, markAsUsed, referralCode.hasCode, referralCode.code]);

  // Process URL referral code on page load
  React.useEffect(() => {
    if (typeof window !== 'undefined') {
      processUrl();
    }
  }, [processUrl]);

  // WebSocket integration for real-time updates
  const {
    isConnected: wsConnected,
    isConnecting: wsConnecting,
    connectionError: wsError
  } = useWebSocket({
    wallet: connected && publicKey ? publicKey.toString() : null,
    onSignatureProcessingUpdate: handleSignatureProcessingUpdate,
    onBusinessUpdate: (data) => {
      console.log('🏢 WebSocket business update:', data);
      // Trigger refetch on business updates
      refetch();
    },
    onEarningsUpdate: (data) => {
      console.log('💰 WebSocket earnings update:', data);
      // Trigger refetch on earnings updates  
      refetch();
    },
    onPlayerUpdate: (data) => {
      console.log('👤 WebSocket player update:', data);
      // Trigger refetch on player updates
      refetch();
    },
    onPrestigeUpdate: (data) => {
      console.log('💎 WebSocket prestige update:', data);
      // Trigger refetch on prestige updates
      refetch();
    },
    refetchData: refetch,
    enabled: connected && !!publicKey
  });

  // Debug logging for new player detection
  React.useEffect(() => {
    if (connected && publicKey) {
      const isNewPlayer = !data.profile && (!data.stats || (data.stats && data.stats.total_businesses === 0 && !data.stats.last_activity));
      console.log('🔍 Player data debug:', {
        wallet: publicKey.toString(),
        hasProfile: !!data.profile,
        hasStats: !!data.stats,
        statsBusinesses: data.stats?.total_businesses,
        statsLastActivity: data.stats?.last_activity,
        hasError: !!error,
        isNewPlayer,
        loading,
        error
      });
    }
  }, [data, error, loading, connected, publicKey]);

  // Calculate derived data from backend response
  const playerStats: PlayerStats = React.useMemo(() => {
    if (!data.stats && !data.profile) {
      // If no data yet, show default values for new player
      return {
        totalEarnings: 0,
        businessCount: 0,
        businessSlots: 9, // Show all 9 business slots available
        totalSlots: 9, // Always 9 total slots (3 free + 3 basic paid + 3 premium)
        earningsBalance: 0,
      };
    }

    // All 9 slots are always available by design:
    // - Slots 0-2: Basic (free)
    // - Slots 3-5: Basic (10% of business cost)  
    // - Slots 6-8: Premium/VIP/Legendary (1/2/5 SOL fixed cost)
    const totalSlots = 9; // Always 9 slots available
    const businessCount = data.stats?.active_businesses || 0;
    
    return {
      totalEarnings: (data.stats?.total_earnings || 0) + (data.stats?.earnings_balance || 0), // 🔧 FIX: Show total earned + pending as total earnings
      businessCount: businessCount,
      businessSlots: Math.max(0, totalSlots - businessCount),
      totalSlots: totalSlots,
      earningsBalance: data.stats?.earnings_balance || 0,
    };
  }, [data.stats, data.profile]);

  // Generate slot data for the purchase modal
  const availableSlots: SlotData[] = React.useMemo(() => {
    const slots: SlotData[] = [];
    
    // Create a map of occupied slots from businesses
    const occupiedSlots = new Map<number, any>();
    
    // Use backend data
    if (data.businesses?.businesses) {
      data.businesses.businesses.forEach((business) => {
        if (business.slot_index !== undefined) {
          occupiedSlots.set(business.slot_index, {
            id: business.business_id,
            name: business.name || business.business_type,
            businessType: business.business_type,
            level: business.level,
          });
        }
      });
    }
    
    // Create basic slots (6 total: 0-2 free, 3-5 paid)
    for (let i = 0; i < 6; i++) {
      const business = occupiedSlots.get(i);
      slots.push({
        index: i,
        type: SlotType.Basic,
        isUnlocked: true, // All 6 basic slots are available (UI shows cost for 3-5)
        business: business
      });
    }
    
    // Add premium slots (6-8: Premium/VIP/Legendary with fixed costs)
    const premiumSlotTypes = [SlotType.Premium, SlotType.VIP, SlotType.Legendary];
    premiumSlotTypes.forEach((slotType, index) => {
      const slotIndex = 6 + index;
      const business = occupiedSlots.get(slotIndex);
      
      slots.push({
        index: slotIndex,
        type: slotType,
        isUnlocked: true, // All premium slots are available for purchase
        business: business
      });
    });
    
    // Return all slots (UI will handle unlocked/occupied states)
    return slots;
  }, [data.businesses]);

  // Transform businesses data for display
  const businesses: BusinessData[] = React.useMemo(() => {
    if (!data.businesses?.businesses) return [];
    
    return data.businesses.businesses.map((business) => {
      // Find business metadata from BUSINESS_TYPES
      const businessMetadata = BUSINESS_TYPES.find(bt => bt.id === parseInt(business.business_type));
      const levelData = businessMetadata?.levels?.[business.level];
      
      return {
        id: business.business_id,
        name: business.name || business.business_type,
        level: business.level, // Уровень как есть из смарт-контракта (0,1,2,3)
        earning: business.earnings_per_hour, // 🔧 FIX: Backend already returns DAILY earnings in "earnings_per_hour" field  
        totalEarned: 0, // This would need to be calculated from earnings history
        businessPrice: business.total_invested, // 🔧 FIX: Use total invested (base + upgrades) instead of just base cost
        dailyYieldPercent: calculateDailyYield(business.earnings_per_hour, business.total_invested), // 🔧 FIX: Backend already returns daily earnings
        imageUrl: levelData?.imageUrl, // Get NFT image from business metadata
        levelName: levelData?.name, // Get level name (e.g. "Corner Stand", "Smoke & Secrets")
        levelDescription: levelData?.description, // Get level description
        needsSync: false, // Direct ownership - no sync needed
        businessData: {
          businessId: business.business_id,
          slotIndex: business.slot_index,
          businessType: business.business_type,
          level: business.level, // Уровень как есть для внутренней логики
          totalInvestedAmount: business.total_invested,
          earningsPerHour: business.earnings_per_hour,
          isActive: business.is_active,
          createdAt: business.created_at ? Math.floor(new Date(business.created_at).getTime() / 1000) : undefined, // Convert ISO string to Unix timestamp
        },
      };
    });
  }, [data.businesses]);

  // Event handlers
  const handleBuyBusiness = () => {
    setIsPurchaseModalOpen(true);
  };

  const handleWithdrawClick = () => {
    setIsWithdrawModalOpen(true);
  };

  const handleUpdateEarningsClick = async () => {
    if (!connected || !publicKey) {
      toast.error('Please connect your wallet first');
      return;
    }
    
    setIsUpdatingEarnings(true);
    
    try {
      // Use current wallet as target player for earnings update
      const targetPlayerWallet = publicKey.toString();
      
      console.log('🚀 NEW ARCHITECTURE: Starting enhanced earnings update', {
        targetPlayerWallet,
        userWallet: publicKey.toString()
      });

      // Use new signature processing architecture
      const result = await updateEarningsWithProcessing(
        updateEarnings,  // Original update function (already takes wallet, targetWallet)
        wallet,  // 🔧 FIX: Pass wallet object
        targetPlayerWallet,
        publicKey.toString(),
        (status, data) => {
          console.log('🔄 Earnings update status:', status, data);
          
          // Update toast messages
          if (status === 'sending') {
            toast.loading('Updating earnings on blockchain...', { id: 'earnings-update' });
          } else if (status === 'processing') {
            toast.loading(`Transaction sent! Processing... ${data?.signature?.slice(0, 8)}...`, { id: 'earnings-update' });
          }
        }
      );

      console.log('✅ NEW ARCHITECTURE: Earnings update initiated', {
        signature: result.signature.slice(0, 20) + '...',
        status: result.status
      });

      // Show immediate success message
      toast.success(`Earnings update queued for processing! ${result.signature.slice(0, 8)}...`, { id: 'earnings-update' });

      // Note: WebSocket will handle completion notifications and UI updates
      console.log('📡 NEW ARCHITECTURE: Waiting for WebSocket notifications for completion...');
      
    } catch (error) {
      console.error('❌ NEW ARCHITECTURE: Earnings update failed:', error);
      
      // Extract more detailed error message
      let errorMessage = 'Unknown error';
      if (error instanceof Error) {
        errorMessage = error.message;
        
        // Handle specific earnings update errors
        if (errorMessage.includes('EarningsNotDue') || errorMessage.includes('not due yet')) {
          toast.error('Earnings update is not due yet. Updates happen every minute based on your schedule.', { 
            id: 'earnings-update' 
          });
          return;
        } else if (errorMessage.includes('User rejected')) {
          toast.error('Transaction cancelled by user.', { id: 'earnings-update' });
          return;
        }
      }
      
      toast.error(`Earnings update failed: ${errorMessage}`, { id: 'earnings-update' });
    } finally {
      setIsUpdatingEarnings(false);
    }
  };

  const handleSyncFromBlockchain = async () => {
    if (!connected || !publicKey) {
      toast.error('Please connect your wallet first');
      return;
    }
    
    try {
      toast.loading('Syncing data from blockchain...', { id: 'blockchain-sync' });
      
      const walletAddress = publicKey.toString();
      console.log('🔄 Syncing player data from blockchain:', walletAddress);
      
      const result = await syncPlayerFromBlockchain(walletAddress);
      
      if (result.success) {
        toast.success('Data synced from blockchain!', { id: 'blockchain-sync' });
        
        // Refresh frontend data
        setTimeout(async () => {
          try {
            console.log('🔄 Refreshing frontend data after blockchain sync...');
            await refetch();
          } catch (refreshError) {
            console.error('Failed to refresh data after sync:', refreshError);
          }
        }, 1000);
      } else {
        throw new Error(result.message || 'Sync failed');
      }
      
    } catch (error) {
      console.error('❌ Blockchain sync failed:', error);
      
      let errorMessage = 'Unknown error';
      if (error instanceof Error) {
        errorMessage = error.message;
      }
      
      toast.error(`Blockchain sync failed: ${errorMessage}`, { id: 'blockchain-sync' });
    }
  };

  const handleWithdrawSubmit = async () => {
    if (!connected || !publicKey) {
      throw new Error('Wallet not connected');
    }
    
    try {
      console.log('🚀 NEW ARCHITECTURE: Starting enhanced earnings claim', {
        userWallet: publicKey.toString()
      });

      // Use new signature processing architecture - no amount parameter needed
      const result = await claimEarningsWithProcessing(
        (wallet) => withdrawEarnings(wallet), // Simplified: no amount parameter
        wallet,  // 🔧 FIX: Pass wallet object
        publicKey.toString(),
        (status, data) => {
          console.log('🔄 Earnings claim status:', status, data);
        }
      );

      console.log('✅ NEW ARCHITECTURE: Earnings claim initiated', {
        signature: result.signature.slice(0, 20) + '...',
        status: result.status
      });

      // Note: WebSocket will handle completion notifications and UI updates
      console.log('📡 NEW ARCHITECTURE: Waiting for WebSocket notifications for claim completion...');
      
      // Return compatible result object
      return {
        signature: result.signature
      };
      
    } catch (error) {
      console.error('❌ NEW ARCHITECTURE: Earnings claim failed:', error);
      throw error;
    }
  };

  const handlePurchase = async (businessTypeId: number, slotIndex: number, level: number = 0) => {
    if (!connected || !publicKey) {
      toast.error('Please connect your wallet first');
      return;
    }

    // 🛡️ PROTECTION: Prevent duplicate transactions for the same slot
    const currentState = businessProcessingStates[slotIndex];
    if (currentState && ['sending', 'processing'].includes(currentState.status)) {
      console.warn('🚫 Transaction already in progress for slot:', slotIndex, currentState);
      toast.warning('Transaction already in progress for this slot!');
      return;
    }

    try {
      console.log('🚀 NEW ARCHITECTURE: Starting enhanced business purchase', {
        businessTypeId, slotIndex, level, userWallet: publicKey.toString()
      });

      // Use new signature processing architecture
      const result = await purchaseBusinessWithProcessing(
        purchaseBusiness,  // Original purchase function
        wallet,  // 🔧 FIX: Pass wallet object
        businessTypeId,
        slotIndex,
        level,
        publicKey.toString(),
        (status, data) => {
          console.log('🔄 Purchase status update:', status, data);
          
          // Update business processing state
          setBusinessProcessingStates(prev => ({
            ...prev,
            [slotIndex]: {
              status,
              signature: data?.signature,
              error: data?.error
            }
          }));

          // Update toast messages
          if (status === 'sending') {
            toast.loading('Sending transaction to blockchain...', { id: 'purchase' });
          } else if (status === 'processing') {
            toast.loading(`Transaction sent! Processing... ${data?.signature?.slice(0, 8)}...`, { id: 'purchase' });
          }
        }
      );

      console.log('✅ NEW ARCHITECTURE: Purchase initiated', {
        signature: result.signature.slice(0, 20) + '...',
        status: result.status
      });

      // Show immediate success message
      toast.success(`Transaction queued for processing! ${result.signature.slice(0, 8)}...`, { id: 'purchase' });

      // Note: WebSocket will handle completion notifications and UI updates
      console.log('📡 NEW ARCHITECTURE: Waiting for WebSocket notifications for completion...');

    } catch (error) {
      console.error('❌ NEW ARCHITECTURE: Purchase failed:', error);
      
      // Update processing state to failed
      setBusinessProcessingStates(prev => ({
        ...prev,
        [slotIndex]: {
          status: 'failed',
          error: error instanceof Error ? error.message : 'Unknown error'
        }
      }));

      toast.error(`Purchase failed: ${error instanceof Error ? error.message : 'Unknown error'}`, { id: 'purchase' });
    }
  };

  const handleRetry = () => {
    toast.loading('Загрузка данных...', { id: 'retry' });
    refetch().then(() => {
      toast.success('Данные обновлены!', { id: 'retry' });
    }).catch(() => {
      toast.error('Ошибка загрузки данных', { id: 'retry' });
    });
  };

  // Handle business upgrade
  const handleUpgrade = async (businessId: string, currentLevel: number, targetLevel: number) => {
    if (!connected || !publicKey) {
      toast.error('Please connect your wallet first');
      return;
    }

    try {
      // Find business from backend data to get slot index
      const business = data.businesses?.businesses.find(b => b.business_id === businessId);
      if (!business || business.slot_index === undefined) {
        throw new Error('Business not found or slot index missing');
      }

      // 🛡️ PROTECTION: Prevent duplicate transactions for the same slot
      const currentState = businessProcessingStates[business.slot_index];
      if (currentState && ['sending', 'processing'].includes(currentState.status)) {
        console.warn('🚫 Transaction already in progress for slot:', business.slot_index, currentState);
        toast.warning('Transaction already in progress for this business!');
        return;
      }

      console.log('🚀 NEW ARCHITECTURE: Starting enhanced business upgrade', {
        businessId,
        currentLevel,
        targetLevel,
        slotIndex: business.slot_index,
        userWallet: publicKey.toString()
      });

      // Use new signature processing architecture
      const result = await upgradeBusinessWithProcessing(
        upgradeBusiness,  // Original upgrade function (already takes wallet, bId, sIndex, cLevel, tLevel)
        wallet,  // 🔧 FIX: Pass wallet object
        businessId,
        business.slot_index,
        currentLevel,
        targetLevel,
        publicKey.toString(),
        (status, data) => {
          console.log('🔄 Business upgrade status:', status, data);
          
          // Update business processing state
          setBusinessProcessingStates(prev => ({
            ...prev,
            [business.slot_index]: {
              status,
              signature: data?.signature,
              error: data?.error
            }
          }));

          // Update toast messages
          if (status === 'sending') {
            toast.loading('Upgrading business...', { id: 'upgrade' });
          } else if (status === 'processing') {
            toast.loading(`Transaction sent! Processing upgrade... ${data?.signature?.slice(0, 8)}...`, { id: 'upgrade' });
          }
        }
      );

      console.log('✅ NEW ARCHITECTURE: Business upgrade initiated', {
        signature: result.signature.slice(0, 20) + '...',
        status: result.status
      });

      // Show immediate success message
      toast.success(`Business upgrade queued for processing! ${result.signature.slice(0, 8)}...`, { id: 'upgrade' });

      // Note: WebSocket will handle completion notifications and UI updates
      console.log('📡 NEW ARCHITECTURE: Waiting for WebSocket notifications for upgrade completion...');
      
    } catch (error) {
      console.error('❌ NEW ARCHITECTURE: Business upgrade failed:', error);
      
      // Extract more detailed error message
      let errorMessage = 'Unknown error';
      if (error instanceof Error) {
        errorMessage = error.message;
        // Check if it's a duplicate transaction error (which might mean it actually succeeded)
        if (errorMessage.includes('already been processed')) {
          toast.success('Upgrade may have succeeded! Processing...', { id: 'upgrade' });
          return;
        }
      }
      
      toast.error(`Upgrade failed: ${errorMessage}`, { id: 'upgrade' });
    }
  };

  // Handle business sell
  const handleSell = async (businessId: string, slotIndex: number) => {
    if (!connected || !publicKey) {
      toast.error('Please connect your wallet first');
      return;
    }

    // 🛡️ PROTECTION: Prevent duplicate transactions for the same slot
    const currentState = businessProcessingStates[slotIndex];
    if (currentState && ['sending', 'processing'].includes(currentState.status)) {
      console.warn('🚫 Transaction already in progress for slot:', slotIndex, currentState);
      toast.warning('Transaction already in progress for this business!');
      return;
    }

    try {
      console.log('🚀 NEW ARCHITECTURE: Starting enhanced business sell', {
        businessId,
        slotIndex,
        userWallet: publicKey.toString()
      });

      // Use new signature processing architecture
      const result = await sellBusinessWithProcessing(
        sellBusiness,  // Original sell function (already takes wallet, bId, sIndex)
        wallet,  // 🔧 FIX: Pass wallet object
        businessId,
        slotIndex,
        publicKey.toString(),
        (status, data) => {
          console.log('🔄 Business sell status:', status, data);
          
          // Update business processing state
          setBusinessProcessingStates(prev => ({
            ...prev,
            [slotIndex]: {
              status,
              signature: data?.signature,
              error: data?.error
            }
          }));

          // Update toast messages
          if (status === 'sending') {
            toast.loading('Selling business...', { id: 'sell' });
          } else if (status === 'processing') {
            toast.loading(`Transaction sent! Processing sale... ${data?.signature?.slice(0, 8)}...`, { id: 'sell' });
          }
        }
      );

      console.log('✅ NEW ARCHITECTURE: Business sell initiated', {
        signature: result.signature.slice(0, 20) + '...',
        status: result.status
      });

      // Show immediate success message
      toast.success(`Business sale queued for processing! ${result.signature.slice(0, 8)}...`, { id: 'sell' });

      // Note: WebSocket will handle completion notifications and UI updates
      console.log('📡 NEW ARCHITECTURE: Waiting for WebSocket notifications for sale completion...');
      
    } catch (error) {
      console.error('❌ NEW ARCHITECTURE: Business sell failed:', error);
      
      // Extract more detailed error message
      let errorMessage = 'Unknown error';
      if (error instanceof Error) {
        errorMessage = error.message;
        // Check if it's a duplicate transaction error (which might mean it actually succeeded)
        if (errorMessage.includes('already been processed')) {
          toast.success('Sale may have succeeded! Processing...', { id: 'sell' });
          return;
        }
      }
      
      toast.error(`Sale failed: ${errorMessage}`, { id: 'sell' });
    }
  };

  return {
    // State
    language,
    setLanguage,
    languageLoaded, // 🆕 NEW: Prevents language flash on page load
    isPurchaseModalOpen,
    setIsPurchaseModalOpen,
    isWithdrawModalOpen,
    setIsWithdrawModalOpen,
    isUpdatingEarnings,
    businessProcessingStates,  // 🆕 NEW: Processing states for signature architecture
    setBusinessProcessingStates,
    
    // WebSocket state
    wsConnected,
    wsConnecting,
    wsError,
    
    // Data
    data,
    loading,
    error,
    playerStats,
    availableSlots,
    businesses,
    walletBalance,
    balanceLoading,
    
    // Wallet connection
    userReferralCode,
    isWalletConnecting,
    walletConnectError,
    isNewUser,
    refetchWalletConnect,
    
    // Actions
    handleBuyBusiness,
    handleWithdrawClick,
    handleUpdateEarningsClick,
    handleSyncFromBlockchain,  // 🆕 NEW: Sync data directly from blockchain
    handleWithdrawSubmit,
    handlePurchase,
    handleRetry,
    handleUpgrade,
    handleSell,
    refetch
  };
};
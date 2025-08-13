/**
 * Hook for handling wallet connection and user creation
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { connectWallet, ConnectWalletResponse } from '@/lib/api';
import toast from 'react-hot-toast';

interface UseWalletConnectReturn {
  userReferralCode: string | null;
  isConnecting: boolean;
  error: string | null;
  isNewUser: boolean;
  refetch: () => Promise<void>;
}

export const useWalletConnect = (): UseWalletConnectReturn => {
  const { connected, publicKey } = useWallet();
  const [userReferralCode, setUserReferralCode] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isNewUser, setIsNewUser] = useState(false);
  
  // Track if we've already processed this wallet to avoid multiple calls
  const processedWalletRef = useRef<string | null>(null);

  const connectUserWallet = useCallback(async () => {
    if (!connected || !publicKey) {
      setUserReferralCode(null);
      setError(null);
      setIsNewUser(false);
      processedWalletRef.current = null;
      return;
    }

    const walletAddress = publicKey.toString();
    
    // Skip if we've already processed this wallet
    if (processedWalletRef.current === walletAddress) {
      return;
    }

    setIsConnecting(true);
    setError(null);

    try {
      console.log('🔗 Connecting wallet and creating user:', walletAddress);
      
      const response = await connectWallet(walletAddress);
      
      if (response.success && response.data) {
        setUserReferralCode(response.data.referral_code);
        setIsNewUser(response.data.is_new_user);
        processedWalletRef.current = walletAddress;
        
        // Show welcome message for new users
        if (response.data.is_new_user) {
          toast.success('🎉 Welcome to Solana Mafia! Your referral code is ready!', {
            duration: 5000
          });
        }
        
        console.log('✅ User connected successfully:', {
          wallet: walletAddress,
          referralCode: response.data.referral_code,
          isNewUser: response.data.is_new_user
        });
      } else {
        const errorMsg = response.error || 'Failed to connect wallet';
        setError(errorMsg);
        console.error('❌ Wallet connection failed:', errorMsg);
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Unexpected error';
      setError(errorMsg);
      console.error('❌ Wallet connection error:', error);
    } finally {
      setIsConnecting(false);
    }
  }, [connected, publicKey]);

  // Auto-connect when wallet connects
  useEffect(() => {
    connectUserWallet();
  }, [connectUserWallet]);

  // Manual refetch function
  const refetch = useCallback(async () => {
    processedWalletRef.current = null; // Clear cache to force refetch
    await connectUserWallet();
  }, [connectUserWallet]);

  return {
    userReferralCode,
    isConnecting,
    error,
    isNewUser,
    refetch
  };
};
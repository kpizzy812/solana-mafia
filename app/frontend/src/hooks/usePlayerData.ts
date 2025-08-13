/**
 * React hook for fetching and managing player data
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { 
  apiClient, 
  PlayerProfile, 
  PlayerStats, 
  PlayerBusinesses, 
  ApiResponse 
} from '@/lib/api';

export interface PlayerData {
  profile: PlayerProfile | null;
  stats: PlayerStats | null;
  businesses: PlayerBusinesses | null;
}

export interface UsePlayerDataReturn {
  data: PlayerData;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  isConnected: boolean;
}

export const usePlayerData = (): UsePlayerDataReturn => {
  const { connected, publicKey } = useWallet();
  const [data, setData] = useState<PlayerData>({
    profile: null,
    stats: null,
    businesses: null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const wallet = publicKey?.toString();

  const fetchPlayerData = useCallback(async () => {
    if (!connected || !wallet) {
      setData({ profile: null, stats: null, businesses: null });
      setError(null);
      return;
    }

    // Cancel previous request
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    // Create new abort controller
    abortControllerRef.current = new AbortController();

    setLoading(true);
    setError(null);

    try {
      // Set wallet auth
      apiClient.setWalletAuth(wallet);

      // Fetch all player data in parallel
      const [profileResult, statsResult, businessesResult] = await Promise.allSettled([
        apiClient.getPlayerProfile(wallet),
        apiClient.getPlayerStats(wallet),
        apiClient.getPlayerBusinesses(wallet, true, 50, 0),
      ]);

      // Check if request was aborted
      if (abortControllerRef.current?.signal.aborted) {
        return;
      }

      const newData: PlayerData = {
        profile: null,
        stats: null,
        businesses: null,
      };

      let hasErrors = false;
      const errors: string[] = [];

      // Process profile result
      if (profileResult.status === 'fulfilled') {
        const response = profileResult.value;
        console.log('🔍 Profile result:', response);
        if (response.success && response.data) {
          newData.profile = response.data;
        } else if (response.error && response.error !== 'PLAYER_NOT_FOUND') {
          errors.push(`Profile: ${response.error}`);
          hasErrors = true;
        }
      } else {
        console.log('🔍 Profile failed:', profileResult.reason);
        // Ignore 404 errors for new players
        const isNotFoundError = profileResult.reason?.message?.includes('404') || 
                              profileResult.reason?.status === 404;
        if (!isNotFoundError) {
          errors.push(`Profile: ${profileResult.reason.message}`);
          hasErrors = true;
        }
      }

      // Process stats result
      if (statsResult.status === 'fulfilled') {
        const response = statsResult.value;
        console.log('🔍 Stats result:', response);
        if (response.success && response.data) {
          newData.stats = response.data;
        } else if (response.error && response.error !== 'PLAYER_NOT_FOUND') {
          errors.push(`Stats: ${response.error}`);
          hasErrors = true;
        }
      } else {
        console.log('🔍 Stats failed:', statsResult.reason);
        // Ignore 404 errors for new players
        const isNotFoundError = statsResult.reason?.message?.includes('404') || 
                              statsResult.reason?.status === 404;
        if (!isNotFoundError) {
          errors.push(`Stats: ${statsResult.reason.message}`);
          hasErrors = true;
        }
      }

      // Process businesses result
      if (businessesResult.status === 'fulfilled') {
        const response = businessesResult.value;
        if (response.success && response.data) {
          newData.businesses = response.data;
        } else if (response.error && response.error !== 'PLAYER_NOT_FOUND') {
          errors.push(`Businesses: ${response.error}`);
          hasErrors = true;
        }
      } else {
        // Ignore 404 errors for new players
        const isNotFoundError = businessesResult.reason?.message?.includes('404') || 
                              businessesResult.reason?.status === 404;
        if (!isNotFoundError) {
          errors.push(`Businesses: ${businessesResult.reason.message}`);
          hasErrors = true;
        }
      }

      console.log('🔍 Final result:', { 
        newData, 
        hasErrors, 
        errors, 
        isNewPlayer: !newData.profile && !newData.stats 
      });

      setData(newData);

      if (hasErrors) {
        setError(errors.join('; '));
      } else {
        setError(null); // Clear any previous errors
      }

    } catch (err) {
      if (abortControllerRef.current?.signal.aborted) {
        return;
      }
      
      const errorMessage = err instanceof Error ? err.message : 'Failed to fetch player data';
      setError(errorMessage);
      console.error('Error fetching player data:', err);
    } finally {
      if (!abortControllerRef.current?.signal.aborted) {
        setLoading(false);
      }
    }
  }, [connected, wallet]);

  // Fetch data when wallet connection changes
  useEffect(() => {
    fetchPlayerData();

    // Cleanup function
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchPlayerData]);

  // Clear auth when wallet disconnects
  useEffect(() => {
    if (!connected) {
      apiClient.clearAuth();
    }
  }, [connected]);

  const refetch = useCallback(async () => {
    await fetchPlayerData();
  }, [fetchPlayerData]);

  return {
    data,
    loading,
    error,
    refetch,
    isConnected: connected,
  };
};
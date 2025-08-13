/**
 * Hook for managing FOMO banner data
 */

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api';
import { FomoData } from '../types';

export const useFomoData = (connected: boolean, publicKey: any) => {
  const [fomoData, setFomoData] = useState<FomoData>({
    totalPlayers: 0,
    currentEntryFee: 0.012, // SOL amount
    currentEntryFeeUsd: 2.0, // USD amount  
    solPriceUsd: 162.0, // Current SOL price
    lastUpdated: null
  });

  useEffect(() => {
    if (connected && publicKey) {
      const loadFomoData = async () => {
        try {
          // Try new SOL price endpoint first
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
          
          let solPriceUsd = 162.0;
          let currentEntryFeeUsd = 2.0;
          let currentEntryFeeSol = 0.012;
          
          try {
            const priceResponse = await fetch(`${apiUrl}/api/v1/stats/sol-price`);
            if (priceResponse.ok) {
              const priceData = await priceResponse.json();
              if (priceData.success && priceData.data) {
                solPriceUsd = priceData.data.sol_price_usd || 162.0;
                currentEntryFeeUsd = priceData.data.current_entry_fee_usd || 2.0;
                currentEntryFeeSol = priceData.data.current_entry_fee_sol || 0.012;
              }
            }
          } catch (err) {
            console.warn('SOL price endpoint failed, using fallback');
          }
          
          // Get global stats (including player count) from existing endpoint
          const response = await apiClient.getGlobalStats();
          if (response.success && response.data) {
            setFomoData({
              totalPlayers: response.data.total_players,
              currentEntryFee: currentEntryFeeSol,
              currentEntryFeeUsd: currentEntryFeeUsd,
              solPriceUsd: solPriceUsd,
              lastUpdated: 'live'
            });
          }
        } catch (error) {
          console.error('Failed to load FOMO data:', error);
        }
      };
      
      loadFomoData();
      
      // Refresh FOMO data every 30 seconds
      const interval = setInterval(loadFomoData, 30000);
      return () => clearInterval(interval);
    }
  }, [connected, publicKey]);

  return { fomoData };
};
/**
 * ReferralStats - Display user's referral statistics
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Users, DollarSign, TrendingUp, Clock, Info, Loader2 } from 'lucide-react';
import { useWallet } from '@solana/wallet-adapter-react';
import { apiClient } from '@/lib/api';

interface ReferralStatsData {
  total_referrals: number;
  total_earnings: number;
  pending_commission: number;
  level_1_referrals: number;
  level_2_referrals: number;
  level_3_referrals: number;
  level_1_earnings: number;
  level_2_earnings: number;
  level_3_earnings: number;
  sol_balance_lamports: number;
  total_sol_withdrawn: number;
  last_withdrawal_at: string | null;
  last_updated_at: string | null;
}

interface SolBalanceData {
  balance_lamports: number;
  balance_sol: number;
  total_withdrawn_lamports: number;
  total_withdrawn_sol: number;
  last_withdrawal_at: string | null;
  available_for_withdrawal: boolean;
}

export function ReferralStats() {
  const { publicKey } = useWallet();
  const [stats, setStats] = useState<ReferralStatsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchStats = async () => {
      if (!publicKey) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        // Use the wallet address as path parameter
        const response = await apiClient.get(`/referrals/${publicKey.toString()}/stats`);
        
        if (response.success) {
          setStats(response);
        } else {
          setError('Failed to load referral statistics');
        }
      } catch (err) {
        console.error('Failed to fetch referral stats:', err);
        setError('Failed to load referral statistics');
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
  }, [publicKey]);

  const formatSOL = (lamports: number) => {
    return (lamports / 1_000_000_000).toFixed(4);
  };

  if (loading) {
    return (
      <div className="bg-card border border-border rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Users className="w-5 h-5 text-primary" />
          <h2 className="text-xl font-semibold">Referral Statistics</h2>
        </div>
        
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card border border-border rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Users className="w-5 h-5 text-primary" />
          <h2 className="text-xl font-semibold">Referral Statistics</h2>
        </div>
        
        <div className="text-center py-8">
          <p className="text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  // Default stats if no data
  const displayStats = stats || {
    total_referrals: 0,
    total_earnings: 0,
    pending_commission: 0,
    level_1_referrals: 0,
    level_2_referrals: 0,
    level_3_referrals: 0,
    level_1_earnings: 0,
    level_2_earnings: 0,
    level_3_earnings: 0,
    sol_balance_lamports: 0,
    total_sol_withdrawn: 0,
    last_withdrawal_at: null,
    last_updated_at: null
  };

  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4">
        <Users className="w-4 h-4 text-primary" />
        <h2 className="text-lg font-semibold">Referral Statistics</h2>
        <div className="group relative">
          <Info className="w-4 h-4 text-muted-foreground cursor-help" />
          <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block bg-popover border border-border rounded-lg p-3 text-sm w-64 shadow-lg z-10">
            <p>Statistics update in real-time when your referrals make transactions</p>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="bg-muted rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <Users className="w-3 h-3 text-primary" />
            <span className="text-xs font-medium">Total Referrals</span>
          </div>
          <div className="text-xl font-bold">{displayStats.total_referrals}</div>
        </div>

        <div className="bg-muted rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1">
            <DollarSign className="w-3 h-3 text-green-500" />
            <span className="text-xs font-medium">Total Earnings</span>
          </div>
          <div className="text-xl font-bold text-green-500">
            {formatSOL(displayStats.total_earnings)} SOL
          </div>
        </div>
      </div>

      {/* Pending Commission */}
      {displayStats.pending_commission > 0 && (
        <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3 mb-4">
          <div className="flex items-center gap-2 mb-1">
            <Clock className="w-3 h-3 text-yellow-500" />
            <span className="text-xs font-medium text-yellow-500">Pending Commission</span>
          </div>
          <div className="text-lg font-bold text-yellow-500">
            {formatSOL(displayStats.pending_commission)} SOL
          </div>
          <p className="text-xs text-yellow-600 mt-1">
            Will be distributed with next earnings claim
          </p>
        </div>
      )}

      {/* Level Breakdown */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
          Level Breakdown
        </h3>

        {/* Level 1 */}
        <div className="flex items-center justify-between p-2 bg-muted rounded-lg">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <div>
              <div className="text-xs font-medium">Level 1 (10%)</div>
              <div className="text-xs text-muted-foreground">Direct referrals</div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs font-semibold">{displayStats.level_1_referrals} users</div>
            <div className="text-xs text-muted-foreground">
              {formatSOL(displayStats.level_1_earnings)} SOL
            </div>
          </div>
        </div>

        {/* Level 2 */}
        <div className="flex items-center justify-between p-2 bg-muted rounded-lg">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
            <div>
              <div className="text-xs font-medium">Level 2 (5%)</div>
              <div className="text-xs text-muted-foreground">Referrals of referrals</div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs font-semibold">{displayStats.level_2_referrals} users</div>
            <div className="text-xs text-muted-foreground">
              {formatSOL(displayStats.level_2_earnings)} SOL
            </div>
          </div>
        </div>

        {/* Level 3 */}
        <div className="flex items-center justify-between p-2 bg-muted rounded-lg">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
            <div>
              <div className="text-xs font-medium">Level 3 (2.5%)</div>
              <div className="text-xs text-muted-foreground">Third level referrals</div>
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs font-semibold">{displayStats.level_3_referrals} users</div>
            <div className="text-xs text-muted-foreground">
              {formatSOL(displayStats.level_3_earnings)} SOL
            </div>
          </div>
        </div>
      </div>

      {/* Last Updated */}
      {displayStats.last_updated_at && (
        <div className="mt-4 text-xs text-muted-foreground text-center">
          Last updated: {new Date(displayStats.last_updated_at).toLocaleString()}
        </div>
      )}
    </div>
  );
}
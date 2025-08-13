/**
 * ReferralsList - Display list of user's referrals
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Users, DollarSign, Calendar, TrendingUp, ChevronRight, Filter, Loader2 } from 'lucide-react';
import { useWallet } from '@solana/wallet-adapter-react';
import { apiClient } from '@/lib/api';

interface ReferralUser {
  referee_id: string;
  referee_name: string;
  level: number;
  commission_rate: number;
  total_earnings_referred: number;
  total_commission_earned: number;
  first_earning_at: string | null;
  created_at: string;
}

export function ReferralsList() {
  const { publicKey } = useWallet();
  const [referrals, setReferrals] = useState<ReferralUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedLevel, setSelectedLevel] = useState<number | null>(null);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);

  useEffect(() => {
    const fetchReferrals = async () => {
      if (!publicKey) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const params = new URLSearchParams({
          limit: '20',
          offset: (page * 20).toString()
        });

        if (selectedLevel) {
          params.append('level', selectedLevel.toString());
        }

        const response = await apiClient.get(`/referrals/${publicKey.toString()}/info?${params}`);
        
        if (response.success) {
          const newReferrals = response.referrals || [];
          
          if (page === 0) {
            setReferrals(newReferrals);
          } else {
            setReferrals(prev => [...prev, ...newReferrals]);
          }
          
          setHasMore(newReferrals.length === 20);
        } else {
          setError('Failed to load referrals');
        }
      } catch (err) {
        console.error('Failed to fetch referrals:', err);
        setError('Failed to load referrals');
      } finally {
        setLoading(false);
      }
    };

    fetchReferrals();
  }, [publicKey, selectedLevel, page]);

  const formatSOL = (lamports: number) => {
    return (lamports / 1_000_000_000).toFixed(4);
  };

  const formatAddress = (address: string) => {
    return `${address.slice(0, 4)}...${address.slice(-4)}`;
  };

  const handleLevelFilter = (level: number | null) => {
    setSelectedLevel(level);
    setPage(0);
    setReferrals([]);
  };

  const loadMore = () => {
    if (!loading && hasMore) {
      setPage(prev => prev + 1);
    }
  };

  const getLevelColor = (level: number) => {
    switch (level) {
      case 1: return 'text-green-500 bg-green-500/10';
      case 2: return 'text-blue-500 bg-blue-500/10';
      case 3: return 'text-purple-500 bg-purple-500/10';
      default: return 'text-gray-500 bg-gray-500/10';
    }
  };

  const getLevelRate = (level: number) => {
    switch (level) {
      case 1: return '10%';
      case 2: return '5%';
      case 3: return '2.5%';
      default: return '0%';
    }
  };

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-primary" />
          <h2 className="text-xl font-semibold">Your Referrals</h2>
        </div>

        {/* Level Filter */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-muted-foreground" />
          <div className="flex gap-1">
            <button
              onClick={() => handleLevelFilter(null)}
              className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                selectedLevel === null 
                  ? 'bg-primary text-primary-foreground' 
                  : 'bg-muted hover:bg-muted/80'
              }`}
            >
              All
            </button>
            {[1, 2, 3].map(level => (
              <button
                key={level}
                onClick={() => handleLevelFilter(level)}
                className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                  selectedLevel === level 
                    ? 'bg-primary text-primary-foreground' 
                    : 'bg-muted hover:bg-muted/80'
                }`}
              >
                L{level}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loading && page === 0 ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      ) : error ? (
        <div className="text-center py-8">
          <p className="text-muted-foreground">{error}</p>
        </div>
      ) : referrals.length === 0 ? (
        <div className="text-center py-12">
          <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
          <h3 className="text-lg font-semibold mb-2">No Referrals Yet</h3>
          <p className="text-muted-foreground max-w-md mx-auto">
            Share your referral link to start earning commissions when friends join and play!
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {referrals.map((referral) => (
            <div 
              key={`${referral.referee_id}-${referral.level}`}
              className="border border-border rounded-lg p-4 hover:bg-accent/50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  {/* Level Badge */}
                  <div className={`px-2 py-1 rounded-full text-xs font-semibold ${getLevelColor(referral.level)}`}>
                    L{referral.level}
                  </div>

                  {/* User Info */}
                  <div>
                    <div className="font-medium">
                      {referral.referee_name !== 'Unknown' 
                        ? referral.referee_name 
                        : formatAddress(referral.referee_id)
                      }
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {getLevelRate(referral.level)} commission rate
                    </div>
                  </div>
                </div>

                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              </div>

              {/* Stats Row */}
              <div className="grid grid-cols-3 gap-4 mt-4 pt-4 border-t border-border">
                <div>
                  <div className="flex items-center gap-1 mb-1">
                    <TrendingUp className="w-3 h-3 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">Their Earnings</span>
                  </div>
                  <div className="text-sm font-semibold">
                    {formatSOL(referral.total_earnings_referred)} SOL
                  </div>
                </div>

                <div>
                  <div className="flex items-center gap-1 mb-1">
                    <DollarSign className="w-3 h-3 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">Your Commission</span>
                  </div>
                  <div className="text-sm font-semibold text-green-500">
                    {formatSOL(referral.total_commission_earned)} SOL
                  </div>
                </div>

                <div>
                  <div className="flex items-center gap-1 mb-1">
                    <Calendar className="w-3 h-3 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">Joined</span>
                  </div>
                  <div className="text-sm">
                    {new Date(referral.created_at).toLocaleDateString()}
                  </div>
                </div>
              </div>

              {/* First Earning Date */}
              {referral.first_earning_at && (
                <div className="mt-2 text-xs text-muted-foreground">
                  First earning: {new Date(referral.first_earning_at).toLocaleDateString()}
                </div>
              )}
            </div>
          ))}

          {/* Load More Button */}
          {hasMore && (
            <button
              onClick={loadMore}
              disabled={loading}
              className="w-full py-3 text-sm text-muted-foreground hover:text-foreground transition-colors disabled:opacity-50"
            >
              {loading ? (
                <div className="flex items-center justify-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Loading...
                </div>
              ) : (
                'Load More Referrals'
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
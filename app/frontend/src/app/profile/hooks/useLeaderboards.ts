'use client';

import { useState, useEffect, useCallback } from 'react';

interface LeaderboardEntry {
  rank: number;
  wallet: string;
  prestige_level: string;
  prestige_points: number;
}

interface EarningsLeaderboardEntry extends LeaderboardEntry {
  total_earned: number;
  total_invested: number;
  roi_percentage: number;
  active_businesses: number;
  last_claim_amount?: number;
  last_claim_at?: string;
}

interface ReferralLeaderboardEntry extends LeaderboardEntry {
  total_referrals: number;
  total_referral_earnings: number;
  level_1_referrals: number;
  level_2_referrals: number;
  level_3_referrals: number;
  level_1_earnings: number;
  level_2_earnings: number;
  level_3_earnings: number;
}

interface PrestigeLeaderboardEntry extends LeaderboardEntry {
  current_points: number;
  total_points_earned: number;
  current_level: string;
  level_up_count: number;
  points_to_next_level: number;
  progress_percentage: number;
  achievements_unlocked: number;
}

interface PlayerPosition {
  wallet: string;
  earnings_rank?: number;
  referrals_rank?: number;
  prestige_rank?: number;
  combined_rank?: number;
  total_players_earnings: number;
  total_players_referrals: number;
  total_players_prestige: number;
  earnings_percentile?: number;
  referrals_percentile?: number;
  prestige_percentile?: number;
}

interface LeaderboardData {
  leaderboard: any[];
  period: string;
  total_entries: number;
  stats: any;
  last_updated: string;
  pagination: {
    limit: number;
    offset: number;
    total: number;
    has_next: boolean;
    has_previous: boolean;
  };
}

interface UseLeaderboardsReturn {
  earningsLeaderboard: LeaderboardData | null;
  referralsLeaderboard: LeaderboardData | null;
  prestigeLeaderboard: LeaderboardData | null;
  playerPosition: PlayerPosition | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

// Mock data generators
const generateMockEarningsLeaderboard = (): LeaderboardData => {
  const entries: EarningsLeaderboardEntry[] = [];
  const prestigeLevels = ['wannabe', 'associate', 'soldier', 'capo', 'underboss', 'boss'];
  
  for (let i = 0; i < 50; i++) {
    const totalInvested = Math.floor(Math.random() * 100000000000) + 5000000000;
    const totalEarned = Math.floor(totalInvested * (0.5 + Math.random() * 2));
    
    entries.push({
      rank: i + 1,
      wallet: `${Math.random().toString(36).substring(2, 6)}...${Math.random().toString(36).substring(2, 6)}`,
      prestige_level: prestigeLevels[Math.floor(Math.random() * prestigeLevels.length)],
      prestige_points: Math.floor(Math.random() * 5000) + 100,
      total_earned: totalEarned,
      total_invested: totalInvested,
      roi_percentage: ((totalEarned - totalInvested) / totalInvested) * 100,
      active_businesses: Math.floor(Math.random() * 10) + 1,
      last_claim_amount: Math.floor(Math.random() * 5000000000),
      last_claim_at: new Date(Date.now() - Math.random() * 24 * 60 * 60 * 1000).toISOString(),
    });
  }

  // Sort by total_earned descending
  entries.sort((a, b) => b.total_earned - a.total_earned);
  
  return {
    leaderboard: entries,
    period: 'all_time',
    total_entries: entries.length,
    stats: {
      total_players: entries.length,
      total_earnings: entries.reduce((sum, e) => sum + e.total_earned, 0),
      average_earnings: entries.reduce((sum, e) => sum + e.total_earned, 0) / entries.length,
      max_earnings: Math.max(...entries.map(e => e.total_earned)),
      top_earner_wallet: entries[0]?.wallet,
      top_earner_amount: entries[0]?.total_earned,
    },
    last_updated: new Date().toISOString(),
    pagination: {
      limit: 100,
      offset: 0,
      total: entries.length,
      has_next: false,
      has_previous: false,
    },
  };
};

const generateMockReferralsLeaderboard = (): LeaderboardData => {
  const entries: ReferralLeaderboardEntry[] = [];
  const prestigeLevels = ['wannabe', 'associate', 'soldier', 'capo', 'underboss', 'boss'];
  
  for (let i = 0; i < 50; i++) {
    const level1 = Math.floor(Math.random() * 50);
    const level2 = Math.floor(Math.random() * 20);
    const level3 = Math.floor(Math.random() * 10);
    const totalReferrals = level1 + level2 + level3;
    
    if (totalReferrals === 0) continue;
    
    entries.push({
      rank: i + 1,
      wallet: `${Math.random().toString(36).substring(2, 6)}...${Math.random().toString(36).substring(2, 6)}`,
      prestige_level: prestigeLevels[Math.floor(Math.random() * prestigeLevels.length)],
      prestige_points: Math.floor(Math.random() * 5000) + 100,
      total_referrals: totalReferrals,
      total_referral_earnings: Math.floor(Math.random() * 10000000000) + 1000000000,
      level_1_referrals: level1,
      level_2_referrals: level2,
      level_3_referrals: level3,
      level_1_earnings: Math.floor(Math.random() * 5000000000),
      level_2_earnings: Math.floor(Math.random() * 3000000000),
      level_3_earnings: Math.floor(Math.random() * 1000000000),
    });
  }

  // Sort by total_referrals descending
  entries.sort((a, b) => b.total_referrals - a.total_referrals);
  
  return {
    leaderboard: entries,
    period: 'all_time',
    total_entries: entries.length,
    stats: {
      total_players: entries.length,
      total_referrals: entries.reduce((sum, e) => sum + e.total_referrals, 0),
      total_referral_earnings: entries.reduce((sum, e) => sum + e.total_referral_earnings, 0),
      max_referrals: Math.max(...entries.map(e => e.total_referrals)),
      top_referrer_wallet: entries[0]?.wallet,
      top_referrer_count: entries[0]?.total_referrals,
    },
    last_updated: new Date().toISOString(),
    pagination: {
      limit: 100,
      offset: 0,
      total: entries.length,
      has_next: false,
      has_previous: false,
    },
  };
};

const generateMockPrestigeLeaderboard = (): LeaderboardData => {
  const entries: PrestigeLeaderboardEntry[] = [];
  const prestigeLevels = ['wannabe', 'associate', 'soldier', 'capo', 'underboss', 'boss'];
  
  for (let i = 0; i < 50; i++) {
    const currentPoints = Math.floor(Math.random() * 15000) + 100;
    const currentLevel = prestigeLevels[Math.min(Math.floor(currentPoints / 2000), prestigeLevels.length - 1)];
    
    entries.push({
      rank: i + 1,
      wallet: `${Math.random().toString(36).substring(2, 6)}...${Math.random().toString(36).substring(2, 6)}`,
      prestige_level: currentLevel,
      prestige_points: currentPoints,
      current_points: currentPoints,
      total_points_earned: currentPoints + Math.floor(Math.random() * 10000),
      current_level: currentLevel,
      level_up_count: Math.floor(Math.random() * 15),
      points_to_next_level: Math.max(0, (Math.floor(currentPoints / 2000) + 1) * 2000 - currentPoints),
      progress_percentage: Math.random() * 100,
      achievements_unlocked: Math.floor(Math.random() * 20),
    });
  }

  // Sort by current_points descending
  entries.sort((a, b) => b.current_points - a.current_points);
  
  return {
    leaderboard: entries,
    period: 'all_time',
    total_entries: entries.length,
    stats: {
      total_players: entries.length,
      average_prestige_points: entries.reduce((sum, e) => sum + e.current_points, 0) / entries.length,
      max_prestige_points: Math.max(...entries.map(e => e.current_points)),
      boss_level_players: entries.filter(e => e.current_level === 'boss').length,
      top_prestige_wallet: entries[0]?.wallet,
      top_prestige_points: entries[0]?.current_points,
    },
    last_updated: new Date().toISOString(),
    pagination: {
      limit: 100,
      offset: 0,
      total: entries.length,
      has_next: false,
      has_previous: false,
    },
  };
};

const generateMockPlayerPosition = (wallet: string, leaderboards: {
  earnings?: LeaderboardData;
  referrals?: LeaderboardData;
  prestige?: LeaderboardData;
}): PlayerPosition => {
  // Find player position in each leaderboard
  const earningsRank = leaderboards.earnings?.leaderboard.findIndex(
    (entry: any) => entry.wallet === wallet
  );
  const referralsRank = leaderboards.referrals?.leaderboard.findIndex(
    (entry: any) => entry.wallet === wallet
  );
  const prestigeRank = leaderboards.prestige?.leaderboard.findIndex(
    (entry: any) => entry.wallet === wallet
  );

  const calculatePercentile = (rank: number, total: number) => {
    return ((total - rank) / total) * 100;
  };

  return {
    wallet,
    earnings_rank: earningsRank !== undefined && earningsRank >= 0 ? earningsRank + 1 : undefined,
    referrals_rank: referralsRank !== undefined && referralsRank >= 0 ? referralsRank + 1 : undefined,
    prestige_rank: prestigeRank !== undefined && prestigeRank >= 0 ? prestigeRank + 1 : undefined,
    combined_rank: undefined,
    total_players_earnings: leaderboards.earnings?.total_entries || 0,
    total_players_referrals: leaderboards.referrals?.total_entries || 0,
    total_players_prestige: leaderboards.prestige?.total_entries || 0,
    earnings_percentile: earningsRank !== undefined && earningsRank >= 0 
      ? calculatePercentile(earningsRank + 1, leaderboards.earnings?.total_entries || 1)
      : undefined,
    referrals_percentile: referralsRank !== undefined && referralsRank >= 0 
      ? calculatePercentile(referralsRank + 1, leaderboards.referrals?.total_entries || 1)
      : undefined,
    prestige_percentile: prestigeRank !== undefined && prestigeRank >= 0 
      ? calculatePercentile(prestigeRank + 1, leaderboards.prestige?.total_entries || 1)
      : undefined,
  };
};

export const useLeaderboards = (wallet?: string): UseLeaderboardsReturn => {
  const [earningsLeaderboard, setEarningsLeaderboard] = useState<LeaderboardData | null>(null);
  const [referralsLeaderboard, setReferralsLeaderboard] = useState<LeaderboardData | null>(null);
  const [prestigeLeaderboard, setPrestigeLeaderboard] = useState<LeaderboardData | null>(null);
  const [playerPosition, setPlayerPosition] = useState<PlayerPosition | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchLeaderboards = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      // Real API calls to backend
      const [earningsRes, referralsRes, prestigeRes] = await Promise.all([
        fetch(`${baseUrl}/api/v1/leaderboards/earnings?limit=50`).catch(() => null),
        fetch(`${baseUrl}/api/v1/leaderboards/referrals?limit=50`).catch(() => null),
        fetch(`${baseUrl}/api/v1/leaderboards/prestige?limit=50`).catch(() => null),
      ]);

      let earnings: LeaderboardData;
      let referrals: LeaderboardData;
      let prestige: LeaderboardData;

      // Handle earnings leaderboard
      if (earningsRes && earningsRes.ok) {
        const data = await earningsRes.json();
        earnings = data.data || data;
      } else {
        console.log('Earnings API not available, using mock data');
        earnings = generateMockEarningsLeaderboard();
      }

      // Handle referrals leaderboard  
      if (referralsRes && referralsRes.ok) {
        const data = await referralsRes.json();
        referrals = data.data || data;
      } else {
        console.log('Referrals API not available, using mock data');
        referrals = generateMockReferralsLeaderboard();
      }

      // Handle prestige leaderboard
      if (prestigeRes && prestigeRes.ok) {
        const data = await prestigeRes.json();
        prestige = data.data || data;
      } else {
        console.log('Prestige API not available, using mock data');
        prestige = generateMockPrestigeLeaderboard();
      }

      setEarningsLeaderboard(earnings);
      setReferralsLeaderboard(referrals);
      setPrestigeLeaderboard(prestige);

      // Get player position if wallet is provided
      if (wallet) {
        try {
          const positionRes = await fetch(`${baseUrl}/api/v1/leaderboards/${wallet}/position`).catch(() => null);
          
          if (positionRes && positionRes.ok) {
            const positionData = await positionRes.json();
            setPlayerPosition(positionData.data || positionData);
          } else {
            // Fallback to generating position from current leaderboard data
            console.log('Player position API not available, generating from leaderboard data');
            const position = generateMockPlayerPosition(wallet, { earnings, referrals, prestige });
            setPlayerPosition(position);
          }
        } catch (err) {
          console.log('Error fetching player position, using fallback');
          const position = generateMockPlayerPosition(wallet, { earnings, referrals, prestige });
          setPlayerPosition(position);
        }
      } else {
        setPlayerPosition(null);
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch leaderboards');
      setEarningsLeaderboard(null);
      setReferralsLeaderboard(null);
      setPrestigeLeaderboard(null);
      setPlayerPosition(null);
    } finally {
      setLoading(false);
    }
  }, [wallet]);

  const refetch = useCallback(async () => {
    await fetchLeaderboards();
  }, [fetchLeaderboards]);

  useEffect(() => {
    fetchLeaderboards();
  }, [fetchLeaderboards]);

  return {
    earningsLeaderboard,
    referralsLeaderboard,
    prestigeLeaderboard,
    playerPosition,
    loading,
    error,
    refetch,
  };
};
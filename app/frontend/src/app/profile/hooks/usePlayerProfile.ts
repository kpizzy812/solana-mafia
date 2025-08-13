'use client';

import { useState, useEffect, useCallback } from 'react';

// Business type mapping based on on-chain data
const getBusinessTypeName = (businessType: number): string => {
  const businessTypes: { [key: number]: string } = {
    0: 'Casino',
    1: 'Laundromat', 
    2: 'Restaurant',
    3: 'Nightclub',
    4: 'Construction',
    5: 'Shipping',
  };
  return businessTypes[businessType] || `Business ${businessType}`;
};

interface PrestigeInfo {
  current_points: number;
  current_level: string;
  total_points_earned: number;
  points_to_next_level: number;
  progress_percentage: number;
  level_up_count: number;
}

interface BusinessBreakdown {
  business_type: string;
  count: number;
  total_value: number;
  total_earnings: number;
}

interface PlayerProfile {
  wallet: string;
  total_earned: number;
  total_invested: number;
  pending_earnings: number;
  active_businesses_count: number;
  prestige_info: PrestigeInfo;
  business_breakdown: BusinessBreakdown[];
  roi_percentage: number;
  last_activity_at: string;
  created_at: string;
  is_active: boolean;
}

interface UsePlayerProfileReturn {
  profile: PlayerProfile | null;
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

// Mock data generator for development
const generateMockProfile = (wallet: string): PlayerProfile => {
  const now = new Date();
  const createdAt = new Date(now.getTime() - (Math.random() * 30 * 24 * 60 * 60 * 1000));
  const lastActivity = new Date(now.getTime() - (Math.random() * 24 * 60 * 60 * 1000));
  
  const totalInvested = Math.floor(Math.random() * 100000000000) + 5000000000; // 5-105 SOL
  const totalEarned = Math.floor(totalInvested * (0.5 + Math.random() * 1.5)); // 50-200% ROI
  const currentPoints = Math.floor(Math.random() * 5000) + 100;
  
  const prestigeLevels = [
    { level: 'wannabe', minPoints: 0, maxPoints: 50 },
    { level: 'associate', minPoints: 50, maxPoints: 200 },
    { level: 'soldier', minPoints: 200, maxPoints: 800 },
    { level: 'capo', minPoints: 800, maxPoints: 3000 },
    { level: 'underboss', minPoints: 3000, maxPoints: 10000 },
    { level: 'boss', minPoints: 10000, maxPoints: Infinity },
  ];
  
  let currentLevel = 'wannabe';
  let pointsToNext = 50;
  let progressPercentage = 0;
  
  for (const level of prestigeLevels) {
    if (currentPoints >= level.minPoints && currentPoints < level.maxPoints) {
      currentLevel = level.level;
      pointsToNext = level.maxPoints === Infinity ? 0 : level.maxPoints - currentPoints;
      progressPercentage = level.maxPoints === Infinity ? 100 : 
        ((currentPoints - level.minPoints) / (level.maxPoints - level.minPoints)) * 100;
      break;
    }
  }

  const businessTypes = ['casino', 'laundromat', 'restaurant', 'nightclub', 'construction', 'shipping'];
  const businessBreakdown: BusinessBreakdown[] = businessTypes
    .filter(() => Math.random() > 0.5)
    .map(type => ({
      business_type: type,
      count: Math.floor(Math.random() * 5) + 1,
      total_value: Math.floor(Math.random() * 20000000000) + 1000000000,
      total_earnings: Math.floor(Math.random() * 10000000000) + 500000000,
    }));

  const activeBusiness = businessBreakdown.reduce((sum, b) => sum + b.count, 0);

  return {
    wallet,
    total_earned: totalEarned,
    total_invested: totalInvested,
    pending_earnings: Math.floor(Math.random() * 5000000000),
    active_businesses_count: activeBusiness,
    prestige_info: {
      current_points: currentPoints,
      current_level: currentLevel,
      total_points_earned: currentPoints + Math.floor(Math.random() * 10000),
      points_to_next_level: pointsToNext,
      progress_percentage: progressPercentage,
      level_up_count: Math.floor(Math.random() * 10),
    },
    business_breakdown: businessBreakdown,
    roi_percentage: ((totalEarned - totalInvested) / totalInvested) * 100,
    last_activity_at: lastActivity.toISOString(),
    created_at: createdAt.toISOString(),
    is_active: Math.random() > 0.1, // 90% chance of being active
  };
};

export const usePlayerProfile = (wallet?: string): UsePlayerProfileReturn => {
  const [profile, setProfile] = useState<PlayerProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProfile = useCallback(async () => {
    if (!wallet) {
      setProfile(null);
      setLoading(false);
      setError(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Real API call to backend
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/players/${wallet}`);
      
      if (!response.ok) {
        // If player not found or API error, fall back to mock data for development
        if (response.status === 404) {
          console.log('Player not found in API, using mock data for development');
          const mockProfile = generateMockProfile(wallet);
          setProfile(mockProfile);
          return;
        }
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      const apiData = data.data || data;
      
      // Adapt API data to expected profile structure
      const adaptedProfile: PlayerProfile = {
        wallet: apiData.wallet,
        total_earned: apiData.basic_stats?.total_earned || apiData.total_earned || 0,
        total_invested: apiData.basic_stats?.total_invested || apiData.total_invested || 0,
        pending_earnings: apiData.basic_stats?.pending_earnings || apiData.pending_earnings || 0,
        active_businesses_count: apiData.basic_stats?.active_businesses || apiData.active_businesses_count || 0,
        prestige_info: {
          current_points: apiData.prestige_info?.current_points || apiData.prestige_points || 0,
          current_level: apiData.prestige_info?.current_level || apiData.prestige_level || 'wannabe',
          total_points_earned: apiData.prestige_info?.total_points_earned || apiData.total_prestige_earned || 0,
          points_to_next_level: apiData.prestige_info?.points_to_next_level || apiData.points_to_next_level || 0,
          progress_percentage: apiData.prestige_info?.progress_percentage || apiData.prestige_progress_percentage || 0,
          level_up_count: apiData.prestige_info?.level_up_count || apiData.prestige_level_up_count || 0,
        },
        business_breakdown: [], // Will be populated from businesses API
        roi_percentage: apiData.roi_percentage || 0,
        last_activity_at: apiData.updated_at || apiData.last_activity_at || new Date().toISOString(),
        created_at: apiData.created_at || new Date().toISOString(),
        is_active: apiData.is_active !== false,
      };
      
      // Fetch businesses data separately if needed
      try {
        const businessResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/players/${wallet}/businesses`);
        if (businessResponse.ok) {
          const businessData = await businessResponse.json();
          const businesses = businessData.data?.businesses || [];
          
          // Group businesses by type for breakdown
          const breakdown: { [key: string]: BusinessBreakdown } = {};
          businesses.forEach((business: any) => {
            const typeKey = business.business_type?.toString() || 'unknown';
            if (!breakdown[typeKey]) {
              breakdown[typeKey] = {
                business_type: getBusinessTypeName(business.business_type),
                count: 0,
                total_value: 0,
                total_earnings: 0,
              };
            }
            breakdown[typeKey].count += 1;
            breakdown[typeKey].total_value += business.initial_cost || 0;
            breakdown[typeKey].total_earnings += business.total_earnings || 0;
          });
          
          adaptedProfile.business_breakdown = Object.values(breakdown);
        }
      } catch (businessError) {
        console.warn('Failed to fetch business data:', businessError);
      }
      
      setProfile(adaptedProfile);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch profile');
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, [wallet]);

  const refetch = useCallback(async () => {
    await fetchProfile();
  }, [fetchProfile]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  return {
    profile,
    loading,
    error,
    refetch,
  };
};
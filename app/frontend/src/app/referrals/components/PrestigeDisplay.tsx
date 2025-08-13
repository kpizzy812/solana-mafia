/**
 * PrestigeDisplay - Show user's prestige level and progress
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Award, TrendingUp, Star, Info, Loader2 } from 'lucide-react';
import { useWallet } from '@solana/wallet-adapter-react';
import { apiClient } from '@/lib/api';
import { useWebSocket } from '@/hooks/useWebSocket';

interface PrestigeData {
  wallet: string;
  current_points: number;
  current_level: string;
  level_info: {
    display_name_en: string;
    display_name_ru: string;
    description_en: string;
    description_ru: string;
    icon: string;
    color: string;
  };
  progress: {
    points_to_next: number | null;
    progress_percentage: number;
  };
  stats: {
    total_earned: number;
    level_up_count: number;
    daily_points: number;
    last_update: string | null;
  };
}

const levelIcons: Record<string, React.ReactNode> = {
  wannabe: <Star className="w-5 h-5" />,
  associate: <Award className="w-5 h-5" />,
  soldier: <TrendingUp className="w-5 h-5" />,
  capo: <Award className="w-5 h-5" />,
  underboss: <Award className="w-5 h-5" />,
  boss: <Award className="w-5 h-5" />
};

export function PrestigeDisplay() {
  const { publicKey } = useWallet();
  const [prestige, setPrestige] = useState<PrestigeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Handle WebSocket prestige updates
  const handlePrestigeUpdate = useCallback((data: any) => {
    console.log('💎 PrestigeDisplay received prestige update:', data);
    
    if (data.event === 'prestige_updated' && data.wallet === publicKey?.toString()) {
      setPrestige(current => {
        if (!current) return current;
        
        return {
          ...current,
          current_points: data.current_points || current.current_points,
          current_level: data.current_level || current.current_level,
          stats: {
            ...current.stats,
            total_earned: data.total_earned || current.stats.total_earned,
            daily_points: data.current_points - (current.stats.total_earned - current.stats.daily_points),
            last_update: new Date().toISOString()
          }
        };
      });
    }
  }, [publicKey]);

  // Connect to WebSocket for real-time updates
  useWebSocket({
    wallet: publicKey?.toString() || null,
    onPrestigeUpdate: handlePrestigeUpdate,
    enabled: !!publicKey
  });

  useEffect(() => {
    const fetchPrestige = async () => {
      if (!publicKey) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        // Note: This would call the prestige API endpoint
        const response = await apiClient.get(`/prestige/players/${publicKey.toString()}`);
        
        if (response.success && response.data) {
          setPrestige(response.data);
        } else {
          // Default prestige data for new players
          setPrestige({
            wallet: publicKey.toString(),
            current_points: 0,
            current_level: 'wannabe',
            level_info: {
              display_name_en: 'Wannabe',
              display_name_ru: 'Хочу быть',
              description_en: 'Just getting started in the mafia world',
              description_ru: 'Только начинаешь путь в мире мафии',
              icon: 'wannabe',
              color: '#64748b'
            },
            progress: {
              points_to_next: 50,
              progress_percentage: 0
            },
            stats: {
              total_earned: 0,
              level_up_count: 0,
              daily_points: 0,
              last_update: null
            }
          });
        }
      } catch (err) {
        console.error('Failed to fetch prestige data:', err);
        setError('Failed to load prestige information');
      } finally {
        setLoading(false);
      }
    };

    fetchPrestige();
  }, [publicKey]);

  if (loading) {
    return (
      <div className="bg-card border border-border rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Award className="w-5 h-5 text-primary" />
          <h2 className="text-xl font-semibold">Prestige Level</h2>
        </div>
        
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (error || !prestige) {
    return (
      <div className="bg-card border border-border rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Award className="w-5 h-5 text-primary" />
          <h2 className="text-xl font-semibold">Prestige Level</h2>
        </div>
        
        <div className="text-center py-8">
          <p className="text-muted-foreground">{error || 'No prestige data available'}</p>
        </div>
      </div>
    );
  }

  const levelIcon = levelIcons[prestige.current_level] || levelIcons.wannabe;

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      <div className="flex items-center gap-2 mb-6">
        <Award className="w-5 h-5 text-primary" />
        <h2 className="text-xl font-semibold">Prestige Level</h2>
        <div className="group relative">
          <Info className="w-4 h-4 text-muted-foreground cursor-help" />
          <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block bg-popover border border-border rounded-lg p-3 text-sm w-64 shadow-lg z-10">
            <p>Earn prestige points by:</p>
            <ul className="mt-2 space-y-1">
              <li>• Purchasing businesses</li>
              <li>• Upgrading businesses</li>
              <li>• Claiming earnings</li>
              <li>• Inviting referrals</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Current Level */}
      <div className="flex items-center gap-4 mb-6">
        <div 
          className="w-16 h-16 rounded-full flex items-center justify-center text-white"
          style={{ backgroundColor: prestige.level_info.color }}
        >
          {levelIcon}
        </div>
        
        <div>
          <h3 className="text-2xl font-bold" style={{ color: prestige.level_info.color }}>
            {prestige.level_info.display_name_en}
          </h3>
          <p className="text-sm text-muted-foreground">
            {prestige.level_info.description_en}
          </p>
          <div className="text-lg font-semibold mt-1">
            {prestige.current_points.toLocaleString()} points
          </div>
        </div>
      </div>

      {/* Progress to Next Level */}
      {prestige.progress.points_to_next !== null && (
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium">Progress to Next Level</span>
            <span className="text-sm text-muted-foreground">
              {prestige.progress.points_to_next} points needed
            </span>
          </div>
          
          <div className="w-full bg-muted rounded-full h-2">
            <div 
              className="h-2 rounded-full transition-all duration-300"
              style={{ 
                width: `${prestige.progress.progress_percentage}%`,
                backgroundColor: prestige.level_info.color 
              }}
            />
          </div>
          
          <div className="text-xs text-muted-foreground mt-1">
            {prestige.progress.progress_percentage.toFixed(1)}% complete
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-muted rounded-lg p-3">
          <div className="text-sm text-muted-foreground mb-1">Total Earned</div>
          <div className="text-lg font-semibold">
            {prestige.stats.total_earned.toLocaleString()}
          </div>
        </div>

        <div className="bg-muted rounded-lg p-3">
          <div className="text-sm text-muted-foreground mb-1">Level Ups</div>
          <div className="text-lg font-semibold">
            {prestige.stats.level_up_count}
          </div>
        </div>

        <div className="bg-muted rounded-lg p-3">
          <div className="text-sm text-muted-foreground mb-1">Today</div>
          <div className="text-lg font-semibold">
            {prestige.stats.daily_points}
          </div>
        </div>

        <div className="bg-muted rounded-lg p-3">
          <div className="text-sm text-muted-foreground mb-1">Rank</div>
          <div className="text-lg font-semibold capitalize">
            {prestige.current_level}
          </div>
        </div>
      </div>

      {/* Last Updated */}
      {prestige.stats.last_update && (
        <div className="mt-4 text-xs text-muted-foreground text-center">
          Last updated: {new Date(prestige.stats.last_update).toLocaleString()}
        </div>
      )}
    </div>
  );
}
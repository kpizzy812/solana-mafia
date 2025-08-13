'use client';

import React from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { UserIcon, RefreshIcon, TrophyIcon, CoinsIcon } from '@/components/ui/icons';

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

interface ProfileHeaderProps {
  profile?: PlayerProfile;
  loading: boolean;
  error?: string;
  language: 'en' | 'ru';
  onRefresh: () => void;
}

const prestigeLevels = {
  wannabe: { en: 'Wannabe', ru: 'Желающий', color: 'text-gray-400' },
  associate: { en: 'Associate', ru: 'Подручный', color: 'text-green-400' },
  soldier: { en: 'Soldier', ru: 'Солдат', color: 'text-blue-400' },
  capo: { en: 'Capo', ru: 'Капо', color: 'text-purple-400' },
  underboss: { en: 'Underboss', ru: 'Подбосс', color: 'text-orange-400' },
  boss: { en: 'Boss', ru: 'Босс', color: 'text-red-400' },
};

const formatWallet = (wallet: string): string => {
  if (!wallet) return '';
  return `${wallet.slice(0, 6)}...${wallet.slice(-6)}`;
};

const formatSOL = (lamports: number | undefined | null): string => {
  if (lamports == null) return '0.0000';
  return (lamports / 1000000000).toFixed(4);
};

const calculateNetProfit = (earned: number, invested: number): number => {
  return (earned || 0) - (invested || 0);
};

const calculateROI = (earned: number, invested: number): number => {
  if (!invested || invested === 0) return 0;
  return ((earned || 0) / invested) * 100;
};

const formatNumber = (num: number | undefined | null): string => {
  if (num == null) return '0';
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
};

const formatDate = (dateString: string, language: 'en' | 'ru'): string => {
  if (!dateString) return '';
  
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffHours < 1) {
    return language === 'ru' ? 'Только что' : 'Just now';
  } else if (diffHours < 24) {
    return language === 'ru' 
      ? `${diffHours} ч. назад` 
      : `${diffHours}h ago`;
  } else if (diffDays < 7) {
    return language === 'ru' 
      ? `${diffDays} дн. назад` 
      : `${diffDays}d ago`;
  } else {
    return date.toLocaleDateString(language === 'ru' ? 'ru-RU' : 'en-US');
  }
};

export const ProfileHeader: React.FC<ProfileHeaderProps> = ({
  profile,
  loading,
  error,
  language,
  onRefresh,
}) => {
  if (loading) {
    return (
      <Card className="p-6">
        <div className="animate-pulse">
          <div className="flex items-center space-x-4">
            <div className="w-16 h-16 bg-gray-600/30 rounded-full"></div>
            <div className="flex-1 space-y-2">
              <div className="h-6 bg-gray-600/30 rounded w-1/3"></div>
              <div className="h-4 bg-gray-600/20 rounded w-1/2"></div>
              <div className="h-4 bg-gray-600/20 rounded w-1/4"></div>
            </div>
            <div className="w-20 h-10 bg-gray-600/30 rounded"></div>
          </div>
          <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 bg-gray-600/20 rounded"></div>
                <div className="h-6 bg-gray-600/30 rounded"></div>
              </div>
            ))}
          </div>
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6 text-center">
        <div className="text-red-500 mb-4">
          {language === 'ru' ? 'Ошибка загрузки профиля' : 'Error loading profile'}
        </div>
        <Button onClick={onRefresh} variant="primary">
          <RefreshIcon className="w-4 h-4 mr-2" />
          {language === 'ru' ? 'Повторить' : 'Retry'}
        </Button>
      </Card>
    );
  }

  if (!profile) {
    return (
      <Card className="p-6 text-center">
        <UserIcon className="w-16 h-16 mx-auto text-gray-400 mb-4" />
        <div className="text-gray-500">
          {language === 'ru' ? 'Профиль не найден' : 'Profile not found'}
        </div>
      </Card>
    );
  }

  const prestigeLevel = prestigeLevels[profile.prestige_info.current_level as keyof typeof prestigeLevels];

  return (
    <Card className="p-6">
      {/* Header Section */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          {/* Avatar */}
          <div className="relative">
            <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center">
              <UserIcon className="w-8 h-8 text-white" />
            </div>
            {/* Status indicator */}
            <div className={`absolute -bottom-1 -right-1 w-5 h-5 rounded-full border-2 border-white ${
              profile.is_active ? 'bg-green-500' : 'bg-gray-400'
            }`}></div>
          </div>

          {/* User Info */}
          <div>
            <h1 className="text-xl font-bold text-white">
              {formatWallet(profile.wallet)}
            </h1>
            <div className={`font-semibold ${prestigeLevel?.color || 'text-gray-400'}`}>
              {prestigeLevel?.[language] || profile.prestige_info.current_level}
            </div>
            <div className="text-sm text-gray-400">
              {language === 'ru' ? 'Участник с' : 'Member since'} {formatDate(profile.created_at, language)}
            </div>
          </div>
        </div>

        {/* Refresh Button */}
        <Button 
          onClick={onRefresh} 
          variant="ghost" 
          size="sm"
          className="flex items-center space-x-2"
        >
          <RefreshIcon className="w-4 h-4" />
          <span className="hidden sm:inline">
            {language === 'ru' ? 'Обновить' : 'Refresh'}
          </span>
        </Button>
      </div>

      {/* Prestige Progress */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-200">
            {language === 'ru' ? 'Прогресс престижа' : 'Prestige Progress'}
          </span>
          <span className="text-sm text-gray-400">
            {formatNumber(profile.prestige_info.current_points)} / {
              formatNumber(profile.prestige_info.current_points + profile.prestige_info.points_to_next_level)
            }
          </span>
        </div>
        <div className="w-full bg-gray-700 rounded-full h-3">
          <div 
            className="bg-gradient-to-r from-purple-500 to-purple-600 h-3 rounded-full transition-all duration-300"
            style={{ width: `${Math.min(100, profile.prestige_info?.progress_percentage || 0)}%` }}
          ></div>
        </div>
        <div className="flex justify-between items-center mt-1">
          <span className="text-xs text-gray-400">
            {formatNumber(profile.prestige_info.points_to_next_level)} {language === 'ru' ? 'до следующего уровня' : 'to next level'}
          </span>
          <span className="text-xs text-gray-400">
            {(profile.prestige_info.progress_percentage || 0).toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Total Earned */}
        <div className="text-center p-4 bg-gradient-to-br from-green-500/10 to-green-600/10 border border-green-500/20 rounded-lg backdrop-blur-sm">
          <div className="flex items-center justify-center mb-2">
            <CoinsIcon className="w-5 h-5 text-green-400 mr-1" />
          </div>
          <div className="text-xs text-gray-400 mb-1">
            {language === 'ru' ? 'Заработано' : 'Total Earned'}
          </div>
          <div className="font-bold text-green-400 text-lg">
            {formatSOL(profile.total_earned)} SOL
          </div>
        </div>

        {/* Total Invested */}
        <div className="text-center p-4 bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/20 rounded-lg backdrop-blur-sm">
          <div className="flex items-center justify-center mb-2">
            <CoinsIcon className="w-5 h-5 text-blue-400 mr-1" />
          </div>
          <div className="text-xs text-gray-400 mb-1">
            {language === 'ru' ? 'Инвестировано' : 'Total Invested'}
          </div>
          <div className="font-bold text-blue-400 text-lg">
            {formatSOL(profile.total_invested)} SOL
          </div>
        </div>

        {/* Net Profit */}
        <div className="text-center p-4 bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/20 rounded-lg backdrop-blur-sm">
          <div className="flex items-center justify-center mb-2">
            <TrophyIcon className="w-5 h-5 text-purple-400 mr-1" />
          </div>
          <div className="text-xs text-gray-400 mb-1">
            {language === 'ru' ? 'Чист. прибыль' : 'Net Profit'}
          </div>
          <div className={`font-bold text-lg ${calculateNetProfit(profile.total_earned, profile.total_invested) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {calculateNetProfit(profile.total_earned, profile.total_invested) >= 0 ? '+' : ''}{formatSOL(calculateNetProfit(profile.total_earned, profile.total_invested))} SOL
          </div>
        </div>

        {/* Active Businesses */}
        <div className="text-center p-4 bg-gradient-to-br from-orange-500/10 to-orange-600/10 border border-orange-500/20 rounded-lg backdrop-blur-sm">
          <div className="flex items-center justify-center mb-2">
            <UserIcon className="w-5 h-5 text-orange-400 mr-1" />
          </div>
          <div className="text-xs text-gray-400 mb-1">
            {language === 'ru' ? 'Бизнесы' : 'Businesses'}
          </div>
          <div className="font-bold text-orange-400 text-lg">
            {profile.active_businesses_count}
          </div>
        </div>
      </div>

      {/* Pending Earnings */}
      {profile.pending_earnings > 0 && (
        <div className="mt-4 p-4 bg-gradient-to-r from-yellow-500/10 to-amber-500/10 border border-yellow-500/30 rounded-lg backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-yellow-400">
              {language === 'ru' ? 'Доступно для получения' : 'Available to claim'}
            </span>
            <span className="font-bold text-yellow-400 text-lg">
              {formatSOL(profile.pending_earnings)} SOL
            </span>
          </div>
        </div>
      )}

      {/* Last Activity */}
      <div className="mt-4 text-center text-xs text-gray-400">
        {language === 'ru' ? 'Последняя активность:' : 'Last activity:'} {formatDate(profile.last_activity_at, language)}
      </div>
    </Card>
  );
};
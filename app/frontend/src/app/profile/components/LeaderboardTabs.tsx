'use client';

import React, { useState } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { TrophyIcon, UsersIcon, StatsIcon, RefreshIcon } from '@/components/ui/icons';

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

interface LeaderboardTabsProps {
  earningsLeaderboard?: LeaderboardData;
  referralsLeaderboard?: LeaderboardData;
  prestigeLeaderboard?: LeaderboardData;
  playerPosition?: PlayerPosition;
  loading: boolean;
  error?: string;
  language: 'en' | 'ru';
  currentWallet?: string;
  onRefresh: () => void;
}

type TabType = 'earnings' | 'referrals' | 'prestige';

interface TabItem {
  id: TabType;
  label: {
    en: string;
    ru: string;
  };
  icon: React.ComponentType<{ className?: string }>;
}

const leaderboardTabs: TabItem[] = [
  {
    id: 'earnings',
    label: { en: 'Earnings', ru: 'Заработок' },
    icon: TrophyIcon,
  },
  {
    id: 'referrals',
    label: { en: 'Referrals', ru: 'Рефералы' },
    icon: UsersIcon,
  },
  {
    id: 'prestige',
    label: { en: 'Prestige', ru: 'Престиж' },
    icon: StatsIcon,
  },
];

const prestigeLevels = {
  wannabe: { en: 'Wannabe', ru: 'Желающий' },
  associate: { en: 'Associate', ru: 'Подручный' },
  soldier: { en: 'Soldier', ru: 'Солдат' },
  capo: { en: 'Capo', ru: 'Капо' },
  underboss: { en: 'Underboss', ru: 'Подбосс' },
  boss: { en: 'Boss', ru: 'Босс' },
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

const formatWallet = (wallet: string): string => {
  if (!wallet) return '';
  return `${wallet.slice(0, 4)}...${wallet.slice(-4)}`;
};

const formatSOL = (lamports: number | undefined | null): string => {
  if (lamports == null) return '0.0000';
  return (lamports / 1000000000).toFixed(4);
};

export const LeaderboardTabs: React.FC<LeaderboardTabsProps> = ({
  earningsLeaderboard,
  referralsLeaderboard,
  prestigeLeaderboard,
  playerPosition,
  loading,
  error,
  language,
  currentWallet,
  onRefresh,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('earnings');

  if (loading) {
    return (
      <Card className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="flex space-x-4 border-b border-gray-700">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-10 bg-gray-600/30 rounded w-24"></div>
            ))}
          </div>
          <div className="space-y-3">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-16 bg-gray-600/20 rounded"></div>
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
          {language === 'ru' ? 'Ошибка загрузки лидербордов' : 'Error loading leaderboards'}
        </div>
        <Button onClick={onRefresh} variant="primary">
          <RefreshIcon className="w-4 h-4 mr-2" />
          {language === 'ru' ? 'Повторить' : 'Retry'}
        </Button>
      </Card>
    );
  }

  const renderPlayerPosition = () => {
    if (!playerPosition || !currentWallet) return null;

    const currentRank = activeTab === 'earnings' ? playerPosition.earnings_rank :
                       activeTab === 'referrals' ? playerPosition.referrals_rank :
                       playerPosition.prestige_rank;

    const currentPercentile = activeTab === 'earnings' ? playerPosition.earnings_percentile :
                             activeTab === 'referrals' ? playerPosition.referrals_percentile :
                             playerPosition.prestige_percentile;

    if (!currentRank) return null;

    return (
      <Card className="p-4 mb-4 bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30">
        <div className="text-center">
          <div className="text-lg font-bold text-blue-400">
            {language === 'ru' ? 'Ваша позиция' : 'Your Position'}
          </div>
          <div className="text-2xl font-bold text-white">
            #{currentRank}
          </div>
          {currentPercentile && (
            <div className="text-sm text-blue-300">
              {language === 'ru' ? 'Топ' : 'Top'} {(100 - (currentPercentile || 0)).toFixed(1)}%
            </div>
          )}
        </div>
      </Card>
    );
  };

  const renderEarningsLeaderboard = () => {
    if (!earningsLeaderboard?.leaderboard) return null;

    return (
      <div className="space-y-3">
        {earningsLeaderboard.leaderboard.map((entry: EarningsLeaderboardEntry, index) => (
          <Card 
            key={entry.wallet} 
            className={`p-4 ${entry.wallet === currentWallet ? 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 border-yellow-500/50' : 'bg-gray-800/50 border-gray-700/50'} hover:bg-gray-700/50 transition-colors`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                    entry.rank === 1 ? 'bg-yellow-500 text-white' :
                    entry.rank === 2 ? 'bg-gray-400 text-white' :
                    entry.rank === 3 ? 'bg-amber-600 text-white' :
                    'bg-gray-200 text-gray-700'
                  }`}>
                    {entry.rank}
                  </div>
                </div>
                <div>
                  <div className="font-semibold text-white">{formatWallet(entry.wallet)}</div>
                  <div className="text-sm text-gray-400">
                    {prestigeLevels[entry.prestige_level as keyof typeof prestigeLevels]?.[language] || entry.prestige_level}
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="font-bold text-green-600">
                  {formatSOL(entry.total_earned)} SOL
                </div>
                <div className="text-sm text-gray-400">
                  ROI: {(entry.roi_percentage || 0).toFixed(1)}%
                </div>
                <div className="text-xs text-gray-400">
                  {entry.active_businesses} {language === 'ru' ? 'бизнесов' : 'businesses'}
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  };

  const renderReferralsLeaderboard = () => {
    if (!referralsLeaderboard?.leaderboard) return null;

    return (
      <div className="space-y-3">
        {referralsLeaderboard.leaderboard.map((entry: ReferralLeaderboardEntry) => (
          <Card 
            key={entry.wallet} 
            className={`p-4 ${entry.wallet === currentWallet ? 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 border-yellow-500/50' : 'bg-gray-800/50 border-gray-700/50'} hover:bg-gray-700/50 transition-colors`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                    entry.rank === 1 ? 'bg-yellow-500 text-white' :
                    entry.rank === 2 ? 'bg-gray-400 text-white' :
                    entry.rank === 3 ? 'bg-amber-600 text-white' :
                    'bg-gray-200 text-gray-700'
                  }`}>
                    {entry.rank}
                  </div>
                </div>
                <div>
                  <div className="font-semibold text-white">{formatWallet(entry.wallet)}</div>
                  <div className="text-sm text-gray-400">
                    {prestigeLevels[entry.prestige_level as keyof typeof prestigeLevels]?.[language] || entry.prestige_level}
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="font-bold text-blue-600">
                  {formatNumber(entry.total_referrals)} {language === 'ru' ? 'рефералов' : 'referrals'}
                </div>
                <div className="text-sm text-green-600">
                  {formatSOL(entry.total_referral_earnings)} SOL
                </div>
                <div className="text-xs text-gray-400">
                  L1: {entry.level_1_referrals} | L2: {entry.level_2_referrals} | L3: {entry.level_3_referrals}
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  };

  const renderPrestigeLeaderboard = () => {
    if (!prestigeLeaderboard?.leaderboard) return null;

    return (
      <div className="space-y-3">
        {prestigeLeaderboard.leaderboard.map((entry: PrestigeLeaderboardEntry) => (
          <Card 
            key={entry.wallet} 
            className={`p-4 ${entry.wallet === currentWallet ? 'bg-gradient-to-r from-yellow-500/20 to-amber-500/20 border-yellow-500/50' : 'bg-gray-800/50 border-gray-700/50'} hover:bg-gray-700/50 transition-colors`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-sm ${
                    entry.rank === 1 ? 'bg-yellow-500 text-white' :
                    entry.rank === 2 ? 'bg-gray-400 text-white' :
                    entry.rank === 3 ? 'bg-amber-600 text-white' :
                    'bg-gray-200 text-gray-700'
                  }`}>
                    {entry.rank}
                  </div>
                </div>
                <div>
                  <div className="font-semibold text-white">{formatWallet(entry.wallet)}</div>
                  <div className="text-sm text-purple-400 font-medium">
                    {prestigeLevels[entry.current_level as keyof typeof prestigeLevels]?.[language] || entry.current_level}
                  </div>
                </div>
              </div>
              <div className="text-right">
                <div className="font-bold text-purple-400">
                  {formatNumber(entry.current_points)} {language === 'ru' ? 'очков' : 'points'}
                </div>
                <div className="text-sm text-gray-400">
                  {language === 'ru' ? 'Всего заработано:' : 'Total earned:'} {formatNumber(entry.total_points_earned)}
                </div>
                <div className="text-xs text-gray-400">
                  {language === 'ru' ? 'Повышений:' : 'Level ups:'} {entry.level_up_count}
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  };

  const currentData = activeTab === 'earnings' ? earningsLeaderboard :
                     activeTab === 'referrals' ? referralsLeaderboard :
                     prestigeLeaderboard;

  return (
    <div className="space-y-6">
      {/* Player Position */}
      {renderPlayerPosition()}

      {/* Tab Navigation */}
      <Card className="p-1">
        <div className="flex space-x-1 overflow-x-auto">
          {leaderboardTabs.map((tab) => {
            const isActive = activeTab === tab.id;
            const IconComponent = tab.icon;
            
            return (
              <Button
                key={tab.id}
                variant={isActive ? "primary" : "ghost"}
                size="sm"
                onClick={() => setActiveTab(tab.id)}
                className={`
                  flex-1 min-w-0 flex items-center justify-center space-x-2 
                  transition-all duration-200
                  ${isActive 
                    ? 'bg-primary text-primary-foreground shadow-sm' 
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent'
                  }
                `}
              >
                <IconComponent className="w-4 h-4 shrink-0" />
                <span className="truncate text-xs md:text-sm font-medium">
                  {tab.label[language]}
                </span>
              </Button>
            );
          })}
        </div>
      </Card>

      {/* Leaderboard Content */}
      <div className="min-h-[400px]">
        {/* Header with refresh button */}
        <div className="flex justify-between items-center mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">
              {leaderboardTabs.find(tab => tab.id === activeTab)?.label[language]}
            </h3>
            {currentData && (
              <p className="text-sm text-gray-400">
                {language === 'ru' ? 'Всего записей:' : 'Total entries:'} {currentData.total_entries}
              </p>
            )}
          </div>
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

        {/* Leaderboard Tables */}
        {activeTab === 'earnings' && renderEarningsLeaderboard()}
        {activeTab === 'referrals' && renderReferralsLeaderboard()}
        {activeTab === 'prestige' && renderPrestigeLeaderboard()}

        {/* Empty State */}
        {!currentData?.leaderboard?.length && (
          <Card className="p-8 text-center bg-gray-800/50 border-gray-700/50">
            <div className="text-gray-400">
              {language === 'ru' ? 'Нет данных для отображения' : 'No data available'}
            </div>
          </Card>
        )}

        {/* Pagination Info */}
        {currentData?.pagination && currentData.pagination.total > 0 && (
          <div className="mt-4 text-center text-sm text-gray-400">
            {language === 'ru' ? 'Показано' : 'Showing'} {currentData.pagination.offset + 1}-
            {Math.min(currentData.pagination.offset + currentData.pagination.limit, currentData.pagination.total)} 
            {language === 'ru' ? ' из ' : ' of '} {currentData.pagination.total}
          </div>
        )}
      </div>
    </div>
  );
};
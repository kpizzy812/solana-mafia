'use client';

import React from 'react';
import { Card } from '@/components/ui/Card';
import { TrophyIcon, CoinsIcon, UsersIcon, StatsIcon } from '@/components/ui/icons';

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

interface ProfileStatsProps {
  profile?: PlayerProfile;
  playerPosition?: PlayerPosition;
  loading: boolean;
  language: 'en' | 'ru';
  detailed?: boolean;
}

const formatNumber = (num: number | undefined | null): string => {
  if (num == null) return '0';
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M';
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K';
  }
  return num.toString();
};

const formatSOL = (lamports: number | undefined | null): string => {
  if (lamports == null) return '0.0000';
  return (lamports / 1000000000).toFixed(4);
};

const businessTypeNames = {
  casino: { en: 'Casino', ru: 'Казино' },
  laundromat: { en: 'Laundromat', ru: 'Прачечная' },
  restaurant: { en: 'Restaurant', ru: 'Ресторан' },
  nightclub: { en: 'Nightclub', ru: 'Ночной клуб' },
  construction: { en: 'Construction', ru: 'Стройка' },
  shipping: { en: 'Shipping', ru: 'Доставка' },
};

export const ProfileStats: React.FC<ProfileStatsProps> = ({
  profile,
  playerPosition,
  loading,
  language,
  detailed = false,
}) => {
  if (loading) {
    return (
      <div className="space-y-6">
        {[1, 2, 3].map((i) => (
          <Card key={i} className="p-6">
            <div className="animate-pulse space-y-4">
              <div className="h-6 bg-gray-600/30 rounded w-1/3"></div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {[1, 2, 3].map((j) => (
                  <div key={j} className="space-y-2">
                    <div className="h-4 bg-gray-600/20 rounded"></div>
                    <div className="h-6 bg-gray-600/30 rounded"></div>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  if (!profile) {
    return (
      <Card className="p-6 text-center bg-gray-800/50 border-gray-700/50">
        <div className="text-gray-400">
          {language === 'ru' ? 'Нет данных для отображения' : 'No data available'}
        </div>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Ranking Statistics */}
      {playerPosition && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center text-white">
            <TrophyIcon className="w-5 h-5 mr-2 text-yellow-400" />
            {language === 'ru' ? 'Рейтинг' : 'Rankings'}
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Earnings Rank */}
            <div className="text-center p-4 bg-gradient-to-br from-green-500/10 to-green-600/10 border border-green-500/20 rounded-lg backdrop-blur-sm">
              <div className="text-2xl font-bold text-green-400">
                {playerPosition.earnings_rank ? `#${playerPosition.earnings_rank}` : '-'}
              </div>
              <div className="text-sm text-gray-400">
                {language === 'ru' ? 'По заработку' : 'Earnings Rank'}
              </div>
              {playerPosition.earnings_percentile && (
                <div className="text-xs text-green-300">
                  {language === 'ru' ? 'Топ' : 'Top'} {(100 - (playerPosition.earnings_percentile || 0)).toFixed(1)}%
                </div>
              )}
            </div>

            {/* Referrals Rank */}
            <div className="text-center p-4 bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/20 rounded-lg backdrop-blur-sm">
              <div className="text-2xl font-bold text-blue-400">
                {playerPosition.referrals_rank ? `#${playerPosition.referrals_rank}` : '-'}
              </div>
              <div className="text-sm text-gray-400">
                {language === 'ru' ? 'По рефералам' : 'Referrals Rank'}
              </div>
              {playerPosition.referrals_percentile && (
                <div className="text-xs text-blue-300">
                  {language === 'ru' ? 'Топ' : 'Top'} {(100 - (playerPosition.referrals_percentile || 0)).toFixed(1)}%
                </div>
              )}
            </div>

            {/* Prestige Rank */}
            <div className="text-center p-4 bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/20 rounded-lg backdrop-blur-sm">
              <div className="text-2xl font-bold text-purple-400">
                {playerPosition.prestige_rank ? `#${playerPosition.prestige_rank}` : '-'}
              </div>
              <div className="text-sm text-gray-400">
                {language === 'ru' ? 'По престижу' : 'Prestige Rank'}
              </div>
              {playerPosition.prestige_percentile && (
                <div className="text-xs text-purple-300">
                  {language === 'ru' ? 'Топ' : 'Top'} {(100 - (playerPosition.prestige_percentile || 0)).toFixed(1)}%
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* Financial Statistics */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center text-white">
          <CoinsIcon className="w-5 h-5 mr-2 text-green-400" />
          {language === 'ru' ? 'Финансовая статистика' : 'Financial Statistics'}
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Total Earned */}
          <div className="text-center p-3 bg-gradient-to-br from-green-500/10 to-green-600/10 border border-green-500/20 rounded-lg backdrop-blur-sm">
            <div className="text-lg font-bold text-green-400">
              {formatSOL(profile.total_earned)}
            </div>
            <div className="text-xs text-gray-400">
              {language === 'ru' ? 'Заработано (SOL)' : 'Earned (SOL)'}
            </div>
          </div>

          {/* Total Invested */}
          <div className="text-center p-3 bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/20 rounded-lg backdrop-blur-sm">
            <div className="text-lg font-bold text-blue-400">
              {formatSOL(profile.total_invested)}
            </div>
            <div className="text-xs text-gray-400">
              {language === 'ru' ? 'Инвестировано (SOL)' : 'Invested (SOL)'}
            </div>
          </div>

          {/* Net Profit */}
          <div className="text-center p-3 bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/20 rounded-lg backdrop-blur-sm">
            <div className={`text-lg font-bold ${
              (profile.total_earned - profile.total_invested) >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {((profile.total_earned - profile.total_invested) >= 0 ? '+' : '')}{formatSOL(profile.total_earned - profile.total_invested)}
            </div>
            <div className="text-xs text-gray-400">
              {language === 'ru' ? 'Чистая прибыль' : 'Net Profit'}
            </div>
          </div>

          {/* ROI */}
          <div className="text-center p-3 bg-gradient-to-br from-orange-500/10 to-orange-600/10 border border-orange-500/20 rounded-lg backdrop-blur-sm">
            <div className={`text-lg font-bold ${
              (profile.roi_percentage || 0) >= 0 ? 'text-green-400' : 'text-red-400'
            }`}>
              {((profile.roi_percentage || 0) >= 0 ? '+' : '')}{(profile.roi_percentage || 0).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-400">
              ROI
            </div>
          </div>
        </div>
      </Card>

      {/* Business Portfolio */}
      {profile.business_breakdown && profile.business_breakdown.length > 0 && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center text-white">
            <UsersIcon className="w-5 h-5 mr-2 text-orange-400" />
            {language === 'ru' ? 'Портфель бизнесов' : 'Business Portfolio'}
          </h3>
          <div className="space-y-3">
            {profile.business_breakdown.map((business, index) => (
              <div key={index} className="flex items-center justify-between p-3 bg-gray-800/50 border border-gray-700/50 rounded-lg">
                <div>
                  <div className="font-medium text-white">
                    {businessTypeNames[business.business_type as keyof typeof businessTypeNames]?.[language] || business.business_type}
                  </div>
                  <div className="text-sm text-gray-400">
                    {formatNumber(business.count)} {language === 'ru' ? 'шт.' : 'units'}
                  </div>
                </div>
                <div className="text-right">
                  <div className="font-semibold text-green-400">
                    {formatSOL(business.total_earnings)} SOL
                  </div>
                  <div className="text-sm text-gray-400">
                    {language === 'ru' ? 'Стоимость:' : 'Value:'} {formatSOL(business.total_value)} SOL
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Prestige Details */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center text-white">
          <StatsIcon className="w-5 h-5 mr-2 text-purple-400" />
          {language === 'ru' ? 'Детали престижа' : 'Prestige Details'}
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {/* Current Points */}
          <div className="text-center p-3 bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/20 rounded-lg backdrop-blur-sm">
            <div className="text-lg font-bold text-purple-400">
              {formatNumber(profile.prestige_info.current_points)}
            </div>
            <div className="text-xs text-gray-400">
              {language === 'ru' ? 'Текущие очки' : 'Current Points'}
            </div>
          </div>

          {/* Total Earned */}
          <div className="text-center p-3 bg-gradient-to-br from-indigo-500/10 to-indigo-600/10 border border-indigo-500/20 rounded-lg backdrop-blur-sm">
            <div className="text-lg font-bold text-indigo-400">
              {formatNumber(profile.prestige_info.total_points_earned)}
            </div>
            <div className="text-xs text-gray-400">
              {language === 'ru' ? 'Всего заработано' : 'Total Earned'}
            </div>
          </div>

          {/* Level Ups */}
          <div className="text-center p-3 bg-gradient-to-br from-pink-500/10 to-pink-600/10 border border-pink-500/20 rounded-lg backdrop-blur-sm">
            <div className="text-lg font-bold text-pink-400">
              {profile.prestige_info.level_up_count}
            </div>
            <div className="text-xs text-gray-400">
              {language === 'ru' ? 'Повышений' : 'Level Ups'}
            </div>
          </div>

          {/* To Next Level */}
          <div className="text-center p-3 bg-gradient-to-br from-cyan-500/10 to-cyan-600/10 border border-cyan-500/20 rounded-lg backdrop-blur-sm">
            <div className="text-lg font-bold text-cyan-400">
              {formatNumber(profile.prestige_info.points_to_next_level)}
            </div>
            <div className="text-xs text-gray-400">
              {language === 'ru' ? 'До следующего' : 'To Next Level'}
            </div>
          </div>
        </div>

        {/* Progress Bar */}
        <div className="mt-4">
          <div className="flex justify-between items-center mb-2">
            <span className="text-sm font-medium text-gray-200">
              {language === 'ru' ? 'Прогресс до следующего уровня' : 'Progress to Next Level'}
            </span>
            <span className="text-sm text-gray-400">
              {(profile.prestige_info.progress_percentage || 0).toFixed(1)}%
            </span>
          </div>
          <div className="w-full bg-gray-700 rounded-full h-3">
            <div 
              className="bg-gradient-to-r from-purple-500 to-purple-600 h-3 rounded-full transition-all duration-300"
              style={{ width: `${Math.min(100, profile.prestige_info?.progress_percentage || 0)}%` }}
            ></div>
          </div>
        </div>
      </Card>

      {detailed && (
        <Card className="p-6">
          <h3 className="text-lg font-semibold mb-4 text-white">
            {language === 'ru' ? 'Дополнительная статистика' : 'Additional Statistics'}
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-400">
                {language === 'ru' ? 'Дата регистрации:' : 'Join Date:'}
              </span>
              <div className="font-medium text-white">
                {new Date(profile.created_at).toLocaleDateString(language === 'ru' ? 'ru-RU' : 'en-US')}
              </div>
            </div>
            <div>
              <span className="text-gray-400">
                {language === 'ru' ? 'Последняя активность:' : 'Last Activity:'}
              </span>
              <div className="font-medium text-white">
                {new Date(profile.last_activity_at).toLocaleDateString(language === 'ru' ? 'ru-RU' : 'en-US')}
              </div>
            </div>
            <div>
              <span className="text-gray-400">
                {language === 'ru' ? 'Статус:' : 'Status:'}
              </span>
              <div className={`font-medium ${profile.is_active ? 'text-green-400' : 'text-red-400'}`}>
                {profile.is_active 
                  ? (language === 'ru' ? 'Активен' : 'Active')
                  : (language === 'ru' ? 'Неактивен' : 'Inactive')
                }
              </div>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};
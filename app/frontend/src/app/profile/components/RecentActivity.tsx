'use client';

import React, { useState, useEffect } from 'react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StatsIcon, CoinsIcon, UsersIcon, TrophyIcon, RefreshIcon, UserIcon } from '@/components/ui/icons';

interface ActivityItem {
  id: string;
  type: string; // Allow any string for flexibility with backend event types
  activity_type?: string; // Backend uses this field
  timestamp: string;
  amount?: number;
  business_type?: string;
  description: string;
  transaction_hash?: string;
  transaction_signature?: string; // Backend uses this field
  metadata?: any; // Backend event metadata
}

interface RecentActivityProps {
  wallet?: string;
  language: 'en' | 'ru';
  detailed?: boolean;
}

// Universal mapping for all possible backend event types
const activityTypeIcons: { [key: string]: React.ComponentType<{ className?: string }> } = {
  // Legacy frontend types
  business_purchase: CoinsIcon,
  business_upgrade: TrophyIcon,
  business_sale: CoinsIcon,
  earnings_claim: CoinsIcon,
  referral_bonus: UsersIcon,
  prestige_gain: StatsIcon,
  
  // Backend event types (snake_case from database)
  business_created: CoinsIcon,
  business_created_in_slot: CoinsIcon,
  business_upgraded: TrophyIcon,
  business_upgraded_in_slot: TrophyIcon,
  business_sold: CoinsIcon,
  business_sold_from_slot: CoinsIcon,
  earnings_updated: CoinsIcon,
  earnings_claimed: CoinsIcon,
  referral_bonus_added: UsersIcon,
  prestige_level_up: StatsIcon,
  player_created: UserIcon,
  slot_unlocked: TrophyIcon,
  premium_slot_purchased: TrophyIcon,
};

const activityTypeColors: { [key: string]: string } = {
  // Legacy frontend types
  business_purchase: 'text-blue-400 bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/20',
  business_upgrade: 'text-purple-400 bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/20',
  business_sale: 'text-green-400 bg-gradient-to-br from-green-500/10 to-green-600/10 border border-green-500/20',
  earnings_claim: 'text-green-400 bg-gradient-to-br from-green-500/10 to-green-600/10 border border-green-500/20',
  referral_bonus: 'text-orange-400 bg-gradient-to-br from-orange-500/10 to-orange-600/10 border border-orange-500/20',
  prestige_gain: 'text-indigo-400 bg-gradient-to-br from-indigo-500/10 to-indigo-600/10 border border-indigo-500/20',
  
  // Backend event types
  business_created: 'text-blue-400 bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/20',
  business_created_in_slot: 'text-blue-400 bg-gradient-to-br from-blue-500/10 to-blue-600/10 border border-blue-500/20',
  business_upgraded: 'text-purple-400 bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/20',
  business_upgraded_in_slot: 'text-purple-400 bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/20',
  business_sold: 'text-green-400 bg-gradient-to-br from-green-500/10 to-green-600/10 border border-green-500/20',
  business_sold_from_slot: 'text-green-400 bg-gradient-to-br from-green-500/10 to-green-600/10 border border-green-500/20',
  earnings_updated: 'text-yellow-400 bg-gradient-to-br from-yellow-500/10 to-yellow-600/10 border border-yellow-500/20',
  earnings_claimed: 'text-green-400 bg-gradient-to-br from-green-500/10 to-green-600/10 border border-green-500/20',
  referral_bonus_added: 'text-orange-400 bg-gradient-to-br from-orange-500/10 to-orange-600/10 border border-orange-500/20',
  prestige_level_up: 'text-indigo-400 bg-gradient-to-br from-indigo-500/10 to-indigo-600/10 border border-indigo-500/20',
  player_created: 'text-cyan-400 bg-gradient-to-br from-cyan-500/10 to-cyan-600/10 border border-cyan-500/20',
  slot_unlocked: 'text-purple-400 bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/20',
  premium_slot_purchased: 'text-purple-400 bg-gradient-to-br from-purple-500/10 to-purple-600/10 border border-purple-500/20',
};

const businessTypeNames = {
  casino: { en: 'Casino', ru: 'Казино' },
  laundromat: { en: 'Laundromat', ru: 'Прачечная' },
  restaurant: { en: 'Restaurant', ru: 'Ресторан' },
  nightclub: { en: 'Nightclub', ru: 'Ночной клуб' },
  construction: { en: 'Construction', ru: 'Стройка' },
  shipping: { en: 'Shipping', ru: 'Доставка' },
};

const formatSOL = (lamports: number | undefined | null): string => {
  if (lamports == null) return '0.0000';
  return (lamports / 1000000000).toFixed(4);
};

const formatDate = (dateString: string, language: 'en' | 'ru'): string => {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMinutes < 1) {
    return language === 'ru' ? 'Только что' : 'Just now';
  } else if (diffMinutes < 60) {
    return language === 'ru' 
      ? `${diffMinutes} мин. назад` 
      : `${diffMinutes}m ago`;
  } else if (diffHours < 24) {
    return language === 'ru' 
      ? `${diffHours} ч. назад` 
      : `${diffHours}h ago`;
  } else if (diffDays < 7) {
    return language === 'ru' 
      ? `${diffDays} дн. назад` 
      : `${diffDays}d ago`;
  } else {
    return date.toLocaleDateString(language === 'ru' ? 'ru-RU' : 'en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }
};

const formatTransactionHash = (hash: string): string => {
  if (!hash) return '';
  return `${hash.slice(0, 8)}...${hash.slice(-8)}`;
};

const getActivityDescription = (activity: ActivityItem, language: 'en' | 'ru'): string => {
  // Get activity type from either field
  const activityType = activity.activity_type || activity.type;
  
  // Get business name from metadata if available
  const businessTypeNum = activity.metadata?.business_type;
  const businessTypeMap = ['casino', 'laundromat', 'restaurant', 'nightclub', 'construction', 'shipping'];
  const businessTypeKey = businessTypeNum !== undefined ? businessTypeMap[businessTypeNum] : activity.business_type;
  
  const businessName = businessTypeKey
    ? businessTypeNames[businessTypeKey as keyof typeof businessTypeNames]?.[language] || businessTypeKey
    : '';

  switch (activityType?.toLowerCase()) {
    // Business creation events
    case 'business_created':
    case 'business_created_in_slot':
    case 'business_purchase':
      return language === 'ru' 
        ? `Куплен бизнес${businessName ? ': ' + businessName : ''}`
        : `Purchased business${businessName ? ': ' + businessName : ''}`;
    
    // Business upgrade events
    case 'business_upgraded':
    case 'business_upgraded_in_slot':
    case 'business_upgrade':
      return language === 'ru' 
        ? `Улучшен бизнес${businessName ? ': ' + businessName : ''}`
        : `Upgraded business${businessName ? ': ' + businessName : ''}`;
    
    // Business sale events
    case 'business_sold':
    case 'business_sold_from_slot':
    case 'business_sale':
      return language === 'ru' 
        ? `Продан бизнес${businessName ? ': ' + businessName : ''}`
        : `Sold business${businessName ? ': ' + businessName : ''}`;
    
    // Earnings events
    case 'earnings_updated':
      return language === 'ru' 
        ? 'Обновлена прибыль'
        : 'Earnings updated';
    case 'earnings_claimed':
    case 'earnings_claim':
      return language === 'ru' 
        ? 'Получена прибыль'
        : 'Claimed earnings';
    
    // Referral events
    case 'referral_bonus_added':
    case 'referral_bonus':
      return language === 'ru' 
        ? 'Получен реферальный бонус'
        : 'Received referral bonus';
    
    // Prestige events
    case 'prestige_level_up':
    case 'prestige_gain':
      return language === 'ru' 
        ? 'Повышение престижа'
        : 'Prestige level up';
    
    // Player events
    case 'player_created':
      return language === 'ru' 
        ? 'Игрок создан'
        : 'Player created';
    
    // Slot events
    case 'slot_unlocked':
      return language === 'ru' 
        ? 'Слот разблокирован'
        : 'Slot unlocked';
    case 'premium_slot_purchased':
      return language === 'ru' 
        ? 'Куплен премиум слот'
        : 'Purchased premium slot';
    
    default:
      return activity.description || (language === 'ru' ? 'Неизвестная активность' : 'Unknown activity');
  }
};

// Mock data for demonstration - in real app this would come from API
const generateMockActivity = (wallet: string): ActivityItem[] => {
  const activities: ActivityItem[] = [];
  const now = new Date();
  
  for (let i = 0; i < 15; i++) {
    const timestamp = new Date(now.getTime() - (i * 2 * 60 * 60 * 1000)).toISOString();
    const types: ActivityItem['type'][] = ['business_purchase', 'business_upgrade', 'earnings_claim', 'referral_bonus', 'prestige_gain'];
    const type = types[Math.floor(Math.random() * types.length)];
    const businessTypes = ['casino', 'laundromat', 'restaurant', 'nightclub'];
    
    activities.push({
      id: `activity_${i}`,
      type,
      timestamp,
      amount: type.includes('business') || type === 'earnings_claim' ? Math.floor(Math.random() * 50000000000) + 1000000000 : Math.floor(Math.random() * 100) + 10,
      business_type: ['business_purchase', 'business_upgrade', 'business_sale'].includes(type) 
        ? businessTypes[Math.floor(Math.random() * businessTypes.length)]
        : undefined,
      description: '',
      transaction_hash: `tx_${Math.random().toString(36).substring(2, 15)}`,
    });
  }
  
  return activities;
};

export const RecentActivity: React.FC<RecentActivityProps> = ({
  wallet,
  language,
  detailed = false,
}) => {
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadActivities = async () => {
    if (!wallet) return;
    
    setLoading(true);
    setError(null);
    
    try {
      // Real API call to backend
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${baseUrl}/api/v1/players/${wallet}/activity?limit=20`).catch(() => null);
      
      if (response && response.ok) {
        const data = await response.json();
        const backendActivities = data.data || data.activities || [];
        
        // Transform backend activities to match our interface
        const transformedActivities = backendActivities.map((activity: any, index: number) => ({
          id: activity.id || `activity_${index}`,
          type: activity.activity_type || activity.type || 'unknown',
          activity_type: activity.activity_type,
          timestamp: activity.timestamp,
          amount: activity.metadata?.cost || activity.metadata?.total_paid || activity.amount,
          business_type: activity.metadata?.business_type,
          description: activity.description || '',
          transaction_hash: activity.transaction_signature || activity.transaction_hash,
          transaction_signature: activity.transaction_signature,
          metadata: activity.metadata
        }));
        
        setActivities(transformedActivities);
      } else {
        // Fallback to mock data for development
        console.log('Activity API not available, using mock data');
        const mockActivities = generateMockActivity(wallet);
        setActivities(mockActivities);
      }
    } catch (err) {
      setError(language === 'ru' ? 'Ошибка загрузки активности' : 'Error loading activity');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadActivities();
  }, [wallet, language]);

  if (!wallet) {
    return (
      <Card className="p-6 text-center bg-gray-800/50 border-gray-700/50">
        <div className="text-gray-400">
          {language === 'ru' ? 'Подключите кошелек для просмотра активности' : 'Connect wallet to view activity'}
        </div>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card className="p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-white">
            {language === 'ru' ? 'Последняя активность' : 'Recent Activity'}
          </h3>
          <div className="w-6 h-6 bg-gray-600/30 rounded animate-pulse"></div>
        </div>
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="animate-pulse flex items-center space-x-3 p-3 bg-gray-800/50 border border-gray-700/50 rounded-lg">
              <div className="w-10 h-10 bg-gray-600/30 rounded-full"></div>
              <div className="flex-1 space-y-2">
                <div className="h-4 bg-gray-600/30 rounded w-3/4"></div>
                <div className="h-3 bg-gray-600/20 rounded w-1/2"></div>
              </div>
              <div className="w-16 h-4 bg-gray-600/30 rounded"></div>
            </div>
          ))}
        </div>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="p-6 text-center bg-gray-800/50 border-gray-700/50">
        <div className="text-red-400 mb-4">{error}</div>
        <Button onClick={loadActivities} variant="primary">
          <RefreshIcon className="w-4 h-4 mr-2" />
          {language === 'ru' ? 'Повторить' : 'Retry'}
        </Button>
      </Card>
    );
  }

  const displayActivities = detailed ? activities : activities.slice(0, 10);

  return (
    <Card className="p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold flex items-center text-white">
          <StatsIcon className="w-5 h-5 mr-2 text-gray-400" />
          {language === 'ru' ? 'Последняя активность' : 'Recent Activity'}
        </h3>
        <Button 
          onClick={loadActivities} 
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

      {displayActivities.length === 0 ? (
        <div className="text-center py-8 text-gray-400">
          {language === 'ru' ? 'Нет активности' : 'No activity yet'}
        </div>
      ) : (
        <div className="space-y-3">
          {displayActivities.map((activity) => {
            const activityType = activity.activity_type || activity.type;
            const IconComponent = activityTypeIcons[activityType] || StatsIcon; // Default fallback
            const colorClasses = activityTypeColors[activityType] || 'text-gray-400 bg-gradient-to-br from-gray-500/10 to-gray-600/10 border border-gray-500/20';
            
            return (
              <div 
                key={activity.id}
                className="flex items-center space-x-3 p-3 bg-gray-800/50 border border-gray-700/50 hover:bg-gray-700/50 rounded-lg transition-colors duration-200"
              >
                {/* Icon */}
                <div className={`w-10 h-10 rounded-full flex items-center justify-center backdrop-blur-sm ${colorClasses}`}>
                  <IconComponent className="w-5 h-5" />
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-white truncate">
                    {getActivityDescription(activity, language)}
                  </div>
                  <div className="text-sm text-gray-400">
                    <div className="flex items-center space-x-2">
                      <span>{formatDate(activity.timestamp, language)}</span>
                      {detailed && (activity.transaction_hash || activity.transaction_signature) && (
                        <>
                          <span className="hidden sm:inline">•</span>
                          <span className="font-mono text-xs hidden sm:inline truncate max-w-[100px]">
                            {formatTransactionHash(activity.transaction_hash || activity.transaction_signature || '')}
                          </span>
                        </>
                      )}
                    </div>
                    {/* Show hash on separate line for mobile when detailed view */}
                    {detailed && (activity.transaction_hash || activity.transaction_signature) && (
                      <div className="sm:hidden mt-1 font-mono text-xs text-gray-500 truncate">
                        {formatTransactionHash(activity.transaction_hash || activity.transaction_signature || '')}
                      </div>
                    )}
                  </div>
                </div>

                {/* Amount */}
                {activity.amount !== undefined && (
                  <div className="text-right flex-shrink-0">
                    <div className={`font-semibold ${
                      // Positive (income) events
                      ['business_sale', 'business_sold', 'business_sold_from_slot', 
                       'earnings_claim', 'earnings_claimed', 'earnings_updated',
                       'referral_bonus', 'referral_bonus_added'].includes(activityType)
                        ? 'text-green-400'
                        // Negative (spending) events  
                        : ['business_purchase', 'business_created', 'business_created_in_slot',
                           'business_upgrade', 'business_upgraded', 'business_upgraded_in_slot',
                           'premium_slot_purchased'].includes(activityType)
                        ? 'text-red-400'
                        // Neutral events
                        : 'text-gray-400'
                    }`}>
                      {['business_sale', 'business_sold', 'business_sold_from_slot',
                        'earnings_claim', 'earnings_claimed', 'earnings_updated', 
                        'referral_bonus', 'referral_bonus_added'].includes(activityType) ? '+' : '-'}
                      {['prestige_gain', 'prestige_level_up'].includes(activityType)
                        ? `${activity.amount} ${language === 'ru' ? 'очков' : 'pts'}`
                        : `${formatSOL(activity.amount)} SOL`
                      }
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {!detailed && activities.length > 10 && (
        <div className="mt-4 text-center">
          <div className="text-sm text-gray-400">
            {language === 'ru' 
              ? `Показано 10 из ${activities.length} записей`
              : `Showing 10 of ${activities.length} entries`
            }
          </div>
        </div>
      )}
    </Card>
  );
};
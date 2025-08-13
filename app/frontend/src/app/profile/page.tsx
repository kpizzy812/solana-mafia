'use client';

import React, { useState } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { AppLayout } from '@/components/layout/AppLayout';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { UserIcon, TrophyIcon, UsersIcon, StatsIcon } from '@/components/ui/icons';
import { useLanguage } from '@/hooks/useLanguage';

// Import profile components (will create these)
import { ProfileHeader } from './components/ProfileHeader';
import { LeaderboardTabs } from './components/LeaderboardTabs';
import { ProfileStats } from './components/ProfileStats';
import { RecentActivity } from './components/RecentActivity';

// Import hooks (will create these)
import { usePlayerProfile } from './hooks/usePlayerProfile';
import { useLeaderboards } from './hooks/useLeaderboards';

type TabType = 'overview' | 'leaderboards' | 'stats' | 'activity';

interface TabItem {
  id: TabType;
  label: {
    en: string;
    ru: string;
  };
  icon: React.ComponentType<{ className?: string }>;
}

const tabs: TabItem[] = [
  {
    id: 'overview',
    label: { en: 'Overview', ru: 'Обзор' },
    icon: UserIcon,
  },
  {
    id: 'leaderboards',
    label: { en: 'Leaderboards', ru: 'Лидерборды' },
    icon: TrophyIcon,
  },
  {
    id: 'stats',
    label: { en: 'Statistics', ru: 'Статистика' },
    icon: StatsIcon,
  },
  {
    id: 'activity',
    label: { en: 'Activity', ru: 'Активность' },
    icon: UsersIcon,
  },
];

export default function ProfilePage() {
  const wallet = useWallet();
  const { connected, publicKey } = wallet;
  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const { language, setLanguage, isLoaded: languageLoaded } = useLanguage();

  // Get player profile data
  const {
    profile,
    loading: profileLoading,
    error: profileError,
    refetch: refetchProfile
  } = usePlayerProfile(publicKey?.toString());

  // Get leaderboards data
  const {
    earningsLeaderboard,
    referralsLeaderboard,
    prestigeLeaderboard,
    playerPosition,
    loading: leaderboardsLoading,
    error: leaderboardsError,
    refetch: refetchLeaderboards
  } = useLeaderboards(publicKey?.toString());

  // 🌐 Prevent language flash by waiting for language to load from localStorage
  if (!languageLoaded) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  if (!connected) {
    return (
      <AppLayout
        language={language}
        onLanguageChange={setLanguage}
        playerData={{
          prestigePoints: 0,
          prestigeLevel: 'wannabe',
          pointsToNextLevel: 50,
          prestigeProgressPercentage: 0,
        }}
      >
        <div className="min-h-[60vh] flex flex-col items-center justify-center space-y-6">
          <div className="text-center space-y-4">
            <UserIcon className="w-16 h-16 mx-auto text-muted-foreground/50" />
            <h1 className="text-2xl font-bold text-foreground">
              {language === 'ru' ? 'Подключите кошелек' : 'Connect Wallet'}
            </h1>
            <p className="text-muted-foreground max-w-md">
              {language === 'ru' 
                ? 'Для просмотра профиля и лидербордов необходимо подключить Solana кошелек'
                : 'Connect your Solana wallet to view your profile and leaderboards'
              }
            </p>
          </div>
        </div>
      </AppLayout>
    );
  }

  const handleRefresh = () => {
    refetchProfile();
    refetchLeaderboards();
  };

  return (
    <AppLayout
      language={language}
      onLanguageChange={setLanguage}
      playerData={{
        prestigePoints: profile?.prestige_info?.current_points || 0,
        prestigeLevel: profile?.prestige_info?.current_level || 'wannabe',
        pointsToNextLevel: profile?.prestige_info?.points_to_next_level || 50,
        prestigeProgressPercentage: profile?.prestige_info?.progress_percentage || 0,
      }}
    >
      <div className="space-y-6">
        {/* Profile Header */}
        <ProfileHeader 
          profile={profile}
          loading={profileLoading}
          error={profileError}
          language={language}
          onRefresh={handleRefresh}
        />

        {/* Navigation Tabs */}
        <Card className="p-1">
          <div className="flex space-x-1 overflow-x-auto">
            {tabs.map((tab) => {
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
                  <IconComponent className="w-3 h-3 md:w-4 md:h-4 shrink-0" />
                  <span className="truncate text-[10px] md:text-sm font-medium leading-tight">
                    {tab.label[language]}
                  </span>
                </Button>
              );
            })}
          </div>
        </Card>

        {/* Tab Content */}
        <div className="min-h-[400px]">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <ProfileStats 
                profile={profile}
                playerPosition={playerPosition}
                loading={profileLoading}
                language={language}
              />
              
              <RecentActivity 
                wallet={publicKey?.toString()}
                language={language}
              />
            </div>
          )}

          {activeTab === 'leaderboards' && (
            <LeaderboardTabs
              earningsLeaderboard={earningsLeaderboard}
              referralsLeaderboard={referralsLeaderboard}
              prestigeLeaderboard={prestigeLeaderboard}
              playerPosition={playerPosition}
              loading={leaderboardsLoading}
              error={leaderboardsError}
              language={language}
              currentWallet={publicKey?.toString()}
              onRefresh={refetchLeaderboards}
            />
          )}

          {activeTab === 'stats' && (
            <ProfileStats 
              profile={profile}
              playerPosition={playerPosition}
              loading={profileLoading}
              language={language}
              detailed={true}
            />
          )}

          {activeTab === 'activity' && (
            <RecentActivity 
              wallet={publicKey?.toString()}
              language={language}
              detailed={true}
            />
          )}
        </div>
      </div>
    </AppLayout>
  );
}
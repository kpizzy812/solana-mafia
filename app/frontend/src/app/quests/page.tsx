'use client';

import React, { useState, useEffect } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { AppLayout } from '@/components/layout/AppLayout';
import { NotConnectedState } from '@/app/components/states';
import { useLanguage } from '@/hooks/useLanguage';
import { useTranslation } from '@/locales';
import { QuestIcon, TrophyIcon, CheckCircleIcon, StarIcon, ClockIcon } from '@/components/ui/icons';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { 
  Quest, 
  QuestWithProgress, 
  QuestListResponse, 
  QuestClaimResponse,
  QuestType,
  QuestDifficulty 
} from '@/types';
import { apiClient } from '@/lib/api';

interface QuestPageData {
  quests: QuestWithProgress[];
  loading: boolean;
  error: string | null;
  claiming: Record<number, boolean>;
  stats: {
    totalQuests: number;
    completedCount: number;
    claimedCount: number;
    availableToCllaim: number;
  };
}

export default function QuestsPage() {
  const { connected, publicKey } = useWallet();
  const { language, setLanguage, isLoaded: languageLoaded } = useLanguage();
  const [data, setData] = useState<QuestPageData>({
    quests: [],
    loading: false,
    error: null,
    claiming: {},
    stats: {
      totalQuests: 0,
      completedCount: 0,
      claimedCount: 0,
      availableToCllaim: 0
    }
  });

  // Track which social quests user has clicked on (visited the link)
  const [visitedQuests, setVisitedQuests] = useState<Set<number>>(new Set());

  const t = useTranslation(language);

  // Load visited quests from localStorage for current wallet
  useEffect(() => {
    if (connected && publicKey && typeof window !== 'undefined') {
      const walletKey = `visitedQuests_${publicKey.toBase58()}`;
      const saved = localStorage.getItem(walletKey);
      if (saved) {
        setVisitedQuests(new Set(JSON.parse(saved)));
      } else {
        setVisitedQuests(new Set());
      }
    } else {
      setVisitedQuests(new Set());
    }
  }, [connected, publicKey]);

  // Save visited quests to localStorage whenever it changes
  useEffect(() => {
    if (connected && publicKey && typeof window !== 'undefined') {
      const walletKey = `visitedQuests_${publicKey.toBase58()}`;
      localStorage.setItem(walletKey, JSON.stringify([...visitedQuests]));
    }
  }, [visitedQuests, connected, publicKey]);

  // Load quests for connected user
  useEffect(() => {
    if (connected && publicKey) {
      loadQuests();
    }
  }, [connected, publicKey]);

  const loadQuests = async () => {
    if (!publicKey) return;

    setData(prev => ({ ...prev, loading: true, error: null }));
    
    try {
      // Set wallet authorization for API requests
      apiClient.setWalletAuth(publicKey.toBase58());
      
      const result = await apiClient.getPlayerQuests(publicKey.toBase58());
      
      if (result.success && result.data) {
        const questData: QuestListResponse = result.data;
        
        setData(prev => ({
          ...prev,
          quests: questData.quests,
          stats: {
            totalQuests: questData.total_quests,
            completedCount: questData.completed_count,
            claimedCount: questData.claimed_count,
            availableToCllaim: questData.available_to_claim
          },
          loading: false
        }));
      } else {
        throw new Error(result.error || 'Failed to load quests');
      }
    } catch (error) {
      console.error('Error loading quests:', error);
      setData(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Unknown error',
        loading: false
      }));
    }
  };

  const handleSocialQuestCompleted = async (questId: number) => {
    if (!publicKey) return;

    setData(prev => ({
      ...prev,
      claiming: { ...prev.claiming, [questId]: true }
    }));

    try {
      // First start the quest
      await apiClient.startQuest(questId, publicKey.toBase58());
      
      // Then mark it as completed by updating progress to 1
      const result = await apiClient.updateQuestProgress(
        questId, 
        publicKey.toBase58(), 
        1  // Set progress to 1 (completed)
      );
      
      if (result.success) {
        // Reload quests to get updated state
        await loadQuests();
      } else {
        throw new Error(result.error || 'Failed to update quest progress');
      }
    } catch (error) {
      console.error('Error completing social quest:', error);
      alert(`Ошибка: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setData(prev => ({
        ...prev,
        claiming: { ...prev.claiming, [questId]: false }
      }));
    }
  };

  const handleClaimQuest = async (questId: number) => {
    if (!publicKey) return;

    setData(prev => ({
      ...prev,
      claiming: { ...prev.claiming, [questId]: true }
    }));

    try {
      const result = await apiClient.claimQuestReward(questId, publicKey.toBase58());
      
      if (result.success) {
        const claimResult: QuestClaimResponse = result.data;
        
        // Show success message
        alert(`Задание выполнено! Получено ${claimResult.prestige_points_awarded} очков престижа!`);
        
        // Reload quests to get updated state
        await loadQuests();
      } else {
        throw new Error(result.error || 'Failed to claim quest reward');
      }
    } catch (error) {
      console.error('Error claiming quest:', error);
      alert(`Ошибка: ${error instanceof Error ? error.message : 'Unknown error'}`);
    } finally {
      setData(prev => ({
        ...prev,
        claiming: { ...prev.claiming, [questId]: false }
      }));
    }
  };

  const getDifficultyColor = (difficulty: QuestDifficulty): string => {
    switch (difficulty) {
      case QuestDifficulty.EASY: return 'text-green-500';
      case QuestDifficulty.MEDIUM: return 'text-yellow-500';
      case QuestDifficulty.HARD: return 'text-orange-500';
      case QuestDifficulty.LEGENDARY: return 'text-purple-500';
      default: return 'text-gray-500';
    }
  };

  const getQuestTypeIcon = (questType: QuestType): React.ComponentType<{ className?: string }> => {
    switch (questType) {
      case QuestType.SOCIAL_FOLLOW: return StarIcon;
      case QuestType.BUSINESS_PURCHASE: return QuestIcon;
      case QuestType.BUSINESS_UPGRADE: return TrophyIcon;
      case QuestType.REFERRAL_INVITE: return StarIcon;
      case QuestType.DAILY_LOGIN: return ClockIcon;
      default: return QuestIcon;
    }
  };

  const getProgressPercentage = (quest: QuestWithProgress): number => {
    if (!quest.progress) return 0;
    return quest.progress.progress_percentage || 0;
  };

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
      <AppLayout language={language} onLanguageChange={setLanguage}>
        <NotConnectedState language={language} />
      </AppLayout>
    );
  }

  return (
    <AppLayout language={language} onLanguageChange={setLanguage}>
      <div className="space-y-6">
        {/* Header */}
        <div className="text-center space-y-1">
          <h1 className="text-xl font-bold text-foreground">
            {language === 'ru' ? 'Задания' : 'Quests'}
          </h1>
          <p className="text-sm text-muted-foreground">
            {language === 'ru' 
              ? 'Выполняйте задания и получайте очки престижа' 
              : 'Complete quests and earn prestige points'
            }
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-2">
          <Card className="p-2 text-center">
            <div className="text-sm font-bold text-foreground">{data.stats.totalQuests}</div>
            <div className="text-xs text-muted-foreground">
              {language === 'ru' ? 'Всего' : 'Total'}
            </div>
          </Card>
          <Card className="p-2 text-center">
            <div className="text-sm font-bold text-green-500">{data.stats.completedCount}</div>
            <div className="text-xs text-muted-foreground">
              {language === 'ru' ? 'Выполнено' : 'Completed'}
            </div>
          </Card>
          <Card className="p-2 text-center">
            <div className="text-sm font-bold text-blue-500">{data.stats.claimedCount}</div>
            <div className="text-xs text-muted-foreground">
              {language === 'ru' ? 'Получено' : 'Claimed'}
            </div>
          </Card>
          <Card className="p-2 text-center">
            <div className="text-sm font-bold text-orange-500">{data.stats.availableToCllaim}</div>
            <div className="text-xs text-muted-foreground">
              {language === 'ru' ? 'Готово' : 'Ready'}
            </div>
          </Card>
        </div>

        {/* Loading State */}
        {data.loading && (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto"></div>
            <p className="mt-2 text-muted-foreground">
              {language === 'ru' ? 'Загрузка заданий...' : 'Loading quests...'}
            </p>
          </div>
        )}

        {/* Error State */}
        {data.error && (
          <Card className="p-4 border-red-200 bg-red-50">
            <p className="text-red-700">
              {language === 'ru' ? 'Ошибка загрузки:' : 'Loading error:'} {data.error}
            </p>
            <Button 
              onClick={loadQuests} 
              variant="secondary" 
              className="mt-2"
            >
              {language === 'ru' ? 'Повторить' : 'Retry'}
            </Button>
          </Card>
        )}

        {/* Quests List */}
        {!data.loading && !data.error && (
          <div className="space-y-2">
            {data.quests.length === 0 ? (
              <Card className="p-4 text-center">
                <QuestIcon className="w-8 h-8 text-muted-foreground mx-auto mb-2" />
                <p className="text-sm text-muted-foreground">
                  {language === 'ru' ? 'Заданий пока нет' : 'No quests available'}
                </p>
              </Card>
            ) : (
              data.quests
                .filter(questItem => !questItem.progress?.is_claimed) // Hide claimed quests
                .map((questItem) => {
                  const quest = questItem.quest;
                  const progress = questItem.progress;
                  const isCompleted = progress?.is_completed || false;
                  const isClaimed = progress?.is_claimed || false;
                  const isReadyToClaim = progress?.is_ready_to_claim || false;
                  const progressPercentage = getProgressPercentage(questItem);
                  const TypeIcon = getQuestTypeIcon(quest.quest_type);
                  const isClaiming = data.claiming[quest.id] || false;

                  const handleQuestClick = () => {
                    // Open social links when clicking on quest and mark as visited
                    if (quest.social_links && quest.quest_type === 'social_follow' && !progress) {
                      // Mark quest as visited
                      setVisitedQuests(prev => new Set([...prev, quest.id]));
                      
                      // Open appropriate social link
                      if (quest.social_links.twitter) {
                        window.open(quest.social_links.twitter, '_blank');
                      } else if (quest.social_links.telegram) {
                        window.open(quest.social_links.telegram, '_blank');
                      } else if (quest.social_links.telegram_chat) {
                        window.open(quest.social_links.telegram_chat, '_blank');
                      } else if (quest.social_links.ceo_channel) {
                        window.open(quest.social_links.ceo_channel, '_blank');
                      }
                    }
                  };

                  return (
                    <Card key={quest.id} className="p-3">
                      <div 
                        className="flex items-center justify-between cursor-pointer" 
                        onClick={handleQuestClick}
                      >
                        {/* Left side: Icon + Content */}
                        <div className="flex items-center space-x-3 flex-1 min-w-0">
                          {/* Quest Icon */}
                          <div className={`p-2 rounded-full ${isCompleted ? 'bg-green-100' : 'bg-gray-100'}`}>
                            <TypeIcon className={`w-4 h-4 ${isCompleted ? 'text-green-600' : 'text-gray-600'}`} />
                          </div>

                          {/* Quest Content */}
                          <div className="flex-1 min-w-0">
                            <h3 className="font-medium text-sm text-foreground truncate">
                              {language === 'ru' ? quest.title_ru : quest.title_en}
                            </h3>
                            <p className="text-xs text-muted-foreground truncate">
                              {language === 'ru' ? quest.description_ru : quest.description_en}
                            </p>
                            <div className="flex items-center space-x-2 mt-1">
                              <span className={`text-xs font-medium ${getDifficultyColor(quest.difficulty)}`}>
                                {quest.difficulty.toUpperCase()}
                              </span>
                              <span className="text-xs text-muted-foreground">•</span>
                              <span className="text-xs text-foreground">
                                +{quest.prestige_reward} {language === 'ru' ? 'престижа' : 'prestige'}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Right side: Action Button */}
                        <div className="ml-3 flex-shrink-0">
                          {isReadyToClaim ? (
                            <Button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleClaimQuest(quest.id);
                              }}
                              variant="primary"
                              disabled={isClaiming}
                              className="px-4 py-2 rounded-full text-xs font-medium bg-green-500 hover:bg-green-600 text-white"
                            >
                              {isClaiming ? (
                                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-white"></div>
                              ) : (
                                <>Claim</>
                              )}
                            </Button>
                          ) : quest.quest_type === 'social_follow' && !progress && visitedQuests.has(quest.id) ? (
                            <Button
                              onClick={(e) => {
                                e.stopPropagation();
                                handleSocialQuestCompleted(quest.id);
                              }}
                              variant="secondary"
                              disabled={isClaiming}
                              className="px-3 py-1 rounded-full bg-blue-100 hover:bg-blue-200 text-blue-600 text-xs font-medium"
                            >
                              {isClaiming ? (
                                <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-600"></div>
                              ) : (
                                language === 'ru' ? 'Check' : 'Check'
                              )}
                            </Button>
                          ) : (
                            <div className="w-6 h-6 rounded-full border-2 border-gray-300 flex items-center justify-center">
                              {progress && progress.current_progress > 0 ? (
                                <div className="w-3 h-3 rounded-full bg-blue-400"></div>
                              ) : (
                                <div className="w-3 h-3 rounded-full border border-gray-300"></div>
                              )}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Progress Bar (only if in progress) */}
                      {progress && !isCompleted && !isClaimed && (
                        <div className="mt-2 px-11">
                          <div className="w-full bg-gray-200 rounded-full h-1">
                            <div 
                              className="bg-primary h-1 rounded-full transition-all duration-300"
                              style={{ width: `${Math.min(progressPercentage, 100)}%` }}
                            />
                          </div>
                        </div>
                      )}
                    </Card>
                  );
                })
            )}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
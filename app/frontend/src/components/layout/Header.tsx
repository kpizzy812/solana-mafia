'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { WalletButton } from '@/components/wallet/WalletButton';
import { LanguageSelector } from '@/components/ui/LanguageSelector';
import { InfoTooltip } from '@/components/ui/InfoTooltip';
import { Star } from 'lucide-react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { apiClient } from '@/lib/api';
import Image from 'next/image';
import Link from 'next/link';

interface HeaderProps {
  language?: 'en' | 'ru';
  onLanguageChange?: (lang: 'en' | 'ru') => void;
  playerData?: {
    prestigePoints?: number;
    prestigeLevel?: string;
    pointsToNextLevel?: number;
    prestigeProgressPercentage?: number;
  };
}

export const Header: React.FC<HeaderProps> = ({
  language = 'en',
  onLanguageChange,
  playerData,
}) => {
  const wallet = useWallet();
  const { connected, publicKey } = wallet;
  
  // Internal prestige state for WebSocket updates
  const [internalPrestigeData, setInternalPrestigeData] = useState<{
    points: number;
    level: string;
    pointsToNext: number;
    progressPercentage: number;
  } | null>(null);

  // Handle WebSocket prestige updates
  const handlePrestigeUpdate = useCallback((data: any) => {
    console.log('💎 Header received prestige update:', data);
    
    if (data.event === 'prestige_updated' && data.wallet === publicKey?.toString()) {
      setInternalPrestigeData({
        points: data.current_points || 0,
        level: data.current_level || 'wannabe',
        pointsToNext: data.points_to_next_level || 50,
        progressPercentage: data.progress_percentage || 0,
      });
    }
  }, [publicKey]);

  // Connect to WebSocket for real-time updates
  useWebSocket({
    wallet: publicKey?.toString() || null,
    onPrestigeUpdate: handlePrestigeUpdate,
    enabled: connected && !!publicKey
  });

  // Load initial prestige data when wallet connects
  useEffect(() => {
    const loadPrestigeData = async () => {
      if (!connected || !publicKey) {
        setInternalPrestigeData(null);
        return;
      }

      try {
        // Try to get prestige data from API
        const response = await apiClient.getPlayerStats(publicKey.toString());
        if (response.success && response.data) {
          setInternalPrestigeData({
            points: response.data.prestige_points || 0,
            level: response.data.prestige_level || 'wannabe',
            pointsToNext: response.data.points_to_next_level || 50,
            progressPercentage: response.data.prestige_progress_percentage || 0,
          });
        }
      } catch (error) {
        console.log('Failed to load prestige data in header:', error);
        // Fallback to default values
        setInternalPrestigeData({
          points: 0,
          level: 'wannabe',
          pointsToNext: 50,
          progressPercentage: 0,
        });
      }
    };

    loadPrestigeData();
  }, [connected, publicKey]);

  // Prestige data - use internal data if available, otherwise fall back to props
  const prestigeData = React.useMemo(() => {
    if (connected) {
      // Prefer internal WebSocket-updated data
      if (internalPrestigeData) {
        return internalPrestigeData;
      }
      
      // Fall back to props data
      if (playerData) {
        return {
          points: playerData.prestigePoints || 0,
          level: playerData.prestigeLevel || 'wannabe',
          pointsToNext: playerData.pointsToNextLevel || 50,
          progressPercentage: playerData.prestigeProgressPercentage || 0,
        };
      }
    }
    
    // Default values
    return {
      points: 0,
      level: 'wannabe',
      pointsToNext: 50,
      progressPercentage: 0,
    };
  }, [connected, internalPrestigeData, playerData]);

  // Level display names
  const getLevelDisplayName = (level: string) => {
    const levelNames = {
      en: {
        wannabe: 'Wannabe',
        associate: 'Associate',
        soldier: 'Soldier',
        capo: 'Capo',
        underboss: 'Underboss',
        boss: 'Boss',
      },
      ru: {
        wannabe: 'Новичок',
        associate: 'Помощник',
        soldier: 'Солдат',
        capo: 'Капо',
        underboss: 'Заместитель',
        boss: 'Босс',
      },
    };
    return levelNames[language][level] || level;
  };


  const texts = {
    en: {
      prestigeLevel: 'Level:',
      prestigeSystemTitle: 'Prestige System',
      prestigeSystemDesc: 'Earn prestige points by investing in businesses and referring friends. Progress through 6 mafia ranks: Wannabe → Associate → Soldier → Capo → Underboss → Boss. Higher levels unlock better bonuses, airdrops, and exclusive features!',
    },
    ru: {
      prestigeLevel: 'Уровень:',
      prestigeSystemTitle: 'Система престижа',
      prestigeSystemDesc: 'Зарабатывайте очки престижа инвестируя в бизнесы и приглашая друзей. Проходите через 6 мафиозных рангов: Новичок → Помощник → Солдат → Капо → Заместитель → Босс. Высокие уровни открывают лучшие бонусы, airdrop-ы и эксклюзивные функции!',
    },
  };

  const t = texts[language];

  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 items-center justify-between px-3 gap-3 min-w-0">
        {/* Left Section: Logo + Language Selector */}
        <div className="flex items-center gap-3 flex-shrink-0">
          {/* Logo */}
          <div className="flex items-center">
            <Link href="/" className="relative group cursor-pointer">
              <Image
                src="/icons/logo.png"
                alt="Solana Mafia"
                width={48}
                height={48}
                className="w-12 h-12 transition-all duration-200 group-hover:scale-105 brightness-125 contrast-125 saturate-110"
                priority
                style={{
                  filter: 'drop-shadow(0 0 8px rgba(255,255,255,0.1)) drop-shadow(0 0 16px rgba(139,92,246,0.3))'
                }}
              />
            </Link>
          </div>

          {/* Language Selector */}
          {onLanguageChange && (
            <LanguageSelector
              language={language}
              onLanguageChange={onLanguageChange}
            />
          )}
        </div>

        {/* Center Section: Player Stats when connected */}
        {connected && (
          <div className="flex items-center justify-center flex-1 min-w-0">
            {/* Prestige Display */}
            <div className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-card text-card-foreground hover:bg-accent hover:text-accent-foreground transition-colors text-sm font-medium h-[40px]">
              <Star className="w-4 h-4 text-yellow-500 flex-shrink-0" />
              <span className="text-sm whitespace-nowrap">
                {prestigeData.points}
              </span>
              <InfoTooltip
                content={
                  <div className="space-y-2 max-w-xs">
                    <div className="font-medium text-sm">{t.prestigeSystemTitle}</div>
                    <div className="text-xs text-muted-foreground">
                      {t.prestigeSystemDesc}
                    </div>
                    <div className="text-xs border-t border-muted pt-2">
                      <div className="flex justify-between">
                        <span>{t.prestigeLevel}</span>
                        <span className="font-medium">{getLevelDisplayName(prestigeData.level)}</span>
                      </div>
                      <div className="flex justify-between">
                        <span>{language === 'ru' ? 'Очки к следующему:' : 'Points to next:'}</span>
                        <span className="font-medium">{prestigeData.pointsToNext}</span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-1.5 mt-1">
                        <div 
                          className="bg-yellow-500 h-1.5 rounded-full transition-all duration-300"
                          style={{ width: `${prestigeData.progressPercentage}%` }}
                        />
                      </div>
                    </div>
                  </div>
                }
                position="bottom"
              />
            </div>
          </div>
        )}

        {/* Right Section: Wallet Connection */}
        <div className="flex-shrink-0">
          <WalletButton language={language} />
        </div>
      </div>
    </header>
  );
};
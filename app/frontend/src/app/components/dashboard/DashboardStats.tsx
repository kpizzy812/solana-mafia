/**
 * Dashboard statistics component
 */

import React, { useState, useEffect } from 'react';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { WalletIcon, BuildingIcon, GridIcon } from '@/components/ui/icons';
import { InfoTooltip } from '@/components/ui/InfoTooltip';
import { lamportsToSOL } from '../../../lib/api';
import { formatBalance, formatTotalEarnings } from '../../utils/formatters';
import { useTranslation } from '@/locales';
import { PlayerStats } from '../../types';

interface DashboardStatsProps {
  playerStats: PlayerStats;
  walletBalance: number;
  balanceLoading: boolean;
  language: 'en' | 'ru';
}

export const DashboardStats: React.FC<DashboardStatsProps> = ({
  playerStats,
  walletBalance,
  balanceLoading,
  language
}) => {
  const t = useTranslation(language);
  const [showHint, setShowHint] = useState(false);

  // Show hint animation when component mounts
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowHint(true);
      const hideTimer = setTimeout(() => setShowHint(false), 4000);
      return () => clearTimeout(hideTimer);
    }, 2000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="mb-6">
      <h2 className="text-lg font-semibold text-foreground mb-3">{t.dashboard}</h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
        <div className="relative">
          <DashboardCard
            title={t.totalEarnings} 
            value={`${formatTotalEarnings(lamportsToSOL(playerStats.totalEarnings))} SOL`}
            icon={<WalletIcon className="w-4 h-4 text-primary" />}
          />
          <div className="absolute -top-1 -right-1">
            <div className="relative">
              <InfoTooltip
                content={
                  <div className="space-y-2 max-w-xs">
                    <div className="font-medium text-sm">{t.tooltips.totalEarningsHelp.title}</div>
                    <div className="text-xs text-muted-foreground">
                      {t.tooltips.totalEarningsHelp.content}
                    </div>
                  </div>
                }
                position="bottom"
              />
              
              {/* Animated hint arrow */}
              {showHint && (
                <div className="absolute -top-12 -left-8 flex flex-col items-center animate-in slide-in-from-bottom-2 fade-in-0 duration-300">
                  <div className="flex items-center gap-1 bg-primary text-primary-foreground text-xs px-2 py-1 rounded-md shadow-lg animate-bounce whitespace-nowrap">
                    <span>{t.hintText}</span>
                  </div>
                  <div className="text-primary text-lg animate-bounce" style={{ animationDelay: '0.1s' }}>
                    👇
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
        
        <div className="relative">
          <DashboardCard
            title={t.businesses}
            value={playerStats.businessCount}
            icon={<BuildingIcon className="w-4 h-4 text-primary" />}
          />
          <div className="absolute -top-1 -right-1">
            <InfoTooltip
              content={
                <div className="space-y-2 max-w-xs">
                  <div className="font-medium text-sm">{t.tooltips.businessCountHelp.title}</div>
                  <div className="text-xs text-muted-foreground">
                    {t.tooltips.businessCountHelp.content}
                  </div>
                </div>
              }
              position="bottom"
            />
          </div>
        </div>
        
        <div className="relative">
          <DashboardCard
            title={t.businessSlots}
            value={`${playerStats.totalSlots - playerStats.businessCount}/${playerStats.totalSlots}`}
            icon={<GridIcon className="w-4 h-4 text-primary" />}
          />
          <div className="absolute -top-1 -right-1">
            <InfoTooltip
              content={
                <div className="space-y-2 max-w-xs">
                  <div className="font-medium text-sm">{t.tooltips.businessSlotsHelp.title}</div>
                  <div className="text-xs text-muted-foreground">
                    {t.tooltips.businessSlotsHelp.content}
                  </div>
                </div>
              }
              position="bottom"
            />
          </div>
        </div>
        
        <div className="relative">
          <DashboardCard
            title={t.walletBalance}
            value={balanceLoading ? "..." : `${walletBalance.toFixed(2)} SOL`}
            icon={<WalletIcon className="w-4 h-4 text-green-500" />}
          />
          <div className="absolute -top-1 -right-1">
            <InfoTooltip
              content={
                <div className="space-y-2 max-w-xs">
                  <div className="font-medium text-sm">{t.tooltips.walletBalanceHelp.title}</div>
                  <div className="text-xs text-muted-foreground">
                    {t.tooltips.walletBalanceHelp.content}
                  </div>
                </div>
              }
              position="bottom"
            />
          </div>
        </div>
      </div>
    </div>
  );
};
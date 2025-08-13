/**
 * Earnings balance component with withdraw button
 */

import React from 'react';
import { InfoTooltip } from '@/components/ui/InfoTooltip';
import { useTranslation } from '@/locales';
import { cn } from '../../../lib/utils';
import { formatBalance } from '../../utils/formatters';
import { lamportsToSOL } from '../../../lib/api';
import { PlayerStats } from '../../types';

interface EarningsBalanceProps {
  playerStats: PlayerStats;
  onWithdrawClick: () => void;
  onUpdateEarningsClick: () => void;
  onSyncFromBlockchain: () => void;  // 🆕 NEW: Sync from blockchain
  isUpdatingEarnings?: boolean;
  language: 'en' | 'ru';
}

export const EarningsBalance: React.FC<EarningsBalanceProps> = ({
  playerStats,
  onWithdrawClick,
  onUpdateEarningsClick,
  onSyncFromBlockchain,  // 🆕 NEW: Sync from blockchain
  isUpdatingEarnings = false,
  language
}) => {
  const t = useTranslation(language);

  return (
    <div className="mb-4 relative">
      <div className="bg-card rounded-lg border border-border p-4 hover:bg-accent/50 transition-colors">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <img 
              src="/icons/solana.png" 
              alt="Solana" 
              className="w-16 h-16 object-contain"
            />
            <div>
              <div className="text-sm font-medium text-muted-foreground">{t.earningsBalance}</div>
              <div className="text-xl font-bold text-card-foreground">
                {formatBalance(lamportsToSOL(playerStats.earningsBalance))} SOL
              </div>
            </div>
          </div>
          <div className="flex space-x-2">
            {/* 
            <button
              onClick={onUpdateEarningsClick}
              disabled={isUpdatingEarnings}
              className={cn(
                "px-3 py-2 rounded-lg text-xs font-medium transition-colors",
                isUpdatingEarnings
                  ? "bg-blue-400 text-white cursor-not-allowed"
                  : "bg-blue-500 hover:bg-blue-600 text-white"
              )}
            >
              {isUpdatingEarnings ? "🔄" : "🔄 Update"}
            </button>
            <button
              onClick={onSyncFromBlockchain}
              className="px-3 py-2 rounded-lg text-xs font-medium bg-orange-500 hover:bg-orange-600 text-white transition-colors"
              title="Sync data directly from blockchain (devnet testing)"
            >
              🔗 Sync
            </button>
            */}
            <button
              onClick={onWithdrawClick}
              disabled={playerStats.earningsBalance === 0}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                playerStats.earningsBalance > 0
                  ? "bg-green-500 hover:bg-green-600 text-white"
                  : "bg-transparent border border-muted-foreground/20 text-muted-foreground/40 cursor-not-allowed"
              )}
            >
              {t.withdraw}
            </button>
          </div>
        </div>
      </div>
      <div className="absolute -top-1 -right-1">
        <InfoTooltip
          content={
            <div className="space-y-2 max-w-xs">
              <div className="font-medium text-sm">{t.tooltips.earningsBalanceHelp.title}</div>
              <div className="text-xs text-muted-foreground">
                {t.tooltips.earningsBalanceHelp.content}
              </div>
            </div>
          }
          position="bottom"
        />
      </div>
    </div>
  );
};
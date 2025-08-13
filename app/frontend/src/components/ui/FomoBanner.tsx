'use client';

import React from 'react';
import { InfoTooltip } from './InfoTooltip';
import { useTranslation } from '@/locales';
import { cn } from '@/lib/utils';
import { TrendingUp, Users, DollarSign } from 'lucide-react';

interface FomoBannerProps {
  totalPlayers: number;
  currentEntryFee: number; // in SOL
  currentEntryFeeUsd: number; // in USD
  solPriceUsd: number; // current SOL price
  language?: 'en' | 'ru';
}

export const FomoBanner: React.FC<FomoBannerProps> = ({
  totalPlayers,
  currentEntryFee,
  currentEntryFeeUsd,
  solPriceUsd,
  language = 'en'
}) => {
  const t = useTranslation(language);

  // Calculate next milestone info for UI
  const getNextMilestone = (players: number) => {
    if (players <= 100) {
      return { milestone: 100, nextFeeUsd: 10.0 };
    } else if (players <= 500) {
      return { milestone: 500, nextFeeUsd: 20.0 };
    } else {
      return { milestone: players, nextFeeUsd: 20.0 }; // Max reached
    }
  };

  const { milestone, nextFeeUsd } = getNextMilestone(totalPlayers);
  const playersUntilIncrease = Math.max(0, milestone - totalPlayers);
  const progressPercentage = totalPlayers <= 100 
    ? (totalPlayers / 100) * 100
    : totalPlayers <= 500 
      ? ((totalPlayers - 100) / 400) * 100
      : 100;

  return (
    <div className="bg-gradient-to-r from-orange-500/10 via-red-500/10 to-pink-500/10 rounded-lg p-4 mb-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1">
            <TrendingUp className="w-4 h-4 text-orange-500 animate-pulse" />
            <span className="text-sm font-medium text-orange-700 dark:text-orange-300">
              {language === 'ru' ? 'FOMO: Цена растет!' : 'FOMO: Price Rising!'}
            </span>
          </div>
          
          <InfoTooltip
            content={
              <div className="space-y-3 max-w-sm">
                <div className="font-medium text-sm">
                  {language === 'ru' ? 'Динамическая цена входа' : 'Dynamic Entry Fee'}
                </div>
                <div className="text-xs text-muted-foreground space-y-2">
                  <p>
                    {language === 'ru' 
                      ? 'Цена входа в игру увеличивается каждые 100 новых игроков. Присоединяйтесь сейчас, пока цена еще низкая!'
                      : 'Entry fee increases every 100 new players. Join now while the price is still low!'
                    }
                  </p>
                  <div className="bg-muted/50 rounded p-2 space-y-1">
                    <div className="text-xs">
                      <span className="font-medium">
                        {language === 'ru' ? 'Курс SOL:' : 'SOL Price:'}
                      </span>
                      <span className="text-blue-600 ml-1">
                        ${solPriceUsd.toFixed(2)}
                      </span>
                    </div>
                    <div className="text-xs">
                      <span className="font-medium">
                        {language === 'ru' ? 'Текущая цена:' : 'Current price:'}
                      </span>
                      <span className="text-green-600 ml-1">
                        ${currentEntryFeeUsd.toFixed(2)} ({currentEntryFee.toFixed(4)} SOL)
                      </span>
                    </div>
                    <div className="text-xs">
                      <span className="font-medium">
                        {language === 'ru' ? 'Следующая веха:' : 'Next milestone:'}
                      </span>
                      <span className="text-red-600 ml-1">
                        ${nextFeeUsd.toFixed(2)} ({milestone} {language === 'ru' ? 'игроков' : 'players'})
                      </span>
                    </div>
                    <div className="text-xs">
                      <span className="font-medium">
                        {language === 'ru' ? 'До повышения:' : 'Players until increase:'}
                      </span>
                      <span className="text-orange-600 ml-1">
                        {playersUntilIncrease}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            }
            position="bottom"
          />
        </div>

        <div className="flex items-center gap-3 text-sm">
          <div className="flex items-center gap-1">
            <Users className="w-4 h-4 text-blue-500" />
            <span className="font-medium">{totalPlayers.toLocaleString()}</span>
            <span className="text-muted-foreground">
              {language === 'ru' ? 'игроков' : 'players'}
            </span>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {/* Progress bar */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>
            {language === 'ru' ? 'До повышения цены' : 'Until price increase'}
          </span>
          <span>
            {playersUntilIncrease} {language === 'ru' ? 'игроков' : 'players'}
          </span>
        </div>
        
        <div className="w-full bg-muted rounded-full h-2 overflow-hidden">
          <div 
            className={cn(
              "h-full bg-gradient-to-r from-green-500 to-red-500 transition-all duration-1000 ease-out",
              progressPercentage > 80 && "animate-pulse"
            )}
            style={{ width: `${progressPercentage}%` }}
          />
        </div>

        {/* Price info */}
        <div className="flex items-center justify-between pt-1">
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-green-500" />
            <span className="text-sm font-medium text-green-600">
              ${currentEntryFeeUsd.toFixed(2)}
            </span>
            <span className="text-xs text-muted-foreground">
              ({currentEntryFee.toFixed(4)} SOL)
            </span>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              SOL: ${solPriceUsd.toFixed(2)}
            </span>
            {playersUntilIncrease > 0 && (
              <span className="text-sm font-bold text-red-600">
                {language === 'ru' ? 'След. $' : 'Next $'}{nextFeeUsd.toFixed(2)}
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
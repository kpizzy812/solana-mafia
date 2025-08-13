/**
 * Level selector component for upgrade modal
 */

import React from 'react';
import { InfoTooltip } from '@/components/ui/InfoTooltip';
import { cn } from '@/lib/utils';

interface LevelSelectorProps {
  businessType: any;
  currentLevel: number;
  targetLevel: number;
  setTargetLevel: (level: number) => void;
  canUpgrade: boolean;
}

export const LevelSelector: React.FC<LevelSelectorProps> = ({
  businessType,
  currentLevel,
  targetLevel,
  setTargetLevel,
  canUpgrade
}) => {
  if (!canUpgrade) return null;

  const targetLevelData = businessType.levels[targetLevel];

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <label className="text-sm font-medium text-muted-foreground">
          Upgrade to Level
        </label>
        <InfoTooltip
          content={
            <div className="space-y-2 max-w-xs">
              <div className="font-medium text-sm">Business Upgrades</div>
              <div className="text-xs text-muted-foreground">
                Each upgrade increases your daily yield and business value. Higher levels provide better returns but cost more to upgrade.
              </div>
            </div>
          }
          position="right"
        />
      </div>
      
      <div className="flex gap-1 p-1 bg-muted rounded-lg">
        {businessType.levels.slice(currentLevel + 1).map((level: any, index: number) => {
          const actualLevel = currentLevel + 1 + index;
          return (
            <button
              key={actualLevel}
              onClick={() => setTargetLevel(actualLevel)}
              className={cn(
                'flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all',
                targetLevel === actualLevel
                  ? 'bg-primary text-primary-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {actualLevel + 1}
            </button>
          );
        })}
      </div>
      
      <div className="text-xs text-muted-foreground mt-1 text-center">
        {targetLevelData.name}: {targetLevelData.description}
      </div>
    </div>
  );
};
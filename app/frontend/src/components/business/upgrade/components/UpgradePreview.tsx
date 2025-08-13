/**
 * Upgrade preview component showing costs and benefits
 */

import React from 'react';
import { DollarSign, TrendingUp, Clock } from 'lucide-react';
import { InfoTooltip } from '@/components/ui/InfoTooltip';
import { UpgradeCalculations } from '../types';

interface UpgradePreviewProps {
  calculations: UpgradeCalculations;
  canUpgrade: boolean;
}

export const UpgradePreview: React.FC<UpgradePreviewProps> = ({
  calculations,
  canUpgrade
}) => {
  if (!canUpgrade) return null;

  const {
    upgradeCost,
    currentDailyYield,
    targetDailyYield,
    yieldIncrease,
    currentDailyYieldPercent,
    targetDailyYieldPercent,
    paybackDays
  } = calculations;

  return (
    <div className="space-y-3">
      {/* Upgrade Cost */}
      <div className="bg-violet-500/10 rounded-lg p-3">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-primary" />
            <span className="text-sm text-muted-foreground">Upgrade Cost</span>
          </div>
          <div className="text-right">
            <div className="text-sm font-bold">{upgradeCost.toFixed(3)} SOL</div>
          </div>
        </div>
      </div>

      {/* Daily Yield Comparison */}
      <div className="bg-green-500/10 rounded-lg p-3">
        <div className="flex justify-between items-center mb-2">
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-success" />
            <span className="text-sm text-muted-foreground">Daily Yield</span>
          </div>
        </div>
        
        <div className="space-y-1">
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">Current:</span>
            <span className="text-muted-foreground">
              {currentDailyYield.toFixed(5)} SOL ({currentDailyYieldPercent.toFixed(2)}%)
            </span>
          </div>
          <div className="flex justify-between text-xs">
            <span className="text-success">After upgrade:</span>
            <span className="font-bold text-success">
              {targetDailyYield.toFixed(5)} SOL ({targetDailyYieldPercent.toFixed(2)}%)
            </span>
          </div>
          <div className="flex justify-between text-xs border-t border-success/20 pt-1">
            <span className="text-success">Increase:</span>
            <span className="font-bold text-success">
              +{yieldIncrease.toFixed(5)} SOL/day
            </span>
          </div>
        </div>
      </div>

      {/* Payback Period */}
      <div className="bg-blue-500/10 rounded-lg p-3">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-blue-500" />
            <span className="text-sm text-muted-foreground">Payback Period</span>
            <InfoTooltip
              content={
                <div className="space-y-2 max-w-xs">
                  <div className="font-medium text-sm">Payback Period</div>
                  <div className="text-xs text-muted-foreground">
                    How many days it will take to recover the upgrade cost through increased daily earnings.
                  </div>
                </div>
              }
              position="left"
              iconClassName="w-3 h-3"
            />
          </div>
          <span className="text-sm font-bold text-blue-500">{paybackDays} days</span>
        </div>
      </div>
    </div>
  );
};
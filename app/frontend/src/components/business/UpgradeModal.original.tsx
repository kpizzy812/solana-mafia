'use client';

import React, { useState, useEffect } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { BUSINESS_TYPES, getBusinessPrice, getDailyYield, getDailyYieldPercent } from '@/data/businesses';
import { ChevronUp, DollarSign, TrendingUp, Clock, X, Wallet, AlertTriangle } from 'lucide-react';
import { InfoTooltip } from '@/components/ui/InfoTooltip';
import { useTranslation } from '@/locales';
import { cn } from '@/lib/utils';
import toast from 'react-hot-toast';

interface BusinessData {
  businessId: string;
  businessType: number;
  level: number;
  totalInvestedAmount: number;
  earningsPerHour: number;
  slotIndex: number;
  isActive: boolean;
  name: string;
}

interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpgrade: (businessId: string, currentLevel: number, targetLevel: number) => Promise<void>;
  businessData: BusinessData | null;
  userBalance?: number; // in SOL
  language?: 'en' | 'ru';
}

export const UpgradeModal: React.FC<UpgradeModalProps> = ({
  isOpen,
  onClose,
  onUpgrade,
  businessData,
  userBalance = 0,
  language = 'en'
}) => {
  const [targetLevel, setTargetLevel] = useState(0);
  const [isUpgrading, setIsUpgrading] = useState(false);

  const t = useTranslation(language);

  // Get business type data
  const businessType = businessData ? BUSINESS_TYPES[businessData.businessType] : null;
  const currentLevel = businessData?.level || 0;
  const maxLevel = businessType?.levels.length || 1;

  // Set target level to next level when modal opens
  useEffect(() => {
    if (businessData && isOpen) {
      const nextLevel = Math.min(currentLevel + 1, maxLevel - 1);
      setTargetLevel(nextLevel);
    }
  }, [businessData, currentLevel, maxLevel, isOpen]);

  if (!businessData || !businessType) {
    return null;
  }

  const currentLevelData = businessType.levels[currentLevel];
  const targetLevelData = businessType.levels[targetLevel];

  // Calculate upgrade costs and stats
  const currentPrice = getBusinessPrice(businessType, currentLevel);
  const targetPrice = getBusinessPrice(businessType, targetLevel);
  const upgradeCost = targetPrice - currentPrice;

  const currentDailyYield = getDailyYield(businessType, currentLevel);
  const targetDailyYield = getDailyYield(businessType, targetLevel);
  const yieldIncrease = targetDailyYield - currentDailyYield;

  const currentDailyYieldPercent = getDailyYieldPercent(businessType, currentLevel);
  const targetDailyYieldPercent = getDailyYieldPercent(businessType, targetLevel);

  const canAfford = userBalance >= upgradeCost;
  const canUpgrade = currentLevel < maxLevel - 1;
  const isMaxLevel = currentLevel === maxLevel - 1;

  const handleUpgrade = async () => {
    if (!canAfford || !canUpgrade || isUpgrading) return;
    
    setIsUpgrading(true);
    try {
      console.log('🚀 User clicked upgrade button, starting process...', {
        businessId: businessData.businessId,
        currentLevel,
        targetLevel,
        upgradeCost: upgradeCost.toFixed(3) + ' SOL',
        userBalance: userBalance.toFixed(3) + ' SOL'
      });
      
      await onUpgrade(businessData.businessId, currentLevel, targetLevel);
      toast.success(
        language === 'ru' 
          ? `Бизнес "${businessData.name}" улучшен до уровня ${targetLevel + 1}!`
          : `Business "${businessData.name}" upgraded to level ${targetLevel + 1}!`
      );
      onClose();
    } catch (error) {
      console.error('Upgrade failed:', error);
      toast.error(
        language === 'ru' 
          ? 'Ошибка при улучшении бизнеса'
          : 'Failed to upgrade business'
      );
    } finally {
      setIsUpgrading(false);
    }
  };

  const paybackDays = yieldIncrease > 0 ? Math.ceil(upgradeCost / yieldIncrease) : 0;

  return (
    <div className={cn(
      'fixed inset-0 z-50 flex items-center justify-center',
      isOpen ? 'visible' : 'invisible'
    )}>
      {/* Backdrop */}
      <div 
        className={cn(
          'absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity',
          isOpen ? 'opacity-100' : 'opacity-0'
        )}
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className={cn(
        'relative bg-card rounded-xl shadow-2xl border border-border w-full max-w-lg',
        'max-h-[90vh] overflow-hidden transition-all',
        isOpen ? 'scale-100 opacity-100' : 'scale-95 opacity-0'
      )}>
        {/* Header with Balance */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold text-card-foreground flex items-center gap-2">
            <ChevronUp className="w-5 h-5 text-primary" />
            Upgrade Business
          </h2>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 bg-muted/50 rounded-lg px-2 py-1">
              <Wallet className="w-4 h-4 text-muted-foreground" />
              <span className={cn(
                'text-sm font-medium',
                canAfford ? 'text-success' : 'text-destructive'
              )}>
                {userBalance.toFixed(2)} SOL
              </span>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-muted transition-colors"
            >
              <X className="w-5 h-5 text-muted-foreground" />
            </button>
          </div>
        </div>
        
        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-8rem)] p-6 space-y-6">
          {/* Current Business Info */}
          <div className="text-center">
            <h3 className="text-xl font-bold text-card-foreground">
              {businessType.name}
            </h3>
            <p className="text-sm text-muted-foreground mt-1">
              {businessData.name}
            </p>
            <div className="flex items-center justify-center gap-2 mt-2">
              <span className="text-lg">{businessType.emoji}</span>
              <span className="text-sm bg-primary/20 text-primary px-2 py-1 rounded-full">
                Level {currentLevel + 1}
              </span>
            </div>
          </div>

          {/* Max Level Warning */}
          {isMaxLevel && (
            <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
              <div className="flex items-center gap-2 text-yellow-600">
                <AlertTriangle className="w-5 h-5" />
                <span className="font-medium">Maximum Level Reached</span>
              </div>
              <p className="text-sm text-yellow-600/80 mt-1">
                This business is already at its maximum level and cannot be upgraded further.
              </p>
            </div>
          )}

          {/* Level Selection */}
          {canUpgrade && (
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
                {businessType.levels.slice(currentLevel + 1).map((level, index) => {
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
          )}

          {/* Upgrade Preview */}
          {canUpgrade && (
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
          )}

          {/* Business Info */}
          <div className="border-t border-border pt-4">
            <div className="bg-muted/50 rounded-lg p-3">
              <div className="text-xs text-muted-foreground mb-2">
                <strong>Business Details:</strong>
              </div>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span>Business ID:</span>
                  <span className="font-mono">{businessData.businessId.slice(0, 8)}...{businessData.businessId.slice(-4)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Current Investment:</span>
                  <span>{(businessData.totalInvestedAmount / 1e9).toFixed(3)} SOL</span>
                </div>
                <div className="flex justify-between">
                  <span>Slot:</span>
                  <span>#{businessData.slotIndex + 1}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <Button
              onClick={onClose}
              variant="secondary"
              className="flex-1"
              disabled={isUpgrading}
            >
              Cancel
            </Button>
            
            <Button
              onClick={handleUpgrade}
              variant="primary"
              className="flex-1"
              disabled={!canAfford || !canUpgrade || isUpgrading || isMaxLevel}
            >
              {isUpgrading ? 'Upgrading...' : 
               isMaxLevel ? 'Max Level' :
               !canAfford ? 'Insufficient Funds' :
               !canUpgrade ? 'Cannot Upgrade' :
               `Upgrade for ${upgradeCost.toFixed(3)} SOL`}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
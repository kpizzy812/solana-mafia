/**
 * Hook for upgrade modal logic
 */

import { useState, useEffect } from 'react';
import { BUSINESS_TYPES, getBusinessPrice, getDailyYield, getDailyYieldPercent } from '@/data/businesses';
import toast from 'react-hot-toast';
import { BusinessData, UpgradeCalculations } from '../types';

interface UseUpgradeLogicProps {
  businessData: BusinessData | null;
  userBalance: number;
  isOpen: boolean;
  language: 'en' | 'ru';
  onUpgrade: (businessId: string, currentLevel: number, targetLevel: number) => Promise<void>;
  onClose: () => void;
}

export const useUpgradeLogic = ({
  businessData,
  userBalance,
  isOpen,
  language,
  onUpgrade,
  onClose
}: UseUpgradeLogicProps) => {
  const [targetLevel, setTargetLevel] = useState(0);
  const [isUpgrading, setIsUpgrading] = useState(false);

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

  // Calculate all upgrade metrics
  const calculations: UpgradeCalculations = (() => {
    if (!businessData || !businessType) {
      return {
        currentPrice: 0,
        targetPrice: 0,
        upgradeCost: 0,
        currentDailyYield: 0,
        targetDailyYield: 0,
        yieldIncrease: 0,
        currentDailyYieldPercent: 0,
        targetDailyYieldPercent: 0,
        paybackDays: 0,
        canAfford: false,
        canUpgrade: false,
        isMaxLevel: false,
      };
    }

    const currentPrice = getBusinessPrice(businessType, currentLevel);
    const targetPrice = getBusinessPrice(businessType, targetLevel);
    const upgradeCost = targetPrice - currentPrice;

    const currentDailyYield = getDailyYield(businessType, currentLevel);
    const targetDailyYield = getDailyYield(businessType, targetLevel);
    const yieldIncrease = targetDailyYield - currentDailyYield;

    const currentDailyYieldPercent = getDailyYieldPercent(businessType, currentLevel);
    const targetDailyYieldPercent = getDailyYieldPercent(businessType, targetLevel);

    const paybackDays = yieldIncrease > 0 ? Math.ceil(upgradeCost / yieldIncrease) : 0;

    const canAfford = userBalance >= upgradeCost;
    const canUpgrade = currentLevel < maxLevel - 1;
    const isMaxLevel = currentLevel === maxLevel - 1;

    return {
      currentPrice,
      targetPrice,
      upgradeCost,
      currentDailyYield,
      targetDailyYield,
      yieldIncrease,
      currentDailyYieldPercent,
      targetDailyYieldPercent,
      paybackDays,
      canAfford,
      canUpgrade,
      isMaxLevel,
    };
  })();

  const handleUpgrade = async () => {
    if (!calculations.canAfford || !calculations.canUpgrade || isUpgrading || !businessData) return;
    
    setIsUpgrading(true);
    try {
      console.log('🚀 User clicked upgrade button, starting process...', {
        businessId: businessData.businessId,
        currentLevel,
        targetLevel,
        upgradeCost: calculations.upgradeCost.toFixed(3) + ' SOL',
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

  return {
    targetLevel,
    setTargetLevel,
    isUpgrading,
    businessType,
    currentLevel,
    maxLevel,
    calculations,
    handleUpgrade,
  };
};
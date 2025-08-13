/**
 * Types for UpgradeModal components
 */

export interface BusinessData {
  businessId: string;
  businessType: number;
  level: number;
  totalInvestedAmount: number;
  earningsPerHour: number;
  slotIndex: number;
  isActive: boolean;
  name: string;
}

export interface UpgradeModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpgrade: (businessId: string, currentLevel: number, targetLevel: number) => Promise<void>;
  businessData: BusinessData | null;
  userBalance?: number; // in SOL
  language?: 'en' | 'ru';
}

export interface UpgradeCalculations {
  currentPrice: number;
  targetPrice: number;
  upgradeCost: number;
  currentDailyYield: number;
  targetDailyYield: number;
  yieldIncrease: number;
  currentDailyYieldPercent: number;
  targetDailyYieldPercent: number;
  paybackDays: number;
  canAfford: boolean;
  canUpgrade: boolean;
  isMaxLevel: boolean;
}
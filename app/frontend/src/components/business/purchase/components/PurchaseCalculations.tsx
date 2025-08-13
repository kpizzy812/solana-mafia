/**
 * Purchase calculations display component
 */

import React from 'react';
import { TrendingUp, DollarSign, Clock, AlertTriangle, Wallet } from 'lucide-react';
import { InfoTooltip } from '@/components/ui/InfoTooltip';
import { useTranslation } from '@/locales';
import { PurchaseCalculation, SlotData } from '../types';
import { getSlotInfo } from '@/data/slots';

interface PurchaseCalculationsProps {
  calculations: PurchaseCalculation;
  selectedSlotData: SlotData | undefined;
  userBalance: number;
  isNewPlayer: boolean;
  entryFee: number;
  language: 'en' | 'ru';
}

export const PurchaseCalculations: React.FC<PurchaseCalculationsProps> = ({
  calculations,
  selectedSlotData,
  userBalance,
  isNewPlayer,
  entryFee,
  language
}) => {
  const t = useTranslation(language);
  const slotInfo = selectedSlotData ? getSlotInfo(selectedSlotData.type) : null;

  return (
    <div className="space-y-4 mb-6">
      {/* Cost breakdown */}
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <DollarSign className="w-4 h-4 text-green-400" />
          <span className="text-sm font-medium text-white">{t.cost_breakdown}</span>
        </div>
        
        <div className="space-y-2 text-sm">
          <div className="flex justify-between text-gray-300">
            <span>{t.business_cost}:</span>
            <span>{calculations.businessPrice.toFixed(4)} SOL</span>
          </div>
          
          {isNewPlayer && entryFee > 0 && (
            <div className="flex justify-between text-gray-300">
              <span>{t.entry_fee}:</span>
              <span>{entryFee.toFixed(4)} SOL</span>
            </div>
          )}
          
          <div className="border-t border-gray-600 pt-2 flex justify-between text-white font-medium">
            <span>{t.total_cost}:</span>
            <span>{calculations.totalCost.toFixed(4)} SOL</span>
          </div>
        </div>
      </div>

      {/* Yield information */}
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <TrendingUp className="w-4 h-4 text-blue-400" />
          <span className="text-sm font-medium text-white">{t.daily_yield}</span>
          <InfoTooltip content={t.yield_explanation} />
        </div>
        
        <div className="space-y-2 text-sm">
          <div className="flex justify-between text-gray-300">
            <span>{t.base_yield}:</span>
            <span>{calculations.baseDailyYield.toFixed(4)} SOL ({calculations.baseDailyYieldPercent.toFixed(2)}%)</span>
          </div>
          
          {slotInfo && slotInfo.yieldBonus > 0 && (
            <div className="flex justify-between text-green-400">
              <span>{slotInfo.name[language]} {t.bonus}:</span>
              <span>+{(slotInfo.yieldBonus / 100).toFixed(1)}%</span>
            </div>
          )}
          
          <div className="border-t border-gray-600 pt-2 flex justify-between text-white font-medium">
            <span>{t.final_yield}:</span>
            <span>{calculations.dailyYield.toFixed(4)} SOL ({calculations.dailyYieldPercent.toFixed(2)}%)</span>
          </div>
        </div>
      </div>

      {/* ROI calculation */}
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <Clock className="w-4 h-4 text-yellow-400" />
          <span className="text-sm font-medium text-white">{t.return_on_investment}</span>
          <InfoTooltip content={t.roi_explanation} />
        </div>
        
        <div className="text-sm text-gray-300">
          {calculations.dailyYield > 0 && (
            <div className="flex justify-between">
              <span>{t.payback_period}:</span>
              <span>{Math.ceil(calculations.totalCost / calculations.dailyYield)} {t.days}</span>
            </div>
          )}
        </div>
      </div>

      {/* Balance check */}
      <div className="bg-gray-800 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <Wallet className="w-4 h-4 text-purple-400" />
          <span className="text-sm font-medium text-white">{t.your_balance}</span>
        </div>
        
        <div className="flex justify-between text-sm">
          <span className="text-gray-300">{t.current_balance}:</span>
          <span className="text-white">{userBalance.toFixed(4)} SOL</span>
        </div>
        
        {!calculations.canAfford && (
          <div className="flex items-center gap-2 mt-2 text-red-400 text-sm">
            <AlertTriangle className="w-4 h-4" />
            <span>{t.insufficient_funds}</span>
          </div>
        )}
      </div>
    </div>
  );
};
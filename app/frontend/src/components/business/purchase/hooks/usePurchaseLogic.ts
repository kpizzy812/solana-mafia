/**
 * Custom hook for purchase modal business logic
 */

import { useState, useEffect } from 'react';
import { BUSINESS_TYPES, getBusinessPrice, getDailyYield, getDailyYieldPercent, getBaseDailyYieldPercent } from '@/data/businesses';
import { getSlotInfo, calculateSlotYieldBonus, SlotType } from '@/data/slots';
import { SlotData, PurchaseCalculation } from '../types';

interface UsePurchaseLogicProps {
  availableSlots: SlotData[];
  userBalance: number;
  isNewPlayer: boolean;
  entryFee: number;
}

export const usePurchaseLogic = ({
  availableSlots,
  userBalance,
  isNewPlayer,
  entryFee
}: UsePurchaseLogicProps) => {
  const [selectedBusinessIndex, setSelectedBusinessIndex] = useState(0);
  const [selectedLevel, setSelectedLevel] = useState(0);
  const [selectedSlot, setSelectedSlot] = useState(0);
  const [showHint, setShowHint] = useState(false);
  const [isPurchasing, setIsPurchasing] = useState(false);

  // Ensure selected slot is valid and available
  useEffect(() => {
    if (availableSlots.length > 0) {
      const currentSlot = availableSlots.find(slot => slot.index === selectedSlot);
      
      // If current slot doesn't exist, is locked, or is occupied, find first available slot
      if (!currentSlot || !currentSlot.isUnlocked || currentSlot.business) {
        const firstAvailableSlot = availableSlots.find(slot => slot.isUnlocked && !slot.business);
        if (firstAvailableSlot) {
          setSelectedSlot(firstAvailableSlot.index);
        }
      }
    }
  }, [availableSlots, selectedSlot]);

  // Calculate purchase details
  const selectedBusiness = BUSINESS_TYPES[selectedBusinessIndex];
  const businessPrice = getBusinessPrice(selectedBusiness, selectedLevel);
  const baseDailyYield = getDailyYield(selectedBusiness, selectedLevel);
  // 🆕 ИСПРАВЛЕНИЕ: Используем базовый процент (не изменяется при улучшениях)
  const baseDailyYieldPercent = getBaseDailyYieldPercent(selectedBusiness);
  
  // Calculate yield with slot bonus
  const selectedSlotData = availableSlots.find(slot => slot.index === selectedSlot);
  const slotInfo = selectedSlotData ? getSlotInfo(selectedSlotData.type) : getSlotInfo(SlotType.Basic);
  
  // 🔧 ИСПРАВЛЕНИЕ: Слоты 3-5 (Basic платные) НЕ дают бонуса доходности!
  const isBasicPaidSlot = selectedSlotData && selectedSlotData.type === SlotType.Basic && selectedSlotData.index >= 3 && selectedSlotData.index <= 5;
  const effectiveYieldBonus = isBasicPaidSlot ? 0 : slotInfo.yieldBonus;
  
  const dailyYield = baseDailyYield * (1 + effectiveYieldBonus / 10000);
  const dailyYieldPercent = baseDailyYieldPercent + (effectiveYieldBonus / 100);
  
  // Calculate slot cost based on slot type and business price
  let slotCost = 0;
  if (selectedSlotData) {
    if (selectedSlotData.type === SlotType.Basic && selectedSlotData.index >= 3) {
      // Basic slots 3-5 cost 10% of business price (но НЕ дают бонуса доходности!)
      slotCost = businessPrice * 0.1;
    } else if (selectedSlotData.type !== SlotType.Basic) {
      // Premium slots have fixed costs
      slotCost = slotInfo.cost;
    }
  }
  
  const totalPrice = businessPrice + slotCost;
  const totalCost = totalPrice + (isNewPlayer ? entryFee : 0);
  const canAfford = userBalance >= totalCost;

  const calculations: PurchaseCalculation = {
    businessPrice,
    slotCost,
    totalPrice,
    baseDailyYield,
    baseDailyYieldPercent,
    dailyYield,
    dailyYieldPercent,
    totalCost,
    canAfford
  };

  // Show hint animation
  const showHintAnimation = (isOpen: boolean) => {
    if (isOpen) {
      const timer = setTimeout(() => {
        setShowHint(true);
        const hideTimer = setTimeout(() => setShowHint(false), 3000);
        return () => clearTimeout(hideTimer);
      }, 1000);
      return () => clearTimeout(timer);
    } else {
      setShowHint(false);
    }
  };

  return {
    // State
    selectedBusinessIndex,
    selectedLevel,
    selectedSlot,
    showHint,
    isPurchasing,
    
    // Setters
    setSelectedBusinessIndex,
    setSelectedLevel,
    setSelectedSlot,
    setIsPurchasing,
    showHintAnimation,
    
    // Computed values
    selectedBusiness,
    selectedSlotData,
    slotInfo,
    calculations
  };
};
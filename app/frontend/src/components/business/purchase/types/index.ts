/**
 * Types for Purchase Modal components
 */

import { SlotType } from '@/data/slots';

export interface SlotData {
  index: number;
  type: SlotType;
  isUnlocked: boolean;
  business?: any; // Existing business in slot
}

export interface PurchaseModalProps {
  isOpen: boolean;
  onClose: () => void;
  onPurchase: (businessTypeId: number, slotIndex: number, level?: number) => Promise<void>;
  availableSlots: SlotData[]; // Changed from number to detailed slot data
  userBalance?: number; // in SOL
  language?: 'en' | 'ru';
  isNewPlayer?: boolean; // Whether this is a new player who needs to pay entry fee
  entryFee?: number; // Entry fee in SOL for new players
}

export interface PurchaseCalculation {
  businessPrice: number;
  slotCost: number; // Cost of the selected slot
  totalPrice: number; // businessPrice + slotCost
  baseDailyYield: number;
  baseDailyYieldPercent: number;
  dailyYield: number;
  dailyYieldPercent: number;
  totalCost: number; // totalPrice + entryFee if new player
  canAfford: boolean;
}
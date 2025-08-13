/**
 * Types for the main app page
 */

import { SlotType } from '@/data/slots';

export interface SlotData {
  index: number;
  type: SlotType;
  isUnlocked: boolean;
  business?: any;
}

export interface FomoData {
  totalPlayers: number;
  currentEntryFee: number;
  currentEntryFeeUsd: number;
  solPriceUsd: number;
  lastUpdated: string | null;
}

export interface PlayerStats {
  totalEarnings: number;
  businessCount: number;
  businessSlots: number;
  totalSlots: number;
  earningsBalance: number;
}

export interface BusinessData {
  id: string;
  name: string;
  level: number;
  earning: number;
  totalEarned: number;
  businessPrice: number;
  dailyYieldPercent: number;
  imageUrl?: string;
  levelName?: string;
  levelDescription?: string;
  needsSync: boolean;
  businessData: {
    businessId: string;
    slotIndex: number;
    businessType: string;
    level: number;
    totalInvestedAmount: number;
    earningsPerHour: number;
    isActive: boolean;
    createdAt?: number; // Unix timestamp when business was created
  };
}

export interface AppPageProps {
  language: 'en' | 'ru';
  connected: boolean;
  publicKey: any;
  wallet: any;
}
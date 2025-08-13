// Slot types and configurations matching the smart contract

export enum SlotType {
  Basic = 'Basic',
  Premium = 'Premium', 
  VIP = 'VIP',
  Legendary = 'Legendary'
}

export interface SlotInfo {
  type: SlotType;
  name: string;
  description: string;
  cost: number; // in SOL
  yieldBonus: number; // in basis points
  sellFeeDiscount: number; // in percentage
  icon: string;
  gradient: string;
  rarity: 'common' | 'rare' | 'epic' | 'legendary';
}

export const SLOT_TYPES: SlotInfo[] = [
  {
    type: SlotType.Basic,
    name: 'Basic Slot',
    description: 'Standard business slot with no bonuses',
    cost: 0,
    yieldBonus: 0,
    sellFeeDiscount: 0,
    icon: '🏪',
    gradient: 'from-gray-400 to-gray-600',
    rarity: 'common'
  },
  {
    type: SlotType.Premium,
    name: 'Premium',
    description: '+0.5% yield bonus for businesses placed here',
    cost: 1, // 1 SOL - updated cost
    yieldBonus: 50, // +0.5% - matches PREMIUM_SLOT_YIELD_BONUSES[0]
    sellFeeDiscount: 0, // 0% - matches PREMIUM_SLOT_SELL_FEE_DISCOUNTS[0]
    icon: '💎',
    gradient: 'from-blue-400 to-blue-600',
    rarity: 'rare'
  },
  {
    type: SlotType.VIP,
    name: 'VIP',
    description: '+1% yield bonus, -50% selling fees',
    cost: 2, // 2 SOL - updated cost
    yieldBonus: 100, // +1% - matches PREMIUM_SLOT_YIELD_BONUSES[1]
    sellFeeDiscount: 50, // -50% - matches PREMIUM_SLOT_SELL_FEE_DISCOUNTS[1]
    icon: '👑',
    gradient: 'from-purple-400 to-purple-600',
    rarity: 'epic'
  },
  {
    type: SlotType.Legendary,
    name: 'Legendary',
    description: '+2% yield bonus, -100% selling fees',
    cost: 5, // 5 SOL - updated cost
    yieldBonus: 200, // +2% - matches PREMIUM_SLOT_YIELD_BONUSES[2]
    sellFeeDiscount: 100, // -100% - matches PREMIUM_SLOT_SELL_FEE_DISCOUNTS[2]
    icon: '🌟',
    gradient: 'from-yellow-400 to-orange-600',
    rarity: 'legendary'
  }
];

// Helper functions
export const getSlotInfo = (slotType: SlotType): SlotInfo => {
  return SLOT_TYPES.find(slot => slot.type === slotType) || SLOT_TYPES[0];
};

export const calculateSlotYieldBonus = (baseYield: number, slotType: SlotType): number => {
  const slotInfo = getSlotInfo(slotType);
  return baseYield * (1 + slotInfo.yieldBonus / 10000);
};

export const getSlotRarityColor = (rarity: 'common' | 'rare' | 'epic' | 'legendary'): string => {
  switch (rarity) {
    case 'common': return 'text-gray-500 border-gray-500';
    case 'rare': return 'text-blue-500 border-blue-500';
    case 'epic': return 'text-purple-500 border-purple-500';
    case 'legendary': return 'text-yellow-500 border-yellow-500';
  }
};
// Business data matching the smart contract constants
export interface BusinessType {
  id: number;
  name: string;
  description: string;
  emoji: string;
  basePrice: number; // in SOL
  baseDailyRate: number; // in basis points (e.g., 80 = 0.8%)
  levels: {
    level: number;
    name: string;
    description: string;
    priceMultiplier: number; // multiplier from base price
    rateBonus: number; // bonus in basis points
    imageUrl?: string;
  }[];
}

// Data from smart contract constants
export const BUSINESS_TYPES: BusinessType[] = [
  {
    id: 0,
    name: "Lucky Strike Cigars",
    description: "A tobacco shop that serves as the perfect cover for family business operations.",
    emoji: "🚬",
    basePrice: 0.1, // 100_000_000 lamports = 0.1 SOL
    baseDailyRate: 200, // 2.0%
    levels: [
      {
        level: 0,
        name: "Corner Stand",
        description: "A humble kiosk that serves as the perfect cover for family business operations.",
        priceMultiplier: 1.0,
        rateBonus: 0,
        imageUrl: "/nft-images/tobacco/level_0_corner_stand.png"
      },
      {
        level: 1,
        name: "Smoke & Secrets",
        description: "Back room operations begin to take shape.",
        priceMultiplier: 1.2,
        rateBonus: 10,
        imageUrl: "/nft-images/tobacco/level_1_smoke_and_secrets.png"
      },
      {
        level: 2,
        name: "Cigar Lounge",
        description: "Elite club for the chosen ones.",
        priceMultiplier: 1.5,
        rateBonus: 25,
        imageUrl: "/nft-images/tobacco/level_2_cigar_lounge.png"
      },
      {
        level: 3,
        name: "Empire of Smoke",
        description: "Citywide network of operations.",
        priceMultiplier: 2.0,
        rateBonus: 50,
        imageUrl: "/nft-images/tobacco/level_3_empire_of_smoke.png"
      }
    ]
  },
  {
    id: 1,
    name: "Eternal Rest Funeral",
    description: "A funeral parlor providing discreet services for those who need to 'disappear'.",
    emoji: "⚰️",
    basePrice: 0.5, // 500_000_000 lamports = 0.5 SOL
    baseDailyRate: 180, // 1.8%
    levels: [
      {
        level: 0,
        name: "Quiet Departure",
        description: "Simple funeral services with no questions asked.",
        priceMultiplier: 1.0,
        rateBonus: 0,
        imageUrl: "/nft-images/funeral/level_0_quiet_departure.png"
      },
      {
        level: 1,
        name: "Silent Service",
        description: "Premium services for sensitive situations.",
        priceMultiplier: 1.2,
        rateBonus: 10,
        imageUrl: "/nft-images/funeral/level_1_silent_service.png"
      },
      {
        level: 2,
        name: "Final Solution",
        description: "VIP funerals for the most elite clients.",
        priceMultiplier: 1.5,
        rateBonus: 25,
        imageUrl: "/nft-images/funeral/level_2_final_solution.png"
      },
      {
        level: 3,
        name: "Legacy of Silence",
        description: "Empire of silence spanning the entire city.",
        priceMultiplier: 2.0,
        rateBonus: 50,
        imageUrl: "/nft-images/funeral/level_3_legacy_of_silence.png"
      }
    ]
  },
  {
    id: 2,
    name: "Midnight Motors Garage",
    description: "An auto shop specializing in untraceable vehicle modifications.",
    emoji: "🔧",
    basePrice: 2.0, // 2_000_000_000 lamports = 2.0 SOL
    baseDailyRate: 160, // 1.6%
    levels: [
      {
        level: 0,
        name: "Street Repair",
        description: "Regular automotive workshop services.",
        priceMultiplier: 1.0,
        rateBonus: 0,
        imageUrl: "/nft-images/car/level_0_street_repair.png"
      },
      {
        level: 1,
        name: "Custom Works",
        description: "Tuning and special modifications available.",
        priceMultiplier: 1.2,
        rateBonus: 10,
        imageUrl: "/nft-images/car/level_1_custom_works.png"
      },
      {
        level: 2,
        name: "Underground Garage",
        description: "Secret conversions and untraceable work.",
        priceMultiplier: 1.5,
        rateBonus: 25,
        imageUrl: "/nft-images/car/level_2_underground_garage.png"
      },
      {
        level: 3,
        name: "Ghost Fleet",
        description: "Empire of invisible vehicles across the city.",
        priceMultiplier: 2.0,
        rateBonus: 50,
        imageUrl: "/nft-images/car/level_3_ghost_fleet.png"
      }
    ]
  },
  {
    id: 3,
    name: "Nonna's Secret Kitchen",
    description: "An Italian restaurant where important family meetings take place.",
    emoji: "🍝",
    basePrice: 5.0, // 5_000_000_000 lamports = 5.0 SOL
    baseDailyRate: 140, // 1.4%
    levels: [
      {
        level: 0,
        name: "Family Recipe",
        description: "Home kitchen serving traditional dishes.",
        priceMultiplier: 1.0,
        rateBonus: 0,
        imageUrl: "/nft-images/restaurant/level_0_family_recipe.png"
      },
      {
        level: 1,
        name: "Mama's Table",
        description: "Popular trattoria in the neighborhood.",
        priceMultiplier: 1.2,
        rateBonus: 10,
        imageUrl: "/nft-images/restaurant/level_1_mama's_table.png"
      },
      {
        level: 2,
        name: "Don's Dining",
        description: "Restaurant for important family meetings.",
        priceMultiplier: 1.5,
        rateBonus: 25,
        imageUrl: "/nft-images/restaurant/level_2_don's_dining.png"
      },
      {
        level: 3,
        name: "Empire Feast",
        description: "Network of cover restaurants across the city.",
        priceMultiplier: 2.0,
        rateBonus: 50,
        imageUrl: "/nft-images/restaurant/level_3_empire_feast.png"
      }
    ]
  },
  {
    id: 4,
    name: "Velvet Shadows Club",
    description: "An elite club for conducting exclusive 'family business'.",
    emoji: "🥃",
    basePrice: 10.0, // 10_000_000_000 lamports = 10.0 SOL
    baseDailyRate: 120, // 1.2%
    levels: [
      {
        level: 0,
        name: "Private Room",
        description: "Closed room for discrete meetings.",
        priceMultiplier: 1.0,
        rateBonus: 0,
        imageUrl: "/nft-images/club/level_0_private_room.png"
      },
      {
        level: 1,
        name: "Exclusive Lounge",
        description: "VIP zone for important guests.",
        priceMultiplier: 1.2,
        rateBonus: 10,
        imageUrl: "/nft-images/club/level_1_exclusive_lounge.png"
      },
      {
        level: 2,
        name: "Shadow Society",
        description: "Secret society for the most influential.",
        priceMultiplier: 1.5,
        rateBonus: 25,
        imageUrl: "/nft-images/club/level_2_shadow_society.png"
      },
      {
        level: 3,
        name: "Velvet Empire",
        description: "Network of influential clubs across the city.",
        priceMultiplier: 2.0,
        rateBonus: 50,
        imageUrl: "/nft-images/club/level_3_velvet_empire.png"
      }
    ]
  },
  {
    id: 5,
    name: "Angel's Mercy Foundation",
    description: "A charity foundation providing 'assistance' to those in need.",
    emoji: "👼",
    basePrice: 50.0, // 50_000_000_000 lamports = 50.0 SOL
    baseDailyRate: 100, // 1.0%
    levels: [
      {
        level: 0,
        name: "Helping Hand",
        description: "Local charity providing community assistance.",
        priceMultiplier: 1.0,
        rateBonus: 0,
        imageUrl: "/nft-images/charity/level_0_helping_hand.png"
      },
      {
        level: 1,
        name: "Guardian Angel",
        description: "Major donations and community influence.",
        priceMultiplier: 1.2,
        rateBonus: 10,
        imageUrl: "/nft-images/charity/level_1_guardian_angel.png"
      },
      {
        level: 2,
        name: "Divine Intervention",
        description: "International foundation with global reach.",
        priceMultiplier: 1.5,
        rateBonus: 25,
        imageUrl: "/nft-images/charity/level_2_divine_intervention.png"
      },
      {
        level: 3,
        name: "Mercy Empire",
        description: "Global 'assistance' network spanning continents.",
        priceMultiplier: 2.0,
        rateBonus: 50,
        imageUrl: "/nft-images/charity/level_3_mercy_empire.png"
      }
    ]
  }
];

// Helper functions
export const getBusinessPrice = (businessType: BusinessType, level: number = 0): number => {
  const levelData = businessType.levels[level];
  return businessType.basePrice * levelData.priceMultiplier;
};

export const getDailyYield = (businessType: BusinessType, level: number = 0): number => {
  // 🔧 ИСПРАВЛЕНИЕ: Ставка не меняется, меняется только сумма инвестирования!
  const baseRate = businessType.baseDailyRate; // Всегда базовая ставка
  const price = getBusinessPrice(businessType, level); // Сумма увеличивается с уровнем
  return (price * baseRate) / 10000; // Доход = большая_сумма * базовая_ставка
};

export const getDailyYieldPercent = (businessType: BusinessType, level: number = 0): number => {
  // 🔧 ИСПРАВЛЕНИЕ: Процентная ставка всегда базовая, не зависит от уровня!
  return businessType.baseDailyRate / 100; // Всегда 2.0% для TobaccoShop
};

// 🆕 Новая функция: возвращает базовый процент (остается постоянным при улучшениях)
export const getBaseDailyYieldPercent = (businessType: BusinessType): number => {
  return businessType.baseDailyRate / 100;
};
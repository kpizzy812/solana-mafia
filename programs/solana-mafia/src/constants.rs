// constants.rs
use anchor_lang::prelude::*;

// ============================================================================
// BUSINESS CONFIGURATION
// ============================================================================

/// Количество типов бизнесов
pub const BUSINESS_TYPES_COUNT: usize = 6;

/// Минимальные депозиты в lamports (базовые цены)
pub const MIN_DEPOSITS: [u64; 6] = [
    100_000_000,   // 0.1 SOL - TobaccoShop
    500_000_000,   // 0.5 SOL - FuneralService  
    2_000_000_000, // 2 SOL - CarWorkshop
    100_000_000,   // 0.1 SOL - ItalianRestaurant 
    500_000_000,   // 0.5 SOL - GentlemenClub
    2_000_000_000, // 2 SOL - CharityFund
];

/// Дневные ставки в базисных пунктах (базовые доходности)
pub const BUSINESS_RATES: [u16; 6] = [80, 90, 100, 80, 90, 100]; // 0.8%-1.0%

// ============================================================================
// UPGRADE SYSTEM - НОВАЯ МОДЕЛЬ
// ============================================================================

/// Максимальный уровень улучшения для каждого бизнеса
pub const MAX_UPGRADE_LEVEL: u8 = 3;

/// Множители стоимости улучшений (% от базовой стоимости бизнеса)
pub const UPGRADE_COST_MULTIPLIERS: [u8; 3] = [20, 50, 100]; // 20%, 50%, 100%

/// Бонусы доходности за каждый уровень улучшения (в базисных пунктах)
pub const UPGRADE_YIELD_BONUSES: [u16; 3] = [10, 25, 50]; // +0.1%, +0.25%, +0.5%

// ============================================================================
// SLOT SYSTEM - НОВАЯ СИСТЕМА СЛОТОВ
// ============================================================================

/// Количество базовых слотов (бесплатные)
pub const BASE_BUSINESS_SLOTS: u8 = 3;

/// Максимальное количество обычных слотов
pub const MAX_REGULAR_SLOTS: u8 = 6; // 3 базовых + 3 донатных

/// Множитель стоимости дополнительных слотов (% от стоимости бизнеса в слоте)
pub const SLOT_UNLOCK_COST_MULTIPLIER: u8 = 10; // 10% от стоимости

/// Типы слотов
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Debug, PartialEq)]
pub enum SlotType {
    Basic,           // Обычный слот (базовые 3 + разблокированные)
    Premium,         // +15% к доходности, стоимость: 5 SOL
    VIP,             // +30% к доходности, -50% комиссия продажи, стоимость: 25 SOL
    Legendary,       // +50% к доходности, нет комиссии продажи, стоимость: 100 SOL
}

/// Стоимость премиум слотов
pub const PREMIUM_SLOT_COSTS: [u64; 3] = [
    5_000_000_000,   // Premium: 5 SOL
    25_000_000_000,  // VIP: 25 SOL  
    100_000_000_000, // Legendary: 100 SOL
];

/// Бонусы доходности для премиум слотов
pub const PREMIUM_SLOT_YIELD_BONUSES: [u16; 3] = [150, 300, 500]; // +1.5%, +3%, +5%

/// Скидки на комиссию продажи для премиум слотов
pub const PREMIUM_SLOT_SELL_FEE_DISCOUNTS: [u8; 3] = [0, 50, 100]; // 0%, -50%, -100%

// ============================================================================
// NFT UPGRADE SYSTEM
// ============================================================================

/// Префиксы для разных уровней NFT
pub const NFT_LEVEL_NAMES: [&str; 4] = [
    "Basic",      // Уровень 0
    "Advanced",   // Уровень 1
    "Elite",      // Уровень 2
    "Legendary",  // Уровень 3
];

/// URI для разных уровней NFT (будут разные изображения)
pub const BUSINESS_NFT_URIS_BY_LEVEL: [[&str; 4]; 6] = [
    // TobaccoShop
    [
        "https://solana-mafia.com/nft/tobacco_basic.json",
        "https://solana-mafia.com/nft/tobacco_advanced.json", 
        "https://solana-mafia.com/nft/tobacco_elite.json",
        "https://solana-mafia.com/nft/tobacco_legendary.json",
    ],
    // FuneralService
    [
        "https://solana-mafia.com/nft/funeral_basic.json",
        "https://solana-mafia.com/nft/funeral_advanced.json",
        "https://solana-mafia.com/nft/funeral_elite.json", 
        "https://solana-mafia.com/nft/funeral_legendary.json",
    ],
    // Остальные типы аналогично...
    [
        "https://solana-mafia.com/nft/car_basic.json",
        "https://solana-mafia.com/nft/car_advanced.json",
        "https://solana-mafia.com/nft/car_elite.json",
        "https://solana-mafia.com/nft/car_legendary.json",
    ],
    [
        "https://solana-mafia.com/nft/restaurant_basic.json",
        "https://solana-mafia.com/nft/restaurant_advanced.json",
        "https://solana-mafia.com/nft/restaurant_elite.json",
        "https://solana-mafia.com/nft/restaurant_legendary.json",
    ],
    [
        "https://solana-mafia.com/nft/club_basic.json",
        "https://solana-mafia.com/nft/club_advanced.json",
        "https://solana-mafia.com/nft/club_elite.json",
        "https://solana-mafia.com/nft/club_legendary.json",
    ],
    [
        "https://solana-mafia.com/nft/charity_basic.json",
        "https://solana-mafia.com/nft/charity_advanced.json",
        "https://solana-mafia.com/nft/charity_elite.json",
        "https://solana-mafia.com/nft/charity_legendary.json",
    ],
];

// ============================================================================
// SELL FEES - БЕЗ ИЗМЕНЕНИЙ
// ============================================================================

/// Early sell fees by days held (убывающая комиссия)
pub const EARLY_SELL_FEES: [u8; 32] = [
    25, 25, 25, 25, 25, 25, 25, // Days 0-6: 25%
    20, 20, 20, 20, 20, 20, 20, // Days 7-13: 20%
    15, 15, 15, 15, 15, 15, 15, // Days 14-20: 15%
    10, 10, 10, 10, 10, 10, 10, // Days 21-27: 10%
    5,  5,  5,  2,              // Days 28-30: 5%, final: 2%
];

pub const FINAL_SELL_FEE_PERCENT: u8 = 2;

// ============================================================================
// NFT METADATA CONSTANTS
// ============================================================================

/// Business names for NFTs
pub const BUSINESS_NFT_NAMES: [&str; 6] = [
    "Tobacco Shop",
    "Funeral Service", 
    "Car Workshop",
    "Italian Restaurant",
    "Gentlemen Club",
    "Charity Fund",
];

/// Collection symbol
pub const NFT_COLLECTION_SYMBOL: &str = "MAFIA";

// Placeholder URIs - will be replaced with actual metadata
pub const BUSINESS_NFT_URIS: [&str; 6] = [
    "https://solana-mafia.com/nft/tobacco_basic.json",
    "https://solana-mafia.com/nft/funeral_basic.json",
    "https://solana-mafia.com/nft/car_basic.json",
    "https://solana-mafia.com/nft/restaurant_basic.json",
    "https://solana-mafia.com/nft/club_basic.json",
    "https://solana-mafia.com/nft/charity_basic.json",
];

// ============================================================================
// GAME CONFIGURATION CONSTANTS
// ============================================================================

/// Entry fee to join the game (0.01 SOL)
pub const ENTRY_FEE: u64 = 10_000_000; // 0.01 SOL

/// Treasury fee percentage
pub const TREASURY_FEE_PERCENT: u8 = 10; // 10%

/// Upgrade costs (legacy - using multipliers now)
pub const UPGRADE_COSTS: [u64; 3] = [
    100_000_000,   // 0.1 SOL for level 1
    500_000_000,   // 0.5 SOL for level 2
    2_000_000_000, // 2 SOL for level 3
];

/// Upgrade bonuses (legacy - using UPGRADE_YIELD_BONUSES now)
pub const UPGRADE_BONUSES: [u16; 3] = UPGRADE_YIELD_BONUSES;

/// Referral rates for each level
pub const REFERRAL_RATES: [u8; 3] = [5, 3, 2]; // 5%, 3%, 2%

/// Maximum referral levels
pub const MAX_REFERRAL_LEVELS: usize = 3;

// ============================================================================
// COMPATIBILITY CONSTANTS  
// ============================================================================

/// Maximum businesses per player (legacy)
pub const MAX_BUSINESSES_PER_PLAYER: u8 = 20;

// ============================================================================
// PDA SEEDS
// ============================================================================

pub const GAME_STATE_SEED: &[u8] = b"game_state";
pub const GAME_CONFIG_SEED: &[u8] = b"game_config"; 
pub const TREASURY_SEED: &[u8] = b"treasury";
pub const PLAYER_SEED: &[u8] = b"player";
pub const BUSINESS_NFT_SEED: &[u8] = b"business_nft";
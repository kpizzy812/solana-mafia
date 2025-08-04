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

/// URI for different NFT levels with mafia themed names
pub const BUSINESS_NFT_URIS_BY_LEVEL: [[&str; 4]; 6] = [
    // Lucky Strike Cigars - tobacco shop with secrets
    [
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/lucky_strike_cigars_corner_stand.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/lucky_strike_cigars_smoke_secrets.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/lucky_strike_cigars_cigar_lounge.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/lucky_strike_cigars_empire_of_smoke.json",
    ],
    // Eternal Rest Funeral - funeral parlor for "disappearances"
    [
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/eternal_rest_funeral_quiet_departure.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/eternal_rest_funeral_silent_service.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/eternal_rest_funeral_final_solution.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/eternal_rest_funeral_legacy_of_silence.json",
    ],
    // Midnight Motors Garage - auto shop for untraceable vehicles
    [
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/midnight_motors_garage_street_repair.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/midnight_motors_garage_custom_works.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/midnight_motors_garage_underground_garage.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/midnight_motors_garage_ghost_fleet.json",
    ],
    // Nonna's Secret Kitchen - Italian restaurant for operation planning
    [
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/nonnas_secret_kitchen_family_recipe.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/nonnas_secret_kitchen_mamas_table.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/nonnas_secret_kitchen_dons_dining.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/nonnas_secret_kitchen_empire_feast.json",
    ],
    // Velvet Shadows Club - elite club for "family business"
    [
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/velvet_shadows_club_private_room.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/velvet_shadows_club_exclusive_lounge.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/velvet_shadows_club_shadow_society.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/velvet_shadows_club_velvet_empire.json",
    ],
    // Angel's Mercy Foundation - charity foundation for "assistance"
    [
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/angels_mercy_foundation_helping_hand.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/angels_mercy_foundation_guardian_angel.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/angels_mercy_foundation_divine_intervention.json",
        "https://raw.githubusercontent.com/kpizzy812/solana-mafia/main/metadata/nft/angels_mercy_foundation_mercy_empire.json",
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

/// Business names for NFTs - Mafia themed business names
pub const BUSINESS_NFT_NAMES: [&str; 6] = [
    "Lucky Strike Cigars",      // Family tobacco shop with secrets
    "Eternal Rest Funeral",     // Funeral parlor for "disappearances"
    "Midnight Motors Garage",   // Auto shop for untraceable vehicles
    "Nonna's Secret Kitchen",   // Italian restaurant for operation planning
    "Velvet Shadows Club",      // Elite club for "family business"
    "Angel's Mercy Foundation", // Charity foundation for "assistance"
];

/// Collection symbol
pub const NFT_COLLECTION_SYMBOL: &str = "MAFIA";

/// Upgrade names for each business type [business][level]
/// Each business has unique progression from basic to legendary level
pub const BUSINESS_UPGRADE_NAMES: [[&str; 4]; 6] = [
    // Lucky Strike Cigars - tobacco shop with secrets
    [
        "Corner Stand",        // Level 0: humble kiosk
        "Smoke & Secrets",     // Level 1: back room appears
        "Cigar Lounge",        // Level 2: elite club for chosen ones
        "Empire of Smoke",     // Level 3: citywide network
    ],
    // Eternal Rest Funeral - funeral parlor for "disappearances"
    [
        "Quiet Departure",     // Level 0: simple funerals
        "Silent Service",      // Level 1: premium services
        "Final Solution",      // Level 2: VIP funerals for elite
        "Legacy of Silence",   // Level 3: empire of silence
    ],
    // Midnight Motors Garage - auto shop for untraceable vehicles
    [
        "Street Repair",       // Level 0: regular workshop
        "Custom Works",        // Level 1: tuning and modifications
        "Underground Garage",  // Level 2: secret conversions
        "Ghost Fleet",         // Level 3: empire of invisible cars
    ],
    // Nonna's Secret Kitchen - Italian restaurant for operation planning
    [
        "Family Recipe",       // Level 0: home kitchen
        "Mama's Table",        // Level 1: popular trattoria
        "Don's Dining",        // Level 2: restaurant for important meetings
        "Empire Feast",        // Level 3: network of cover restaurants
    ],
    // Velvet Shadows Club - elite club for "family business"
    [
        "Private Room",        // Level 0: closed room
        "Exclusive Lounge",    // Level 1: VIP zone
        "Shadow Society",      // Level 2: secret society
        "Velvet Empire",       // Level 3: network of influential clubs
    ],
    // Angel's Mercy Foundation - charity foundation for "assistance"
    [
        "Helping Hand",        // Level 0: local charity
        "Guardian Angel",      // Level 1: major donations
        "Divine Intervention", // Level 2: international foundation
        "Mercy Empire",        // Level 3: global "assistance" network
    ],
];

// Legacy base URIs (for compatibility)
pub const BUSINESS_NFT_URIS: [&str; 6] = [
    "https://solana-mafia.com/nft/cigars_corner_stand.json",     // Lucky Strike Cigars
    "https://solana-mafia.com/nft/funeral_quiet_departure.json", // Eternal Rest Funeral
    "https://solana-mafia.com/nft/motors_street_repair.json",    // Midnight Motors Garage
    "https://solana-mafia.com/nft/kitchen_family_recipe.json",   // Nonna's Secret Kitchen
    "https://solana-mafia.com/nft/club_private_room.json",       // Velvet Shadows Club
    "https://solana-mafia.com/nft/mercy_helping_hand.json",      // Angel's Mercy Foundation
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
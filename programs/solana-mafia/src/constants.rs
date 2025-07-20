// constants.rs
use anchor_lang::prelude::*;

// ============================================================================
// PROGRAM CONSTANTS
// ============================================================================

/// Seeds для PDA
pub const GAME_STATE_SEED: &[u8] = b"game_state";
pub const GAME_CONFIG_SEED: &[u8] = b"game_config";
pub const TREASURY_SEED: &[u8] = b"treasury";
pub const PLAYER_SEED: &[u8] = b"player";

// ============================================================================
// BUSINESS CONFIGURATION
// ============================================================================

/// Бизнес константы
pub const BUSINESS_TYPES_COUNT: usize = 6;
pub const MAX_BUSINESSES_PER_PLAYER: u8 = 10;
pub const MAX_UPGRADE_LEVEL: u8 = 10;
pub const MAX_REFERRAL_LEVELS: usize = 3;

/// Дневные ставки в базисных пунктах (0.8% = 80)
pub const BUSINESS_RATES: [u16; 6] = [80, 90, 100, 110, 130, 150];

/// Минимальные депозиты в lamports
pub const MIN_DEPOSITS: [u64; 6] = [
    100_000_000,   // 0.1 SOL - CryptoKiosk
    500_000_000,   // 0.5 SOL - MemeCasino
    2_000_000_000, // 2 SOL - NFTLaundry
    5_000_000_000, // 5 SOL - MiningFarm
    20_000_000_000, // 20 SOL - DeFiEmpire
    100_000_000_000, // 100 SOL - SolanaCartel
];

// ============================================================================
// FEES AND ECONOMICS
// ============================================================================

/// Экономические константы
pub const ENTRY_FEE: u64 = 100_000; // 0.0001 SOL
pub const TREASURY_FEE_PERCENT: u8 = 20; // 20%

/// Early sell fees by days held (index = days, value = fee percent)
pub const EARLY_SELL_FEES: [u8; 32] = [
    20, 20, 20, 20, 20, 20, 20, // Days 0-6: 20%
    15, 15, 15, 15, 15, 15, 15, // Days 7-13: 15%
    10, 10, 10, 10, 10, 10, 10, // Days 14-20: 10%
    7,  7,  7,  7,  7,  7,  7,  // Days 21-27: 7%
    5,  5,  5,  2,              // Days 28-30: 5%, final: 2%
];

/// Final sell fee after 30 days
pub const FINAL_SELL_FEE_PERCENT: u8 = 2;

// ============================================================================
// UPGRADE SYSTEM
// ============================================================================

/// Стоимость апгрейдов (в lamports)
pub const UPGRADE_COSTS: [u64; 10] = [
    50_000_000,   // Level 1: 0.05 SOL
    100_000_000,  // Level 2: 0.1 SOL
    200_000_000,  // Level 3: 0.2 SOL
    500_000_000,  // Level 4: 0.5 SOL
    1_000_000_000, // Level 5: 1 SOL
    2_000_000_000, // Level 6: 2 SOL
    5_000_000_000, // Level 7: 5 SOL
    10_000_000_000, // Level 8: 10 SOL
    20_000_000_000, // Level 9: 20 SOL
    50_000_000_000, // Level 10: 50 SOL
];

/// Бонусы за апгрейды в базисных пунктах
pub const UPGRADE_BONUSES: [u16; 10] = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100];

// ============================================================================
// REFERRAL SYSTEM
// ============================================================================

/// Реферальные ставки (5%, 3%, 2%)
pub const REFERRAL_RATES: [u8; 3] = [5, 3, 2];

// ============================================================================
// RATE LIMITING & COOLDOWNS
// ============================================================================

/// Минимальное время между созданием бизнесов (10 минут)
pub const BUSINESS_CREATE_COOLDOWN: i64 = 10; // Было 600, стало 10

/// Минимальное время между клеймами заработка (1 час)
pub const CLAIM_EARNINGS_COOLDOWN: i64 = 3600; // 60 * 60 секунд

/// Минимальное время между обновлениями заработка (5 минут)
pub const UPDATE_EARNINGS_COOLDOWN: i64 = 300; // 5 * 60 секунд

// ============================================================================
// TIME CONSTANTS
// ============================================================================

/// Seconds in a day (for daily rate calculations)
pub const SECONDS_PER_DAY: i64 = 86_400;

/// Basis points denominator (10000 = 100%)
pub const BASIS_POINTS: u64 = 10_000;
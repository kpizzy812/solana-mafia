// constants.rs
use anchor_lang::prelude::*;

// ============================================================================
// BUSINESS CONFIGURATION
// ============================================================================

/// Number of business types available
pub const BUSINESS_TYPES_COUNT: usize = 6;

/// Maximum businesses per player
pub const MAX_BUSINESSES_PER_PLAYER: u8 = 10;

/// Business daily rates in basis points (100 = 1%)
pub const BUSINESS_RATES: [u16; BUSINESS_TYPES_COUNT] = [
    80,  // 0.8% - CryptoKiosk
    90,  // 0.9% - MemeCasino  
    100, // 1.0% - NFTLaundry
    110, // 1.1% - MiningFarm
    130, // 1.3% - DeFiEmpire
    150, // 1.5% - SolanaCartel
];

/// Minimum deposits for each business type (in lamports)
pub const MIN_DEPOSITS: [u64; BUSINESS_TYPES_COUNT] = [
    100_000_000,    // 0.1 SOL - CryptoKiosk
    500_000_000,    // 0.5 SOL - MemeCasino
    2_000_000_000,  // 2 SOL - NFTLaundry
    5_000_000_000,  // 5 SOL - MiningFarm
    20_000_000_000, // 20 SOL - DeFiEmpire
    100_000_000_000,// 100 SOL - SolanaCartel
];

// ============================================================================
// FEES AND ECONOMICS
// ============================================================================

/// Entry fee to start playing (in lamports) - $10 ≈ 0.065 SOL
pub const ENTRY_FEE: u64 = 65_000_000;

/// Treasury fee percentage (20% of deposits go to team)
pub const TREASURY_FEE_PERCENT: u8 = 20;

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

/// Maximum upgrade levels per business
pub const MAX_UPGRADE_LEVEL: u8 = 5;

/// Upgrade costs (donations to team) in lamports
pub const UPGRADE_COSTS: [u64; MAX_UPGRADE_LEVEL as usize] = [
    100_000_000,   // Level 1: 0.1 SOL
    300_000_000,   // Level 2: 0.3 SOL
    800_000_000,   // Level 3: 0.8 SOL
    2_000_000_000, // Level 4: 2.0 SOL
    5_000_000_000, // Level 5: 5.0 SOL
];

/// Upgrade bonuses in basis points (added to daily rate)
pub const UPGRADE_BONUSES: [u16; MAX_UPGRADE_LEVEL as usize] = [
    10, // Level 1: +0.1%
    20, // Level 2: +0.2%  
    30, // Level 3: +0.3%
    40, // Level 4: +0.4%
    50, // Level 5: +0.5%
];

// ============================================================================
// REFERRAL SYSTEM
// ============================================================================

/// Maximum referral levels
pub const MAX_REFERRAL_LEVELS: u8 = 3;

/// Referral rates by level (percent of earnings)
pub const REFERRAL_RATES: [u8; MAX_REFERRAL_LEVELS as usize] = [
    5, // Level 1: 5%
    3, // Level 2: 3%
    2, // Level 3: 2%
];

// ============================================================================
// TIME CONSTANTS
// ============================================================================

/// Seconds in a day (for daily rate calculations)
pub const SECONDS_PER_DAY: i64 = 86_400;

/// Basis points denominator (10000 = 100%)
pub const BASIS_POINTS: u64 = 10_000;

// ============================================================================
// PROGRAM CONSTANTS
// ============================================================================

/// Seed for GameState PDA
pub const GAME_STATE_SEED: &[u8] = b"game_state";

/// Seed for GameConfig PDA  
pub const GAME_CONFIG_SEED: &[u8] = b"game_config";

/// Seed for Player PDA
pub const PLAYER_SEED: &[u8] = b"player";

/// Seed for Treasury PDA
pub const TREASURY_SEED: &[u8] = b"treasury";
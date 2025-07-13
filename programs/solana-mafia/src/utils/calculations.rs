// utils/calculations.rs
use crate::constants::*;

/// Calculate daily earnings for a business
pub fn calculate_daily_earnings(invested_amount: u64, daily_rate: u16) -> u64 {
    (invested_amount as u128 * daily_rate as u128 / BASIS_POINTS as u128) as u64
}

/// Calculate earnings for a specific time period
pub fn calculate_earnings_for_period(
    invested_amount: u64,
    daily_rate: u16,
    seconds: i64,
) -> u64 {
    let daily_earnings = calculate_daily_earnings(invested_amount, daily_rate);
    let seconds_earnings = daily_earnings as u128 / SECONDS_PER_DAY as u128;
    (seconds_earnings * seconds as u128) as u64
}

/// Calculate early sell fee based on days held
pub fn calculate_early_sell_fee(invested_amount: u64, days_held: u64) -> u64 {
    let fee_percent = if days_held < EARLY_SELL_FEES.len() as u64 {
        EARLY_SELL_FEES[days_held as usize]
    } else {
        FINAL_SELL_FEE_PERCENT
    };
    
    (invested_amount * fee_percent as u64) / 100
}

/// Calculate referral bonus
pub fn calculate_referral_bonus(amount: u64, level: u8) -> u64 {
    if level == 0 || level > MAX_REFERRAL_LEVELS {
        return 0;
    }
    
    let rate = REFERRAL_RATES[(level - 1) as usize];
    (amount * rate as u64) / 100
}
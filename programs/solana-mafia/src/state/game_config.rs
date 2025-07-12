// state/game_config.rs
use anchor_lang::prelude::*;
use crate::constants::*;

#[account]
pub struct GameConfig {
    /// Admin authority who can update config
    pub authority: Pubkey,
    
    /// Daily rates for each business type (basis points)
    pub business_rates: [u16; BUSINESS_TYPES_COUNT],
    
    /// Minimum deposits for each business type
    pub min_deposits: [u64; BUSINESS_TYPES_COUNT],
    
    /// Entry fee to join the game
    pub entry_fee: u64,
    
    /// Treasury fee percentage (what goes to team)
    pub treasury_fee_percent: u8,
    
    /// Upgrade costs for each level
    pub upgrade_costs: [u64; MAX_UPGRADE_LEVEL as usize],
    
    /// Upgrade bonuses for each level (basis points)
    pub upgrade_bonuses: [u16; MAX_UPGRADE_LEVEL as usize],
    
    /// Referral rates for each level
    pub referral_rates: [u8; MAX_REFERRAL_LEVELS as usize],
    
    /// Maximum businesses per player
    pub max_businesses_per_player: u8,
    
    /// Whether new registrations are allowed
    pub registrations_open: bool,
    
    /// Bump seed for PDA
    pub bump: u8,
}

impl GameConfig {
    /// Size for account allocation
    pub const SIZE: usize = 8 + // discriminator
        32 + // authority
        2 * BUSINESS_TYPES_COUNT + // business_rates
        8 * BUSINESS_TYPES_COUNT + // min_deposits
        8 + // entry_fee
        1 + // treasury_fee_percent
        8 * (MAX_UPGRADE_LEVEL as usize) + // upgrade_costs
        2 * (MAX_UPGRADE_LEVEL as usize) + // upgrade_bonuses
        1 * (MAX_REFERRAL_LEVELS as usize) + // referral_rates
        1 + // max_businesses_per_player
        1 + // registrations_open
        1; // bump

    /// Create new config with default values
    pub fn new(authority: Pubkey, bump: u8) -> Self {
        Self {
            authority,
            business_rates: BUSINESS_RATES,
            min_deposits: MIN_DEPOSITS,
            entry_fee: ENTRY_FEE,
            treasury_fee_percent: TREASURY_FEE_PERCENT,
            upgrade_costs: UPGRADE_COSTS,
            upgrade_bonuses: UPGRADE_BONUSES,
            referral_rates: REFERRAL_RATES,
            max_businesses_per_player: MAX_BUSINESSES_PER_PLAYER,
            registrations_open: true,
            bump,
        }
    }

    /// Get daily rate for business type
    pub fn get_business_rate(&self, business_type_index: usize) -> u16 {
        if business_type_index < BUSINESS_TYPES_COUNT {
            self.business_rates[business_type_index]
        } else {
            0
        }
    }

    /// Get minimum deposit for business type
    pub fn get_min_deposit(&self, business_type_index: usize) -> u64 {
        if business_type_index < BUSINESS_TYPES_COUNT {
            self.min_deposits[business_type_index]
        } else {
            u64::MAX
        }
    }

    /// Get upgrade cost for level
    pub fn get_upgrade_cost(&self, level: u8) -> Option<u64> {
        if level > 0 && level <= MAX_UPGRADE_LEVEL {
            Some(self.upgrade_costs[(level - 1) as usize])
        } else {
            None
        }
    }

    /// Get upgrade bonus for level
    pub fn get_upgrade_bonus(&self, level: u8) -> u16 {
        if level > 0 && level <= MAX_UPGRADE_LEVEL {
            self.upgrade_bonuses[(level - 1) as usize]
        } else {
            0
        }
    }

    /// Get referral rate for level
    pub fn get_referral_rate(&self, level: u8) -> u8 {
        if level > 0 && level <= MAX_REFERRAL_LEVELS {
            self.referral_rates[(level - 1) as usize]
        } else {
            0
        }
    }

    /// Update business rates (admin only)
    pub fn update_business_rates(&mut self, new_rates: [u16; BUSINESS_TYPES_COUNT]) {
        self.business_rates = new_rates;
    }

    /// Update entry fee (admin only)
    pub fn update_entry_fee(&mut self, new_fee: u64) {
        self.entry_fee = new_fee;
    }

    /// Update treasury fee (admin only, max 25%)
    pub fn update_treasury_fee(&mut self, new_fee: u8) -> Result<()> {
        if new_fee > 25 {
            return Err(crate::error::SolanaMafiaError::InvalidFeePercentage.into());
        }
        self.treasury_fee_percent = new_fee;
        Ok(())
    }

    /// Toggle registrations
    pub fn toggle_registrations(&mut self) {
        self.registrations_open = !self.registrations_open;
    }
}
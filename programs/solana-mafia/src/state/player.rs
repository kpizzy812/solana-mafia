// state/player.rs
use anchor_lang::prelude::*;
use crate::state::business::Business;
use crate::constants::*;

#[account]
pub struct Player {
    /// Owner's wallet address
    pub owner: Pubkey,
    
    /// Referrer who invited this player (if any)
    pub referrer: Option<Pubkey>,
    
    /// Whether player has paid entry fee
    pub has_paid_entry: bool,
    
    /// Total amount invested across all businesses
    pub total_invested: u64,
    
    /// Total earnings claimed by player
    pub total_claimed: u64,
    
    /// Total referral earnings
    pub referral_earnings: u64,
    
    /// List of businesses owned by this player
    pub businesses: Vec<Business>,
    
    /// When player account was created
    pub created_at: i64,
    
    /// When player last claimed earnings
    pub last_claim: i64,
    
    /// Bump seed for PDA
    pub bump: u8,
}

impl Player {
    /// Size calculation for account allocation
    pub const MAX_SIZE: usize = 8 + // discriminator
        32 + // owner
        1 + 32 + // referrer option
        1 + // has_paid_entry
        8 + // total_invested
        8 + // total_claimed
        8 + // referral_earnings
        4 + (Business::SIZE * MAX_BUSINESSES_PER_PLAYER as usize) + // businesses vec
        8 + // created_at
        8 + // last_claim
        1; // bump

    /// Create new player account
    pub fn new(owner: Pubkey, referrer: Option<Pubkey>, current_time: i64, bump: u8) -> Self {
        Self {
            owner,
            referrer,
            has_paid_entry: false,
            total_invested: 0,
            total_claimed: 0,
            referral_earnings: 0,
            businesses: Vec::new(),
            created_at: current_time,
            last_claim: current_time,
            bump,
        }
    }

    /// Check if player can create more businesses
    pub fn can_create_business(&self) -> bool {
        self.businesses.len() < MAX_BUSINESSES_PER_PLAYER as usize
    }

    /// Add a new business to player's portfolio
    pub fn add_business(&mut self, business: Business) -> Result<()> {
        if !self.can_create_business() {
            return Err(crate::error::SolanaMafiaError::MaxBusinessesReached.into());
        }
        
        self.businesses.push(business);
        Ok(())
    }

    /// Get business by index
    pub fn get_business(&self, index: u8) -> Option<&Business> {
        self.businesses.get(index as usize)
    }

    /// Get mutable business by index
    pub fn get_business_mut(&mut self, index: u8) -> Option<&mut Business> {
        self.businesses.get_mut(index as usize)
    }

    /// Calculate total pending earnings across all businesses
    pub fn calculate_total_pending_earnings(&self, current_time: i64) -> u64 {
        self.businesses
            .iter()
            .filter(|b| b.is_active)
            .map(|business| {
                let time_diff = current_time - business.last_claim;
                let daily_earnings = (business.invested_amount as u128 * business.daily_rate as u128) 
                    / BASIS_POINTS as u128;
                let seconds_earnings = daily_earnings / SECONDS_PER_DAY as u128;
                (seconds_earnings * time_diff as u128) as u64
            })
            .sum()
    }

    /// Update last claim time for all businesses
    pub fn update_claim_time(&mut self, current_time: i64) {
        self.last_claim = current_time;
        for business in &mut self.businesses {
            if business.is_active {
                business.last_claim = current_time;
            }
        }
    }
}

impl Business {
    /// Size of Business struct for serialization
    pub const SIZE: usize = 
        1 + // business_type enum (1 byte)
        8 + // invested_amount
        2 + // daily_rate
        1 + // upgrade_level
        8 + // total_earned
        8 + // last_claim
        8 + // created_at
        1;  // is_active
}
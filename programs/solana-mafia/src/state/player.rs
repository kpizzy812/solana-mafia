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
    
    /// Total earnings claimed by player (historical)
    pub total_claimed: u64,
    
    /// Current pending earnings from businesses (ready to claim)
    pub pending_earnings: u64,
    
    /// Current pending referral earnings (ready to claim)
    pub pending_referral_earnings: u64,
    
    /// Total referral earnings claimed (historical)
    pub total_referral_claimed: u64,
    
    /// List of businesses owned by this player
    pub businesses: Vec<Business>,
    
    /// When player account was created
    pub created_at: i64,
    
    /// When player last updated earnings
    pub last_earnings_update: i64,
    
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
        8 + // pending_earnings
        8 + // pending_referral_earnings
        8 + // total_referral_claimed
        4 + (Business::SIZE * MAX_BUSINESSES_PER_PLAYER as usize) + // businesses vec
        8 + // created_at
        8 + // last_earnings_update
        1; // bump

    /// Create new player account
    pub fn new(owner: Pubkey, referrer: Option<Pubkey>, current_time: i64, bump: u8) -> Self {
        Self {
            owner,
            referrer,
            has_paid_entry: false,
            total_invested: 0,
            total_claimed: 0,
            pending_earnings: 0,
            pending_referral_earnings: 0,
            total_referral_claimed: 0,
            businesses: Vec::new(),
            created_at: current_time,
            last_earnings_update: current_time,
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

    /// Update pending earnings for all active businesses
    pub fn update_pending_earnings(&mut self, current_time: i64) {
        let time_diff = current_time - self.last_earnings_update;
        
        for business in &mut self.businesses {
            if business.is_active && time_diff > 0 {
                let time_since_last_claim = current_time - business.last_claim;
                let daily_earnings = (business.invested_amount as u128 * business.daily_rate as u128) 
                    / BASIS_POINTS as u128;
                let seconds_earnings = daily_earnings / SECONDS_PER_DAY as u128;
                let new_earnings = (seconds_earnings * time_since_last_claim as u128) as u64;
                
                // Add to pending earnings
                self.pending_earnings += new_earnings;
                
                // Update business last claim
                business.last_claim = current_time;
                business.total_earned += new_earnings;
            }
        }
        
        self.last_earnings_update = current_time;
    }

    /// Add referral bonus to pending earnings
    pub fn add_referral_bonus(&mut self, amount: u64) {
        self.pending_referral_earnings += amount;
    }

    /// Get total claimable amount (earnings + referrals)
    pub fn get_claimable_amount(&self) -> u64 {
        self.pending_earnings + self.pending_referral_earnings
    }

    /// Claim all pending earnings
    pub fn claim_all_earnings(&mut self) -> u64 {
        let total_amount = self.get_claimable_amount();
        
        // Update historical totals
        self.total_claimed += self.pending_earnings;
        self.total_referral_claimed += self.pending_referral_earnings;
        
        // Reset pending amounts
        self.pending_earnings = 0;
        self.pending_referral_earnings = 0;
        
        total_amount
    }
}
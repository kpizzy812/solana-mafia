use anchor_lang::prelude::*;
use crate::constants::*;
use crate::state::business::Business;

#[account]
pub struct Player {
    pub owner: Pubkey,
    pub businesses: Vec<Business>,
    pub total_invested: u64,
    pub total_earned: u64,
    pub pending_earnings: u64,
    pub pending_referral_earnings: u64, // Для начисления с бэка
    pub has_paid_entry: bool,
    pub created_at: i64,
    pub bump: u8,
}

impl Player {
    /// Size for account allocation
    pub const SIZE: usize = 8 + // discriminator
        32 + // owner
        4 + (Business::SIZE * MAX_BUSINESSES_PER_PLAYER as usize) + // businesses Vec
        8 + // total_invested
        8 + // total_earned
        8 + // pending_earnings
        8 + // pending_referral_earnings
        1 + // has_paid_entry
        8 + // created_at
        1; // bump

    /// Create new player
    pub fn new(owner: Pubkey, _referrer: Option<Pubkey>, current_time: i64, bump: u8) -> Self {
        Self {
            owner,
            businesses: Vec::new(),
            total_invested: 0,
            total_earned: 0,
            pending_earnings: 0,
            pending_referral_earnings: 0,
            has_paid_entry: false,
            created_at: current_time,
            bump,
        }
    }

    /// Get business by index
    pub fn get_business(&self, index: u8) -> Option<&Business> {
        self.businesses.get(index as usize)
    }

    /// Get mutable business by index
    pub fn get_business_mut(&mut self, index: u8) -> Option<&mut Business> {
        self.businesses.get_mut(index as usize)
    }

    /// Check if player can create more businesses
    pub fn can_create_business(&self) -> bool {
        self.businesses.len() < MAX_BUSINESSES_PER_PLAYER as usize
    }

    /// Add new business
    pub fn add_business(&mut self, business: Business) -> Result<()> {
        if !self.can_create_business() {
            return Err(crate::error::SolanaMafiaError::MaxBusinessesReached.into());
        }
        self.businesses.push(business);
        self.total_invested += business.invested_amount;
        Ok(())
    }

    /// Update pending earnings for all businesses
    pub fn update_pending_earnings(&mut self, current_time: i64) {
        for business in &mut self.businesses {
            if business.is_active {
                let pending = business.calculate_pending_earnings(current_time);
                self.pending_earnings += pending;
                business.last_claim = current_time;
            }
        }
    }

    /// Get total claimable amount (earnings + referral)
    pub fn get_claimable_amount(&self) -> u64 {
        self.pending_earnings + self.pending_referral_earnings
    }

    /// Claim all earnings
    pub fn claim_all_earnings(&mut self) {
        let total_claimed = self.pending_earnings + self.pending_referral_earnings;
        self.total_earned += total_claimed;
        self.pending_earnings = 0;
        self.pending_referral_earnings = 0;
    }

    /// Add referral bonus (called from backend)
    pub fn add_referral_bonus(&mut self, amount: u64) {
        self.pending_referral_earnings += amount;
    }

    /// Claim earnings
    pub fn claim_earnings(&mut self, amount: u64) {
        self.pending_earnings = self.pending_earnings.saturating_sub(amount);
        self.total_earned += amount;
    }

    /// Claim referral earnings
    pub fn claim_referral_earnings(&mut self, amount: u64) {
        self.pending_referral_earnings = self.pending_referral_earnings.saturating_sub(amount);
        self.total_earned += amount;
    }
}
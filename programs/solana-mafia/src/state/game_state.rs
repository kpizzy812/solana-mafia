// state/game_state.rs
use anchor_lang::prelude::*;

#[account]
pub struct GameState {
    /// Admin authority (for emergency functions only)
    pub authority: Pubkey,
    
    /// Treasury wallet where team fees go
    pub treasury_wallet: Pubkey,
    
    /// Total number of players who have joined
    pub total_players: u64,
    
    /// Total amount invested in all businesses
    pub total_invested: u64,
    
    /// Total amount withdrawn by players
    pub total_withdrawn: u64,
    
    /// Total amount sent to treasury
    pub total_treasury_collected: u64,
    
    /// Total number of businesses created
    pub total_businesses: u64,
    
    /// Total referral bonuses paid
    pub total_referral_paid: u64,
    
    /// Whether the game is currently paused
    pub is_paused: bool,
    
    /// When the game was initialized
    pub initialized_at: i64,
    
    /// Bump seed for PDA
    pub bump: u8,
}

impl GameState {
    /// Size for account allocation
    pub const SIZE: usize = 8 + // discriminator
        32 + // authority
        32 + // treasury_wallet
        8 + // total_players
        8 + // total_invested
        8 + // total_withdrawn
        8 + // total_treasury_collected
        8 + // total_businesses
        8 + // total_referral_paid
        1 + // is_paused
        8 + // initialized_at
        1; // bump

    /// Create new game state
    pub fn new(
        authority: Pubkey,
        treasury_wallet: Pubkey,
        current_time: i64,
        bump: u8,
    ) -> Self {
        Self {
            authority,
            treasury_wallet,
            total_players: 0,
            total_invested: 0,
            total_withdrawn: 0,
            total_treasury_collected: 0,
            total_businesses: 0,
            total_referral_paid: 0,
            is_paused: false,
            initialized_at: current_time,
            bump,
        }
    }

    /// Increment player count
    pub fn add_player(&mut self) {
        self.total_players += 1;
    }

    /// Add to total invested
    pub fn add_investment(&mut self, amount: u64) {
        self.total_invested += amount;
    }

    /// Add to total withdrawn
    pub fn add_withdrawal(&mut self, amount: u64) {
        self.total_withdrawn += amount;
    }

    /// Add to treasury collected
    pub fn add_treasury_collection(&mut self, amount: u64) {
        self.total_treasury_collected += amount;
    }

    /// Increment business count
    pub fn add_business(&mut self) {
        self.total_businesses += 1;
    }

    /// Add to referral payments
    pub fn add_referral_payment(&mut self, amount: u64) {
        self.total_referral_paid += amount;
    }

    /// Check if game is active (not paused)
    pub fn is_active(&self) -> bool {
        !self.is_paused
    }

    /// Emergency pause toggle (admin only)
    pub fn toggle_pause(&mut self) {
        self.is_paused = !self.is_paused;
    }
}
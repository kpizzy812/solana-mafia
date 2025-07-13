use anchor_lang::prelude::*;

// Import modules
pub mod constants;
pub mod error;
pub mod state;
pub mod instructions;

// Re-export for convenience
pub use constants::*;
pub use error::*;
pub use state::*;
pub use instructions::*;

declare_id!("93zp2Qtgaiud9NTG1fYb4qqDddSi98AAx9Px7Gyv3CnM");

#[program]
pub mod solana_mafia {
    use super::*;

    /// Initialize the game with config and state
    pub fn initialize(ctx: Context<Initialize>, treasury_wallet: Pubkey) -> Result<()> {
        instructions::initialize::handler(ctx, treasury_wallet)
    }

    /// Create a new business for a player
    pub fn create_business(
        ctx: Context<CreateBusiness>,
        business_type: u8,
        deposit_amount: u64,
        referrer: Option<Pubkey>,
    ) -> Result<()> {
        instructions::create_business::handler(ctx, business_type, deposit_amount, referrer)
    }

    /// Claim all pending earnings (business + referral)
    pub fn claim_earnings(ctx: Context<ClaimEarnings>) -> Result<()> {
        instructions::claim_earnings::handler(ctx)
    }

    /// Process referral bonus for a player (crank instruction)
    pub fn process_referral_bonus(
        ctx: Context<ProcessReferralBonus>,
        deposit_amount: u64,
    ) -> Result<()> {
        instructions::process_referral_bonus::handler(ctx, deposit_amount)
    }

    /// Update player's pending earnings (crank instruction)
    pub fn update_earnings(ctx: Context<UpdateEarnings>) -> Result<()> {
        instructions::update_earnings::handler(ctx)
    }
}
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

    /// Pay referral bonus to a referrer
    pub fn pay_referral_bonus(
        ctx: Context<PayReferralBonus>,
        deposit_amount: u64,
        referral_level: u8,
    ) -> Result<()> {
        instructions::pay_referral_bonus::handler(ctx, deposit_amount, referral_level)
    }
}
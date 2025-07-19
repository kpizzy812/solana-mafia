use anchor_lang::prelude::*;

pub mod constants;
pub mod error;
pub mod instructions;
pub mod state;
pub mod utils;

use instructions::*;

declare_id!("11111111111111111111111111111111");

#[program]
pub mod solana_mafia {
    use super::*;

    /// Initialize the game with treasury wallet
    pub fn initialize(ctx: Context<Initialize>, treasury_wallet: Pubkey) -> Result<()> {
        instructions::initialize::handler(ctx, treasury_wallet)
    }

    /// Create/buy a new business (with auto player creation if needed)
    pub fn create_business(
        ctx: Context<CreateBusiness>,
        business_type: u8,
        deposit_amount: u64,
    ) -> Result<()> {
        instructions::create_business::handler(ctx, business_type, deposit_amount)
    }

    /// Claim earnings from all businesses
    pub fn claim_earnings(ctx: Context<ClaimEarnings>) -> Result<()> {
        instructions::claim_earnings::handler(ctx)
    }

    /// Update pending earnings for a player (crank function)
    pub fn update_earnings(ctx: Context<UpdateEarnings>) -> Result<()> {
        instructions::update_earnings::handler(ctx)
    }

    /// Sell a business with early exit fees
    pub fn sell_business(ctx: Context<SellBusiness>, business_index: u8) -> Result<()> {
        instructions::sell_business::handler(ctx, business_index)
    }

    /// Upgrade a business (donate to team for better rates)
    pub fn upgrade_business(ctx: Context<UpgradeBusiness>, business_index: u8) -> Result<()> {
        instructions::upgrade_business::handler(ctx, business_index)
    }

    /// Add referral bonus to player (called by backend)
    pub fn add_referral_bonus(ctx: Context<AddReferralBonus>, amount: u64) -> Result<()> {
        instructions::add_referral_bonus::handler(ctx, amount)
    }

    /// Admin: Toggle game pause state
    pub fn toggle_pause(ctx: Context<TogglePause>) -> Result<()> {
        instructions::admin::toggle_pause(ctx)
    }
}
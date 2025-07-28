use anchor_lang::prelude::*;

pub mod constants;
pub mod error;
pub mod instructions;
pub mod state;
pub mod utils;

use crate::error::SolanaMafiaError; 
use constants::*;
use state::*;

// Handler functions
use instructions::{
    initialize_handler, 
    create_player_handler,
    create_business_handler, 
    claim_earnings_handler, 
    update_earnings_handler,
    sell_business_handler, 
    upgrade_business_handler,
    add_referral_bonus_handler,
    process_referral_bonus_handler
};

// Contexts  
use instructions::{
    Initialize, 
    CreatePlayer, 
    CreateBusiness, 
    ClaimEarnings,
    UpdateEarnings, 
    SellBusiness, 
    UpgradeBusiness,
    AddReferralBonus,
    TogglePause, 
    EmergencyPause, 
    UpdateTreasuryFee,
    UpdateBusinessRates, 
    GetTreasuryStats
};

// Import AddReferralEarnings context from process_referral_bonus
use instructions::AddReferralEarnings;

declare_id!("Hnyyopg1fsQGY1JqEsp8CPZk1KjDKsAoosBJJi5ZpegU");

#[program]
pub mod solana_mafia {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>, treasury_wallet: Pubkey) -> Result<()> {
        initialize_handler(ctx, treasury_wallet)
    }

    pub fn create_player(ctx: Context<CreatePlayer>) -> Result<()> {
        create_player_handler(ctx)
    }

    pub fn create_business(
        ctx: Context<CreateBusiness>,
        business_type: u8,
        deposit_amount: u64,
    ) -> Result<()> {
        if ctx.accounts.game_state.is_paused {
            return Err(SolanaMafiaError::GamePaused.into());
        }
        create_business_handler(ctx, business_type, deposit_amount)
    }

    pub fn claim_earnings(ctx: Context<ClaimEarnings>) -> Result<()> {
        if ctx.accounts.game_state.is_paused {
            return Err(SolanaMafiaError::GamePaused.into());
        }
        claim_earnings_handler(ctx)
    }

    pub fn update_earnings(ctx: Context<UpdateEarnings>) -> Result<()> {
        update_earnings_handler(ctx)
    }

    pub fn sell_business(ctx: Context<SellBusiness>, business_index: u8) -> Result<()> {
        if ctx.accounts.game_state.is_paused {
            return Err(SolanaMafiaError::GamePaused.into());
        }
        sell_business_handler(ctx, business_index)
    }

    pub fn upgrade_business(ctx: Context<UpgradeBusiness>, business_index: u8) -> Result<()> {
        if ctx.accounts.game_state.is_paused {
            return Err(SolanaMafiaError::GamePaused.into());
        }
        upgrade_business_handler(ctx, business_index)
    }

    pub fn add_referral_bonus(ctx: Context<AddReferralBonus>, amount: u64) -> Result<()> {
        add_referral_bonus_handler(ctx, amount)
    }

    pub fn process_referral_bonus(ctx: Context<AddReferralEarnings>, amount: u64) -> Result<()> {
        process_referral_bonus_handler(ctx, amount)
    }

    // ===== ADMIN FUNCTIONS =====
    pub fn toggle_pause(ctx: Context<TogglePause>) -> Result<()> {
        instructions::admin::toggle_pause(ctx)
    }

    pub fn emergency_pause(ctx: Context<EmergencyPause>) -> Result<()> {
        instructions::admin::emergency_pause(ctx)
    }

    pub fn emergency_unpause(ctx: Context<EmergencyPause>) -> Result<()> {
        instructions::admin::emergency_unpause(ctx)
    }

    pub fn update_business_rates(ctx: Context<UpdateBusinessRates>, new_rates: [u16; 6]) -> Result<()> {
        instructions::admin::update_business_rates(ctx, new_rates)
    }

    pub fn update_treasury_fee(ctx: Context<UpdateTreasuryFee>, new_fee: u8) -> Result<()> {
        instructions::admin::update_treasury_fee(ctx, new_fee)
    }

    pub fn get_treasury_stats(ctx: Context<GetTreasuryStats>) -> Result<()> {
        instructions::admin::get_treasury_stats(ctx)
    }

    pub fn health_check_player(ctx: Context<HealthCheckPlayer>) -> Result<()> {
        let clock = Clock::get()?;
        ctx.accounts.player.health_check(clock.unix_timestamp)?;
        msg!("✅ Player health check passed for: {}", ctx.accounts.player.owner);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct HealthCheckPlayer<'info> {
    #[account(
        seeds = [PLAYER_SEED, player.owner.as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
}
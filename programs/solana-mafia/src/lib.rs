use anchor_lang::prelude::*;

// Импортируем модули
pub mod constants;
pub mod error;
pub mod instructions;
pub mod state;
pub mod utils;

// 🔧 ИСПРАВЛЕНО: Убираем дублирующие импорты, оставляем только нужные
use instructions::{
    initialize_handler, 
    create_player_handler,
    create_business_handler, 
    claim_earnings_handler, 
    update_earnings_handler,
    sell_business_handler, 
    upgrade_business_handler,
    add_referral_bonus_handler  // Только один handler для referral
};

// 🔧 ИСПРАВЛЕНО: Импортируем только существующие контексты
use instructions::{
    Initialize, 
    CreatePlayer, 
    CreateBusiness, 
    ClaimEarnings,
    UpdateEarnings, 
    SellBusiness, 
    UpgradeBusiness,
    AddReferralBonus,    // Только этот контекст
    TogglePause, 
    EmergencyPause, 
    UpdateTreasuryFee,
    UpdateBusinessRates, 
    GetTreasuryStats
};

// Импортируем state и constants
use state::*;
use constants::*;

declare_id!("Hnyyopg1fsQGY1JqEsp8CPZk1KjDKsAoosBJJi5ZpegU");

#[program]
pub mod solana_mafia {
    use super::*;

    /// Initialize the game with treasury wallet
    pub fn initialize(ctx: Context<Initialize>, treasury_wallet: Pubkey) -> Result<()> {
        initialize_handler(ctx, treasury_wallet)
    }

    /// Create new player (separate from business creation)
    pub fn create_player(ctx: Context<CreatePlayer>) -> Result<()> {
        create_player_handler(ctx)
    }

    /// Create business (requires existing player)
    pub fn create_business(
        ctx: Context<CreateBusiness>,
        business_type: u8,
        deposit_amount: u64,
    ) -> Result<()> {
        // Check if game is paused
        if ctx.accounts.game_state.is_paused {
            return Err(error::SolanaMafiaError::GamePaused.into());
        }
        create_business_handler(ctx, business_type, deposit_amount)
    }

    /// Claim earnings with safety checks
    pub fn claim_earnings(ctx: Context<ClaimEarnings>) -> Result<()> {
        // Check if game is paused
        if ctx.accounts.game_state.is_paused {
            return Err(error::SolanaMafiaError::GamePaused.into());
        }
        claim_earnings_handler(ctx)
    }

    /// Update earnings (owner only)
    pub fn update_earnings(ctx: Context<UpdateEarnings>) -> Result<()> {
        update_earnings_handler(ctx)
    }

    /// Sell business with early exit fees
    pub fn sell_business(ctx: Context<SellBusiness>, business_index: u8) -> Result<()> {
        // Check if game is paused
        if ctx.accounts.game_state.is_paused {
            return Err(error::SolanaMafiaError::GamePaused.into());
        }
        sell_business_handler(ctx, business_index)
    }

    /// Upgrade business (donation to team)
    pub fn upgrade_business(ctx: Context<UpgradeBusiness>, business_index: u8) -> Result<()> {
        // Check if game is paused  
        if ctx.accounts.game_state.is_paused {
            return Err(error::SolanaMafiaError::GamePaused.into());
        }
        upgrade_business_handler(ctx, business_index)
    }

    /// Add referral bonus (admin only)
    pub fn add_referral_bonus(ctx: Context<AddReferralBonus>, amount: u64) -> Result<()> {
        add_referral_bonus_handler(ctx, amount)
    }

    // ===== ADMIN FUNCTIONS =====

    /// Admin: Toggle game pause state
    pub fn toggle_pause(ctx: Context<TogglePause>) -> Result<()> {
        instructions::admin::toggle_pause(ctx)
    }

    /// Emergency: Stop all financial operations
    pub fn emergency_pause(ctx: Context<EmergencyPause>) -> Result<()> {
        instructions::admin::emergency_pause(ctx)
    }

    /// Emergency: Resume financial operations  
    pub fn emergency_unpause(ctx: Context<EmergencyPause>) -> Result<()> {
        instructions::admin::emergency_unpause(ctx)
    }

    /// Admin: Update business rates with safety checks
    pub fn update_business_rates(
        ctx: Context<UpdateBusinessRates>, 
        new_rates: [u16; 6]
    ) -> Result<()> {
        instructions::admin::update_business_rates(ctx, new_rates)
    }

    /// Admin: Update treasury fee (with limits)
    pub fn update_treasury_fee(ctx: Context<UpdateTreasuryFee>, new_fee: u8) -> Result<()> {
        instructions::admin::update_treasury_fee(ctx, new_fee)
    }

    /// View: Get treasury statistics and health
    pub fn get_treasury_stats(ctx: Context<GetTreasuryStats>) -> Result<()> {
        instructions::admin::get_treasury_stats(ctx)
    }

    /// Health check for player
    pub fn health_check_player(ctx: Context<HealthCheckPlayer>) -> Result<()> {
        let clock = Clock::get()?;
        ctx.accounts.player.health_check(clock.unix_timestamp)?;
        
        msg!("✅ Player health check passed for: {}", ctx.accounts.player.owner);
        Ok(())
    }
}

// Health check context
#[derive(Accounts)]
pub struct HealthCheckPlayer<'info> {
    /// Player to check
    #[account(
        seeds = [PLAYER_SEED, player.owner.as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
}
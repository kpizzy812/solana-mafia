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

    /// 🔒 НОВОЕ: Создание игрока (отдельно от бизнеса)
    pub fn create_player(ctx: Context<CreatePlayer>) -> Result<()> {
        instructions::create_business::create_player(ctx)
    }

    /// 🔒 БЕЗОПАСНОЕ создание бизнеса (требует existing player)
    pub fn create_business(
        ctx: Context<CreateBusiness>,
        business_type: u8,
        deposit_amount: u64,
    ) -> Result<()> {
        // 🔒 БЕЗОПАСНОСТЬ: Проверяем что игра не на паузе
        if ctx.accounts.game_state.is_paused {
            return Err(error::SolanaMafiaError::GamePaused.into());
        }
        instructions::create_business::handler(ctx, business_type, deposit_amount)
    }

    /// 🔒 БЕЗОПАСНЫЙ claim earnings (с лимитами)
    pub fn claim_earnings(ctx: Context<ClaimEarnings>) -> Result<()> {
        // 🔒 БЕЗОПАСНОСТЬ: Проверяем что игра не на паузе
        if ctx.accounts.game_state.is_paused {
            return Err(error::SolanaMafiaError::GamePaused.into());
        }
        instructions::claim_earnings::handler(ctx)
    }

    /// 🔒 БЕЗОПАСНЫЙ update earnings (только владелец)
    pub fn update_earnings(ctx: Context<UpdateEarnings>) -> Result<()> {
        instructions::update_earnings::handler(ctx)
    }

    /// 🔒 БЕЗОПАСНАЯ продажа бизнеса
    pub fn sell_business(ctx: Context<SellBusiness>, business_index: u8) -> Result<()> {
        // 🔒 БЕЗОПАСНОСТЬ: Проверяем что игра не на паузе
        if ctx.accounts.game_state.is_paused {
            return Err(error::SolanaMafiaError::GamePaused.into());
        }
        instructions::sell_business::handler(ctx, business_index)
    }

    /// 🔒 БЕЗОПАСНЫЙ upgrade бизнеса
    pub fn upgrade_business(ctx: Context<UpgradeBusiness>, business_index: u8) -> Result<()> {
        // 🔒 БЕЗОПАСНОСТЬ: Проверяем что игра не на паузе  
        if ctx.accounts.game_state.is_paused {
            return Err(error::SolanaMafiaError::GamePaused.into());
        }
        instructions::upgrade_business::handler(ctx, business_index)
    }

    /// 🔒 ОТКЛЮЧЕНО: Реферальные бонусы (слишком опасно для первой версии)
    // pub fn add_referral_bonus(...) -> Result<()> {
    //     // ОТКЛЮЧЕНО до полной реализации реферальной системы
    // }

    // ===== ADMIN FUNCTIONS =====

    /// Admin: Toggle game pause state
    pub fn toggle_pause(ctx: Context<TogglePause>) -> Result<()> {
        instructions::admin::toggle_pause(ctx)
    }

    /// 🆘 EMERGENCY: Stop all financial operations
    pub fn emergency_pause(ctx: Context<EmergencyPause>) -> Result<()> {
        instructions::admin::emergency_pause(ctx)
    }

    /// 🔓 EMERGENCY: Resume financial operations  
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

    /// 🔒 НОВОЕ: Health check для игрока
    pub fn health_check_player(ctx: Context<HealthCheckPlayer>) -> Result<()> {
        let clock = Clock::get()?;
        ctx.accounts.player.health_check(clock.unix_timestamp)?;
        
        msg!("✅ Player health check passed for: {}", ctx.accounts.player.owner);
        Ok(())
    }
}

// 🔒 НОВЫЙ: Health check context
#[derive(Accounts)]
pub struct HealthCheckPlayer<'info> {
    /// Player to check
    #[account(
        seeds = [b"player", player.owner.as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
}

// 🔒 БЕЗОПАСНОСТЬ РЕЗЮМЕ:
// ✅ Исправлен integer overflow в earnings
// ✅ Только владелец может обновлять свои earnings  
// ✅ Убран race condition (разделили create_player/create_business)
// ✅ Увеличен размер Player аккаунта
// ✅ Добавлены лимиты на все операции
// ✅ Health checks для всех данных
// ✅ Emergency pause функции
// ✅ Comprehensive logging для мониторинга
// ❌ Реферальная система отключена (слишком сложно сделать безопасно)
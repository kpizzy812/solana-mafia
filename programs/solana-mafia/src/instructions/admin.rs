// instructions/admin.rs
use anchor_lang::prelude::*;
use super::*;
use crate::error::SolanaMafiaError;

/// Admin function to pause/unpause the game
pub fn toggle_pause(ctx: Context<TogglePause>) -> Result<()> {
    let game_state = &mut ctx.accounts.game_state;
    
    // Only authority can pause
    if ctx.accounts.authority.key() != game_state.authority {
        return Err(SolanaMafiaError::UnauthorizedAdmin.into());
    }
    
    game_state.toggle_pause();
    
    msg!("Game pause toggled. New state: {}", game_state.is_paused);
    
    Ok(())
}

/// 🆘 EMERGENCY PAUSE - останавливает ВСЕ операции с деньгами
pub fn emergency_pause(ctx: Context<EmergencyPause>) -> Result<()> {
    let game_state = &mut ctx.accounts.game_state;
    
    // Only authority can activate emergency
    if ctx.accounts.authority.key() != game_state.authority {
        return Err(SolanaMafiaError::UnauthorizedAdmin.into());
    }
    
    game_state.is_paused = true;
    // Можно добавить отдельное поле emergency_paused для более жестких ограничений
    
    msg!("🆘 EMERGENCY PAUSE ACTIVATED!");
    msg!("All financial operations are now disabled.");
    msg!("Authority: {}", ctx.accounts.authority.key());
    
    Ok(())
}

/// 🔓 EMERGENCY UNPAUSE - возобновляет операции (только после проверки)
pub fn emergency_unpause(ctx: Context<EmergencyPause>) -> Result<()> {
    let game_state = &mut ctx.accounts.game_state;
    
    // Only authority can deactivate emergency
    if ctx.accounts.authority.key() != game_state.authority {
        return Err(SolanaMafiaError::UnauthorizedAdmin.into());
    }
    
    game_state.is_paused = false;
    
    msg!("🔓 Emergency pause deactivated.");
    msg!("Financial operations are now enabled.");
    msg!("Authority: {}", ctx.accounts.authority.key());
    
    Ok(())
}

/// Admin function to update treasury fee percentage
pub fn update_treasury_fee(ctx: Context<UpdateTreasuryFee>, new_fee: u8) -> Result<()> {
    let game_config = &mut ctx.accounts.game_config;
    let game_state = &ctx.accounts.game_state;
    
    // Check if game is paused
    if game_state.is_paused {
        return Err(SolanaMafiaError::GamePaused.into());
    }
    
    // Only authority can update
    if ctx.accounts.authority.key() != game_config.authority {
        return Err(SolanaMafiaError::UnauthorizedAdmin.into());
    }
    
    game_config.update_treasury_fee(new_fee)?;
    
    msg!("Treasury fee updated to: {}%", new_fee);
    
    Ok(())
}

/// 🔧 Update business rates (with limits)
pub fn update_business_rates(
    ctx: Context<UpdateBusinessRates>, 
    new_rates: [u16; BUSINESS_TYPES_COUNT]
) -> Result<()> {
    let game_config = &mut ctx.accounts.game_config;
    let game_state = &ctx.accounts.game_state;
    
    // Check if game is paused
    if game_state.is_paused {
        return Err(SolanaMafiaError::GamePaused.into());
    }
    
    // Only authority can update
    if ctx.accounts.authority.key() != game_config.authority {
        return Err(SolanaMafiaError::UnauthorizedAdmin.into());
    }
    
    // 🔒 ЗАЩИТА: Проверяем что ставки разумные (максимум 2% в день = 200 basis points)
    for rate in new_rates.iter() {
        if *rate > 200 {
            msg!("⚠️ Rate {} exceeds maximum allowed (200 basis points)", rate);
            return Err(SolanaMafiaError::InvalidFeePercentage.into());
        }
    }
    
    // 🔒 ЗАЩИТА: Ставки должны возрастать с типом бизнеса
    for i in 1..new_rates.len() {
        if new_rates[i] < new_rates[i-1] {
            msg!("⚠️ Rates must be in ascending order");
            return Err(SolanaMafiaError::InvalidFeePercentage.into());
        }
    }
    
    game_config.update_business_rates(new_rates);
    
    msg!("Business rates updated: {:?}", new_rates);
    
    Ok(())
}

/// 📊 Get treasury statistics (view function)
pub fn get_treasury_stats(ctx: Context<GetTreasuryStats>) -> Result<()> {
    let game_state = &ctx.accounts.game_state;
    let treasury_balance = ctx.accounts.treasury_pda.to_account_info().lamports();
    
    msg!("📊 TREASURY STATISTICS:");
    msg!("Treasury balance: {} lamports", treasury_balance);
    msg!("Total invested: {} lamports", game_state.total_invested);
    msg!("Total withdrawn: {} lamports", game_state.total_withdrawn);
    msg!("Total players: {}", game_state.total_players);
    msg!("Total businesses: {}", game_state.total_businesses);
    msg!("Game paused: {}", game_state.is_paused);
    
    let pending_in_system = game_state.total_invested
        .checked_sub(game_state.total_withdrawn)
        .unwrap_or(0);
    msg!("Pending in system: {} lamports", pending_in_system);
    
    // Проверка здоровья системы
    if treasury_balance < pending_in_system {
        msg!("⚠️ WARNING: Treasury balance less than pending obligations!");
    } else {
        msg!("✅ Treasury health: OK");
    }
    
    Ok(())
}

#[derive(Accounts)]
pub struct TogglePause<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
}

#[derive(Accounts)]
pub struct EmergencyPause<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
}

#[derive(Accounts)]
pub struct UpdateTreasuryFee<'info> {
    /// Authority (admin)
    pub authority: Signer<'info>,
    
    /// Game config to update
    #[account(
        mut,
        seeds = [GAME_CONFIG_SEED],
        bump = game_config.bump
    )]
    pub game_config: Account<'info, GameConfig>,
    
    /// Game state for pause check
    #[account(
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
}

#[derive(Accounts)]
pub struct UpdateBusinessRates<'info> {
    /// Authority (admin)
    pub authority: Signer<'info>,
    
    /// Game config to update
    #[account(
        mut,
        seeds = [GAME_CONFIG_SEED],
        bump = game_config.bump
    )]
    pub game_config: Account<'info, GameConfig>,
    
    /// Game state for pause check
    #[account(
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
}

#[derive(Accounts)]
pub struct GetTreasuryStats<'info> {
    /// Game state for statistics
    #[account(
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
    
    /// Treasury PDA for balance check
    #[account(
        seeds = [TREASURY_SEED],
        bump = treasury_pda.bump
    )]
    pub treasury_pda: Account<'info, Treasury>,
}
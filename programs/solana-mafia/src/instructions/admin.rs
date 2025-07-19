// instructions/admin.rs
use anchor_lang::prelude::*;
use crate::constants::*;
use crate::state::*;
use crate::error::*;

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

/// Admin function to update treasury fee percentage
pub fn update_treasury_fee(ctx: Context<UpdateTreasuryFee>, new_fee: u8) -> Result<()> {
    let game_config = &mut ctx.accounts.game_config;
    
    // Only authority can update
    if ctx.accounts.authority.key() != game_config.authority {
        return Err(SolanaMafiaError::UnauthorizedAdmin.into());
    }
    
    game_config.update_treasury_fee(new_fee)?;
    
    msg!("Treasury fee updated to: {}%", new_fee);
    
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
}
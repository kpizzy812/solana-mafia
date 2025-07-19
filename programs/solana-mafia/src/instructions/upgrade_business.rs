// instructions/upgrade_business.rs
use anchor_lang::prelude::*;
use crate::constants::*;
use crate::state::*;
use crate::error::*;
use crate::utils::validation::*;

pub fn handler(
    ctx: Context<UpgradeBusiness>,
    business_index: u8,
) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let game_state = &mut ctx.accounts.game_state;
    let game_config = &ctx.accounts.game_config;
    
    // Get business
    let business = player.get_business_mut(business_index)
        .ok_or(SolanaMafiaError::BusinessNotFound)?;
    
    if !business.is_active {
        return Err(SolanaMafiaError::BusinessNotFound.into());
    }
    
    // Check if can upgrade
    let current_level = business.upgrade_level;
    if current_level >= MAX_UPGRADE_LEVEL {
        return Err(SolanaMafiaError::InvalidUpgradeLevel.into());
    }
    
    let next_level = current_level + 1;
    let upgrade_cost = game_config.get_upgrade_cost(next_level)
        .ok_or(SolanaMafiaError::InvalidUpgradeLevel)?;
    
    // TODO: Implement payment validation
    // For now, just upgrade
    // Apply upgrade
    business.upgrade_level = next_level;
    let bonus = game_config.get_upgrade_bonus(next_level);
    business.daily_rate += bonus;
    
    // Update statistics
    game_state.add_treasury_collection(upgrade_cost);
    
    msg!("Business upgraded!");
    msg!("New level: {}", next_level);
    msg!("Upgrade cost: {} lamports", upgrade_cost);
    msg!("New daily rate: {} basis points", business.daily_rate);
    
    Ok(())
}

#[derive(Accounts)]
pub struct UpgradeBusiness<'info> {
    #[account(mut)]
    pub player_owner: Signer<'info>,
    
    #[account(
        mut,
        seeds = [PLAYER_SEED, player_owner.key().as_ref()],
        bump = player.bump,
        constraint = player.owner == player_owner.key()
    )]
    pub player: Account<'info, Player>,
    
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
    
    #[account(
        seeds = [GAME_CONFIG_SEED],
        bump = game_config.bump
    )]
    pub game_config: Account<'info, GameConfig>,
}
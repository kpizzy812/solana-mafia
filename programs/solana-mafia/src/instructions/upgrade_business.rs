// instructions/upgrade_business.rs
use anchor_lang::prelude::*;
use anchor_lang::system_program;
use crate::constants::{PLAYER_SEED, GAME_STATE_SEED, GAME_CONFIG_SEED, MAX_UPGRADE_LEVEL};
use crate::state::{Player, GameState, GameConfig};
use crate::error::SolanaMafiaError;

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
    
    // 🎯 РЕАЛЬНАЯ ПРОВЕРКА И ОПЛАТА АПГРЕЙДА
    // Весь upgrade_cost идет на кошелек команды (это донат за преимущество)
    system_program::transfer(
        CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.player_owner.to_account_info(),
                to: ctx.accounts.treasury_wallet.to_account_info(),
            },
        ),
        upgrade_cost,
    )?;
    
    // Apply upgrade with overflow protection
    business.upgrade_level = next_level;
    let bonus = game_config.get_upgrade_bonus(next_level);
    business.daily_rate = business.daily_rate
        .checked_add(bonus)
        .ok_or(SolanaMafiaError::MathOverflow)?;
    
    // Update statistics with overflow protection
    game_state.total_treasury_collected = game_state.total_treasury_collected
        .checked_add(upgrade_cost)
        .ok_or(SolanaMafiaError::MathOverflow)?;
    
    msg!("Business upgraded successfully!");
    msg!("Business index: {}", business_index);
    msg!("New level: {}", next_level);
    msg!("Upgrade cost: {} lamports (paid to team)", upgrade_cost);
    msg!("Bonus added: {} basis points", bonus);
    msg!("New daily rate: {} basis points", business.daily_rate);
    
    Ok(())
}

#[derive(Accounts)]
pub struct UpgradeBusiness<'info> {
    /// Player upgrading the business
    #[account(mut)]
    pub player_owner: Signer<'info>,
    
    /// Player account
    #[account(
        mut,
        seeds = [PLAYER_SEED, player_owner.key().as_ref()],
        bump = player.bump,
        constraint = player.owner == player_owner.key()
    )]
    pub player: Account<'info, Player>,
    
    /// Treasury wallet where upgrade fees go (team wallet)
    /// CHECK: This is validated against game_state.treasury_wallet
    #[account(
        mut,
        address = game_state.treasury_wallet
    )]
    pub treasury_wallet: AccountInfo<'info>,
    
    /// Game state for statistics
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
    
    /// Game config for upgrade costs and bonuses
    #[account(
        seeds = [GAME_CONFIG_SEED],
        bump = game_config.bump
    )]
    pub game_config: Account<'info, GameConfig>,
    
    /// System program for transfers
    pub system_program: Program<'info, System>,
}
// instructions/upgrade_business.rs
use anchor_lang::prelude::*;
use anchor_lang::system_program;
use crate::constants::*;
use crate::state::*;
use crate::error::*;
use crate::utils::*;

pub fn handler(
    ctx: Context<UpgradeBusiness>,
    business_index: u8,
) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let game_config = &ctx.accounts.game_config;
    let game_state = &mut ctx.accounts.game_state;
    
    // Get business
    let business = player.get_business_mut(business_index)
        .ok_or(SolanaMafiaError::BusinessNotFound)?;
    
    if !business.is_active {
        return Err(SolanaMafiaError::BusinessNotFound.into());
    }
    
    // Check if business can be upgraded
    if business.upgrade_level >= MAX_UPGRADE_LEVEL {
        return Err(SolanaMafiaError::InvalidUpgradeLevel.into());
    }
    
    let next_level = business.upgrade_level + 1;
    let upgrade_cost = game_config.get_upgrade_cost(next_level)
        .ok_or(SolanaMafiaError::InvalidUpgradeLevel)?;
    
    // Transfer upgrade cost to treasury
    system_program::transfer(
        CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.owner.to_account_info(),
                to: ctx.accounts.treasury_wallet.to_account_info(),
            },
        ),
        upgrade_cost,
    )?;
    
    // Apply upgrade
    business.upgrade_level = next_level;
    let bonus = game_config.get_upgrade_bonus(next_level);
    business.daily_rate += bonus;
    
    // Update statistics
    game_state.add_treasury_collection(upgrade_cost);
    
    msg!("Business upgraded successfully!");
    msg!("New level: {}", business.upgrade_level);
    msg!("New daily rate: {} basis points", business.daily_rate);
    msg!("Upgrade cost: {} lamports", upgrade_cost);
    
    Ok(())
}

#[derive(Accounts)]
pub struct UpgradeBusiness<'info> {
    /// Player upgrading the business
    #[account(mut)]
    pub owner: Signer<'info>,
    
    /// Player account
    #[account(
        mut,
        seeds = [PLAYER_SEED, owner.key().as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
    
    /// Game configuration
    #[account(
        seeds = [GAME_CONFIG_SEED],
        bump = game_config.bump
    )]
    pub game_config: Account<'info, GameConfig>,
    
    /// Game state for statistics
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
    
    /// Treasury wallet for upgrade fees
    /// CHECK: This is validated against game_state.treasury_wallet
    #[account(
        mut,
        address = game_state.treasury_wallet
    )]
    pub treasury_wallet: AccountInfo<'info>,
    
    /// System program
    pub system_program: Program<'info, System>,
}
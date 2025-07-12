// instructions/initialize.rs
use anchor_lang::prelude::*;
use crate::constants::*;
use crate::state::*;

/// Initialize the game with GameState and GameConfig accounts
pub fn handler(ctx: Context<Initialize>, treasury_wallet: Pubkey) -> Result<()> {
    let clock = Clock::get()?;
    
    // Initialize GameState
    let game_state = &mut ctx.accounts.game_state;
    **game_state = GameState::new(
        ctx.accounts.authority.key(),
        treasury_wallet,
        clock.unix_timestamp,
        ctx.bumps.game_state,
    );
    
    // Initialize GameConfig with default values
    let game_config = &mut ctx.accounts.game_config;
    **game_config = GameConfig::new(
        ctx.accounts.authority.key(),
        ctx.bumps.game_config,
    );
    
    msg!("Solana Mafia initialized successfully!");
    msg!("Authority: {}", ctx.accounts.authority.key());
    msg!("Treasury: {}", treasury_wallet);
    msg!("Total business types: {}", BUSINESS_TYPES_COUNT);
    
    Ok(())
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    /// Authority (admin) who can manage the game
    #[account(mut)]
    pub authority: Signer<'info>,
    
    /// Global game state account
    #[account(
        init,
        payer = authority,
        space = GameState::SIZE,
        seeds = [GAME_STATE_SEED],
        bump
    )]
    pub game_state: Account<'info, GameState>,
    
    /// Global game configuration account
    #[account(
        init,
        payer = authority,
        space = GameConfig::SIZE,
        seeds = [GAME_CONFIG_SEED],
        bump
    )]
    pub game_config: Account<'info, GameConfig>,
    
    /// System program for account creation
    pub system_program: Program<'info, System>,
}
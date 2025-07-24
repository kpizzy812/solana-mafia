use anchor_lang::prelude::*;
// 🔧 ИСПРАВЛЕНО: Правильные импорты через crate::
use crate::constants::*;
use crate::state::*;

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
    
    // Initialize Treasury PDA
    let treasury_pda = &mut ctx.accounts.treasury_pda;
    **treasury_pda = Treasury::new(ctx.bumps.treasury_pda);
    
    msg!("Solana Mafia initialized successfully!");
    msg!("Authority: {}", ctx.accounts.authority.key());
    msg!("Treasury Wallet: {}", treasury_wallet);
    msg!("Treasury PDA: {}", ctx.accounts.treasury_pda.key());
    msg!("Total business types: {}", BUSINESS_TYPES_COUNT);
    
    Ok(())
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    /// The authority (admin) of the game
    #[account(mut)]
    pub authority: Signer<'info>,
    
    /// Game state PDA
    #[account(
        init,
        payer = authority,
        space = GameState::SIZE,
        seeds = [GAME_STATE_SEED],
        bump
    )]
    pub game_state: Account<'info, GameState>,
    
    /// Game config PDA
    #[account(
        init,
        payer = authority,
        space = GameConfig::SIZE,
        seeds = [GAME_CONFIG_SEED],
        bump
    )]
    pub game_config: Account<'info, GameConfig>,
    
    /// Treasury PDA for holding funds
    #[account(
        init,
        payer = authority,
        space = Treasury::SIZE,
        seeds = [TREASURY_SEED],
        bump
    )]
    pub treasury_pda: Account<'info, Treasury>,
    
    /// System program
    pub system_program: Program<'info, System>,
}
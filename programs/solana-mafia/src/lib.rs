use anchor_lang::prelude::*;

pub mod constants; 
pub mod error;

declare_id!("Hnyyopg1fsQGY1JqEsp8CPZk1KjDKsAoosBJJi5ZpegU");

#[program]
pub mod solana_mafia {
    use super::*;

    /// Initialize the game with treasury wallet
    pub fn initialize(ctx: Context<Initialize>, treasury_wallet: Pubkey) -> Result<()> {
        let game_state = &mut ctx.accounts.game_state;
        let clock = Clock::get()?;
        
        game_state.authority = ctx.accounts.authority.key();
        game_state.treasury_wallet = treasury_wallet;
        game_state.total_players = 0;
        game_state.total_invested = 0;
        game_state.is_paused = false;
        game_state.created_at = clock.unix_timestamp;
        game_state.bump = ctx.bumps.game_state;
        
        msg!("Solana Mafia initialized!");
        msg!("Authority: {}", ctx.accounts.authority.key());
        msg!("Treasury: {}", treasury_wallet);
        
        Ok(())
    }

    pub fn create_player(ctx: Context<CreatePlayer>) -> Result<()> {
        msg!("Player created");
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    #[account(
        init,
        payer = authority,
        space = 8 + 32 + 32 + 8 + 8 + 8 + 8 + 8 + 8 + 1 + 8 + 1,
        seeds = [b"game_state"],
        bump
    )]
    pub game_state: Account<'info, GameState>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct CreatePlayer<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,
    pub system_program: Program<'info, System>,
}

#[account]
pub struct GameState {
    pub authority: Pubkey,
    pub treasury_wallet: Pubkey,
    pub total_players: u64,
    pub total_invested: u64,
    pub total_withdrawn: u64,
    pub total_referral_paid: u64,
    pub total_treasury_collected: u64,
    pub total_businesses: u64,
    pub is_paused: bool,
    pub created_at: i64,
    pub bump: u8,
}
// instructions/claim_earnings.rs
use anchor_lang::prelude::*;
use anchor_lang::system_program;
use crate::constants::*;
use crate::state::*;
use crate::error::*;

pub fn handler(ctx: Context<ClaimEarnings>) -> Result<()> {
    let clock = Clock::get()?;
    let player = &mut ctx.accounts.player;
    let game_state = &mut ctx.accounts.game_state;
    
    // First, update all pending earnings
    player.update_pending_earnings(clock.unix_timestamp);
    
    // Get total claimable amount
    let claimable_amount = player.get_claimable_amount();
    
    if claimable_amount == 0 {
        return Err(SolanaMafiaError::NoEarningsToClaim.into());
    }
    
    // Transfer earnings from game pool (treasury) to player
    let treasury_seeds = &[
        TREASURY_SEED,
        &[ctx.bumps.treasury_pda]
    ];
    let treasury_signer_seeds = &[&treasury_seeds[..]];
    
    system_program::transfer(
        CpiContext::new_with_signer(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.treasury_pda.to_account_info(),
                to: ctx.accounts.owner.to_account_info(),
            },
            treasury_signer_seeds,
        ),
        claimable_amount,
    )?;
    
    // Update player and game statistics
    let earnings_claimed = player.pending_earnings;
    let referral_claimed = player.pending_referral_earnings;
    
    player.claim_all_earnings();
    game_state.add_withdrawal(claimable_amount);
    
    msg!("Earnings claimed successfully!");
    msg!("Business earnings: {} lamports", earnings_claimed);
    msg!("Referral earnings: {} lamports", referral_claimed);
    msg!("Total claimed: {} lamports", claimable_amount);
    
    Ok(())
}

#[derive(Accounts)]
pub struct ClaimEarnings<'info> {
    /// Player claiming earnings
    #[account(mut)]
    pub owner: Signer<'info>,
    
    /// Player account
    #[account(
        mut,
        seeds = [PLAYER_SEED, owner.key().as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
    
    /// Game state for statistics
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
    
    /// Treasury PDA that holds the game pool funds
    #[account(
        mut,
        seeds = [TREASURY_SEED],
        bump
    )]
    pub treasury_pda: SystemAccount<'info>,
    
    /// System program
    pub system_program: Program<'info, System>,
}
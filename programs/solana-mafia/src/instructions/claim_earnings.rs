// instructions/claim_earnings.rs
use anchor_lang::prelude::*;
use crate::constants::*;
use crate::state::*;
use crate::error::*;

pub fn handler(ctx: Context<ClaimEarnings>) -> Result<()> {
    let clock = Clock::get()?;
    let player = &mut ctx.accounts.player;

    // Update pending earnings first
    player.update_pending_earnings(clock.unix_timestamp);
    
    let claimable_amount = player.get_claimable_amount();
    
    if claimable_amount == 0 {
        return Err(SolanaMafiaError::NoEarningsToClaim.into());
    }
    
    // TODO: Implement actual transfer from treasury PDA to player
    // This is a placeholder implementation

    // For now, just update player state
    player.claim_all_earnings();
    msg!("Earnings claimed!");
    msg!("Player: {}", player.owner);
    msg!("Amount claimed: {} lamports", claimable_amount);
    msg!("Total earned: {} lamports", player.total_earned);
    Ok(())
}

#[derive(Accounts)]
pub struct ClaimEarnings<'info> {
    #[account(mut)]
    pub player_owner: Signer<'info>,
    
    #[account(
        mut,
        seeds = [PLAYER_SEED, player_owner.key().as_ref()],
        bump = player.bump,
        constraint = player.owner == player_owner.key()
    )]
    pub player: Account<'info, Player>,
}

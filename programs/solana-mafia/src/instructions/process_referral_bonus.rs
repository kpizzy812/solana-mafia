// instructions/process_referral_bonus.rs
use anchor_lang::prelude::*;
use crate::constants::{PLAYER_SEED, GAME_STATE_SEED};
use crate::state::{Player, GameState};
use crate::error::SolanaMafiaError;

/// Simple instruction to add referral earnings to a player's balance
/// Called from backend when referral bonus should be credited
pub fn handler(
    ctx: Context<AddReferralEarnings>,
    amount: u64,
) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let game_state = &mut ctx.accounts.game_state;
    
    // Add bonus to player's pending referral earnings - ИСПРАВЛЕНО: обрабатываем Result
    player.add_referral_bonus(amount)?;
    
    // Update game statistics
    game_state.add_referral_payment(amount);
    
    msg!("Referral bonus added!");
    msg!("Player: {}", player.owner);
    msg!("Bonus amount: {} lamports", amount);
    msg!("Total pending referral: {} lamports", player.pending_referral_earnings);
    
    Ok(())
}

#[derive(Accounts)]
pub struct AddReferralEarnings<'info> {
    /// Player receiving the referral bonus
    #[account(
        mut,
        seeds = [PLAYER_SEED, player.owner.as_ref()],
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
}
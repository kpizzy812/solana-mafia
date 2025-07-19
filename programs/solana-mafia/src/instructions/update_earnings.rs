// instructions/update_earnings.rs
use anchor_lang::prelude::*;
use crate::constants::*;
use crate::state::*;
use crate::error::*;

/// Crank instruction to update player's pending earnings
/// Can be called by anyone to update any player's earnings
pub fn handler(ctx: Context<UpdateEarnings>) -> Result<()> {
    let clock = Clock::get()?;
    let player = &mut ctx.accounts.player;
    
    // 🔒 RATE LIMITING: проверяем время последнего обновления
    if player.businesses.len() > 0 {
        // Ищем последнее обновление среди всех бизнесов
        let last_update = player.businesses.iter()
            .map(|b| b.last_claim)
            .max()
            .unwrap_or(0);
            
        let time_since_last_update = clock.unix_timestamp - last_update;
        if time_since_last_update < UPDATE_EARNINGS_COOLDOWN {
            return Err(SolanaMafiaError::TooEarlyToUpdate.into());
        }
    }
    
    // Update pending earnings for all businesses
    let old_pending = player.pending_earnings;
    player.update_pending_earnings(clock.unix_timestamp)?;
    
    let new_earnings = player.pending_earnings
        .checked_sub(old_pending)
        .ok_or(SolanaMafiaError::MathOverflow)?;
    
    msg!("Earnings updated for player: {}", player.owner);
    msg!("New earnings added: {} lamports", new_earnings);
    msg!("Total pending: {} lamports", player.pending_earnings);
    msg!("Active businesses: {}", player.businesses.iter().filter(|b| b.is_active).count());
    
    Ok(())
}

#[derive(Accounts)]
pub struct UpdateEarnings<'info> {
    /// Player whose earnings are being updated
    #[account(
        mut,
        seeds = [PLAYER_SEED, player.owner.as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
}
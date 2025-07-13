// instructions/process_referral_bonus.rs
use anchor_lang::prelude::*;
use crate::constants::*;
use crate::state::*;
use crate::error::*;

pub fn handler(
    ctx: Context<ProcessReferralBonus>,
    deposit_amount: u64,
) -> Result<()> {
    let player = &ctx.accounts.player;
    let game_state = &mut ctx.accounts.game_state;
    
    // Check if player has a referrer
    if player.referrer.is_none() {
        msg!("Player has no referrer, skipping bonus");
        return Ok(());
    }
    
    let referrer = &mut ctx.accounts.referrer;
    
    // Calculate Level 1 referral bonus (5% of deposit)
    let bonus_amount = (deposit_amount * REFERRAL_RATES[0] as u64) / 100;
    
    // Add bonus to referrer's pending earnings
    referrer.add_referral_bonus(bonus_amount);
    
    // Update game statistics
    game_state.add_referral_payment(bonus_amount);
    
    msg!("Referral bonus processed!");
    msg!("Referrer: {}", referrer.owner);
    msg!("Bonus amount: {} lamports", bonus_amount);
    msg!("Level: 1 ({}%)", REFERRAL_RATES[0]);
    
    // TODO: Process Level 2 and Level 3 referrals
    // This would require additional accounts for referrer's referrer, etc.
    
    Ok(())
}

#[derive(Accounts)]
#[instruction(deposit_amount: u64)]
pub struct ProcessReferralBonus<'info> {
    /// Player who made the deposit
    #[account(
        seeds = [PLAYER_SEED, player.owner.as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
    
    /// Referrer receiving the bonus
    #[account(
        mut,
        seeds = [PLAYER_SEED, player.referrer.unwrap().as_ref()],
        bump = referrer.bump
    )]
    pub referrer: Account<'info, Player>,
    
    /// Game state for statistics
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
}
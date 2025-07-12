// instructions/pay_referral_bonus.rs
use anchor_lang::prelude::*;
use crate::constants::*;
use crate::state::*;
use crate::error::*;

pub fn handler(
    ctx: Context<PayReferralBonus>,
    deposit_amount: u64,
    referral_level: u8, // 1, 2, или 3
) -> Result<()> {
    let game_state = &mut ctx.accounts.game_state;
    
    // Validate referral level
    if referral_level == 0 || referral_level > MAX_REFERRAL_LEVELS {
        return Err(SolanaMafiaError::InvalidReferrer.into());
    }
    
    // Calculate bonus based on level
    let rate_index = (referral_level - 1) as usize;
    let bonus = (deposit_amount * REFERRAL_RATES[rate_index] as u64) / 100;
    
    // Pay bonus to referrer
    let referrer = &mut ctx.accounts.referrer;
    referrer.referral_earnings += bonus;
    
    // Update game statistics
    game_state.add_referral_payment(bonus);
    
    msg!("Referral Level {} bonus: {} lamports paid to {}", 
         referral_level, bonus, referrer.owner);
    
    Ok(())
}

#[derive(Accounts)]
#[instruction(deposit_amount: u64, referral_level: u8)]
pub struct PayReferralBonus<'info> {
    /// The referrer receiving the bonus
    #[account(mut)]
    pub referrer: Account<'info, Player>,
    
    /// Game state for statistics
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
}
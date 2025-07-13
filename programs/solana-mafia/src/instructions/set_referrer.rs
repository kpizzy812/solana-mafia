// instructions/set_referrer.rs
use anchor_lang::prelude::*;
use crate::constants::*;
use crate::state::*;
use crate::error::*;
use crate::utils::*;

pub fn handler(
    ctx: Context<SetReferrer>,
    referrer_key: Pubkey,
) -> Result<()> {
    let player = &mut ctx.accounts.player;
    
    // Validate referrer
    validate_referrer(ctx.accounts.owner.key(), Some(referrer_key))?;
    
    // Check if player already has a referrer
    if player.referrer.is_some() {
        msg!("Player already has a referrer");
        return Ok(());
    }
    
    // Set referrer
    player.referrer = Some(referrer_key);
    
    msg!("Referrer set successfully!");
    msg!("Player: {}", player.owner);
    msg!("Referrer: {}", referrer_key);
    
    Ok(())
}

#[derive(Accounts)]
pub struct SetReferrer<'info> {
    /// Player setting referrer
    #[account(mut)]
    pub owner: Signer<'info>,
    
    /// Player account
    #[account(
        mut,
        seeds = [PLAYER_SEED, owner.key().as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
    
    /// Referrer player account (to validate it exists)
    #[account(
        seeds = [PLAYER_SEED, referrer.owner.as_ref()],
        bump = referrer.bump
    )]
    pub referrer: Account<'info, Player>,
}
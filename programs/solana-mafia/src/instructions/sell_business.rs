use anchor_lang::prelude::*;
use crate::constants::*;
use crate::state::*;
use crate::error::*;
use crate::utils::calculations::*;

pub fn handler(
    ctx: Context<SellBusiness>,
    business_index: u8,
) -> Result<()> {
    let clock = Clock::get()?;
    let player = &mut ctx.accounts.player;
    let game_state = &mut ctx.accounts.game_state;
    
    // Get business
    let business = player.get_business(business_index)
        .ok_or(SolanaMafiaError::BusinessNotFound)?;
    
    if !business.is_active {
        return Err(SolanaMafiaError::BusinessNotFound.into());
    }
    
    // Calculate days held
    let days_held = business.days_since_created(clock.unix_timestamp);
    
    // Calculate early sell fee
    let sell_fee = calculate_early_sell_fee(business.invested_amount, days_held);
    let return_amount = business.invested_amount - sell_fee;
    
    // TODO: Implement actual transfer from treasury PDA to player
    // This is a placeholder implementation
    
    // Deactivate business
    let business_mut = player.get_business_mut(business_index).unwrap();
    business_mut.is_active = false;
    
    // Update statistics
    game_state.add_withdrawal(return_amount);
    
    msg!("Business sold!");
    msg!("Days held: {}", days_held);
    msg!("Sell fee: {} lamports", sell_fee);
    msg!("Return amount: {} lamports", return_amount);
    
    Ok(())
}

#[derive(Accounts)]
pub struct SellBusiness<'info> {
    #[account(mut)]
    pub player_owner: Signer<'info>,
    
    #[account(
        mut,
        seeds = [PLAYER_SEED, player_owner.key().as_ref()],
        bump = player.bump,
        constraint = player.owner == player_owner.key()
    )]
    pub player: Account<'info, Player>,
    
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
    
    #[account(
        mut,
        seeds = [TREASURY_SEED],
        bump = treasury_pda.bump
    )]
    pub treasury_pda: Account<'info, Treasury>,
}
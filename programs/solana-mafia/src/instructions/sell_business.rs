// instructions/sell_business.rs
use anchor_lang::prelude::*;
use anchor_lang::system_program;
use super::*;

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
    
    // Calculate early sell fee using constants
    let sell_fee_percent = if days_held < EARLY_SELL_FEES.len() as u64 {
        EARLY_SELL_FEES[days_held as usize]
    } else {
        FINAL_SELL_FEE_PERCENT
    };
    
    let sell_fee = (business.invested_amount * sell_fee_percent as u64) / 100;
    let return_amount = business.invested_amount - sell_fee;
    
    // Check if treasury has enough funds
    let treasury_balance = ctx.accounts.treasury_pda.to_account_info().lamports();
    if treasury_balance < return_amount {
        return Err(ProgramError::InsufficientFunds.into());
    }
    
    // 🎯 Sol transfer from treasury_pda to player wallet
    let treasury_seeds = &[
        TREASURY_SEED,
        &[ctx.accounts.treasury_pda.bump],
    ];
    let treasury_signer = &[&treasury_seeds[..]];

    // Making transfer using system_program::transfer with proper signer
    system_program::transfer(
        CpiContext::new_with_signer(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.treasury_pda.to_account_info(),
                to: ctx.accounts.player_owner.to_account_info(),
            },
            treasury_signer,
        ),
        return_amount,
    )?;
    
    // Deactivate business
    let business_mut = player.get_business_mut(business_index).unwrap();
    business_mut.is_active = false;
    
    // Update statistics
    game_state.add_withdrawal(return_amount);
    
    msg!("Business sold successfully!");
    msg!("Days held: {}", days_held);
    msg!("Sell fee: {}% ({} lamports)", sell_fee_percent, sell_fee);
    msg!("Return amount: {} lamports", return_amount);
    msg!("Treasury fee collected: {} lamports", sell_fee);
    
    Ok(())
}

#[derive(Accounts)]
pub struct SellBusiness<'info> {
    /// Player selling the business
    #[account(mut)]
    pub player_owner: Signer<'info>,
    
    /// Player account
    #[account(
        mut,
        seeds = [PLAYER_SEED, player_owner.key().as_ref()],
        bump = player.bump,
        constraint = player.owner == player_owner.key()
    )]
    pub player: Account<'info, Player>,
    
    /// Treasury PDA holding the funds
    #[account(
        mut,
        seeds = [TREASURY_SEED],
        bump = treasury_pda.bump
    )]
    pub treasury_pda: Account<'info, Treasury>,
    
    /// Game state for statistics
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
    
    /// System program for transfers
    pub system_program: Program<'info, System>,
}
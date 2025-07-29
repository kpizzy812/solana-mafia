// instructions/claim_earnings.rs
use anchor_lang::prelude::*;
use anchor_lang::system_program;
use crate::constants::{PLAYER_SEED, TREASURY_SEED, GAME_STATE_SEED, CLAIM_EARNINGS_COOLDOWN};
use crate::state::{Player, Treasury, GameState};
use crate::error::SolanaMafiaError;

pub fn handler(ctx: Context<ClaimEarnings>) -> Result<()> {
    let clock = Clock::get()?;
    let player = &mut ctx.accounts.player;
    let game_state = &mut ctx.accounts.game_state;

    // 🔒 RATE LIMITING: проверяем время последнего вывода
    if player.businesses.len() > 0 {
        let last_claim = player.businesses.iter()
            .map(|b| b.last_claim)
            .max()
            .unwrap_or(0);
            
        let time_since_last_claim = clock.unix_timestamp - last_claim;
        if time_since_last_claim < CLAIM_EARNINGS_COOLDOWN {
            return Err(SolanaMafiaError::TooEarlyToClaim.into());
        }
    }

    // Update pending earnings first
    player.update_pending_earnings(clock.unix_timestamp)?;
    
    let claimable_amount = player.get_claimable_amount()?;
    
    if claimable_amount == 0 {
        return Err(SolanaMafiaError::NoEarningsToClaim.into());
    }

    // Улучшенная проверка баланса treasury
    let treasury_balance = ctx.accounts.treasury_pda.to_account_info().lamports();
    
    // Проверяем что в treasury достаточно средств + запас 10%
    let required_balance = claimable_amount
        .checked_mul(110)
        .and_then(|x| x.checked_div(100))
        .ok_or(SolanaMafiaError::MathOverflow)?;
    
    if treasury_balance < required_balance {
        msg!("⚠️ Недостаточно средств в treasury!");
        msg!("Требуется: {}, доступно: {}", required_balance, treasury_balance);
        return Err(ProgramError::InsufficientFunds.into());
    }

    // Пересчитываем claimable_amount после всех проверок
    let final_claimable_amount = player.get_claimable_amount()?;

    // 🎯 БЕЗОПАСНЫЙ ПЕРЕВОД SOL из treasury_pda к игроку используя system_program
    let treasury_seeds = &[
        TREASURY_SEED,
        &[ctx.accounts.treasury_pda.bump],
    ];
    let treasury_signer = &[&treasury_seeds[..]];

    system_program::transfer(
        CpiContext::new_with_signer(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.treasury_pda.to_account_info(),
                to: ctx.accounts.player_owner.to_account_info(),
            },
            treasury_signer,
        ),
        final_claimable_amount,
    )?;

    // Обновляем состояние игрока
    player.claim_all_earnings()?;
    
    // Обновляем глобальную статистику с защитой от overflow
    game_state.total_withdrawn = game_state.total_withdrawn
        .checked_add(final_claimable_amount)
        .ok_or(SolanaMafiaError::MathOverflow)?;

    msg!("💰 Безопасная выплата завершена!");
    msg!("Player: {}", player.owner);
    msg!("Amount claimed: {} lamports", final_claimable_amount);
    msg!("Treasury balance after: {}", 
         treasury_balance.checked_sub(final_claimable_amount).unwrap_or(0));
    msg!("Total system withdrawn: {} lamports", game_state.total_withdrawn);
    
    Ok(())
}

#[derive(Accounts)]
pub struct ClaimEarnings<'info> {
    /// Player who is claiming earnings
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

    /// Game state for statistics and security checks
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,

    /// System program for transfers
    pub system_program: Program<'info, System>,
}
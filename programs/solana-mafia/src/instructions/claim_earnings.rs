// instructions/claim_earnings.rs
use anchor_lang::prelude::*;
use anchor_lang::solana_program::program::invoke_signed;
use anchor_lang::solana_program::system_instruction;
use crate::constants::*;
use crate::state::*;
use crate::error::*;

pub fn handler(ctx: Context<ClaimEarnings>) -> Result<()> {
    let clock = Clock::get()?;
    let player = &mut ctx.accounts.player;
    let game_state = &mut ctx.accounts.game_state;

    // Update pending earnings first
    player.update_pending_earnings(clock.unix_timestamp);
    
    let claimable_amount = player.get_claimable_amount();
    
    if claimable_amount == 0 {
        return Err(SolanaMafiaError::NoEarningsToClaim.into());
    }

    // 🎯 РЕАЛЬНЫЙ ПЕРЕВОД SOL из treasury_pda к игроку
    let treasury_seeds = &[
        TREASURY_SEED,
        &[ctx.accounts.treasury_pda.bump],
    ];
    let treasury_signer = &[&treasury_seeds[..]];

    // Создаем инструкцию перевода
    let transfer_instruction = system_instruction::transfer(
        &ctx.accounts.treasury_pda.key(),
        &ctx.accounts.player_owner.key(),
        claimable_amount,
    );

    // Выполняем перевод с подписью treasury PDA
    invoke_signed(
        &transfer_instruction,
        &[
            ctx.accounts.treasury_pda.to_account_info(),
            ctx.accounts.player_owner.to_account_info(),
            ctx.accounts.system_program.to_account_info(),
        ],
        treasury_signer,
    )?;

    // Обновляем состояние игрока
    player.claim_all_earnings();
    
    // Обновляем глобальную статистику
    game_state.add_withdrawal(claimable_amount);

    msg!("Earnings claimed successfully!");
    msg!("Player: {}", player.owner);
    msg!("Amount claimed: {} lamports", claimable_amount);
    msg!("Total earned: {} lamports", player.total_earned);
    
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
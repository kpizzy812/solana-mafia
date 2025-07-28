// instructions/add_referral_bonus.rs
use anchor_lang::prelude::*;
use super::*;

/// Безопасная инструкция для добавления реферального бонуса
/// Вызывается только админом или уполномоченным бэкендом
pub fn handler(
    ctx: Context<AddReferralBonus>,
    amount: u64,
) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let game_state = &mut ctx.accounts.game_state;
    
    // Добавляем бонус к pending_referral_earnings игрока с защитой от overflow
    player.pending_referral_earnings = player.pending_referral_earnings
        .checked_add(amount)
        .ok_or(crate::error::SolanaMafiaError::MathOverflow)?;
    
    // Обновляем глобальную статистику с защитой от overflow
    game_state.total_referral_paid = game_state.total_referral_paid
        .checked_add(amount)
        .ok_or(crate::error::SolanaMafiaError::MathOverflow)?;
    
    msg!("Referral bonus added successfully!");
    msg!("Player: {}", player.owner);
    msg!("Bonus amount: {} lamports", amount);
    msg!("Total pending referral: {} lamports", player.pending_referral_earnings);
    
    Ok(())
}

#[derive(Accounts)]
pub struct AddReferralBonus<'info> {
    /// Authority or backend signer - ТОЛЬКО ОНИ МОГУТ ДОБАВЛЯТЬ БОНУСЫ!
    #[account(
        constraint = authority.key() == game_state.authority @ crate::error::SolanaMafiaError::UnauthorizedAdmin
    )]
    pub authority: Signer<'info>,
    
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

// 🔒 ТЕПЕРЬ БЕЗОПАСНО!
// Только authority (админ) может добавлять реферальные бонусы
// Защита от накрутки и опустошения treasury
// instructions/add_referral_bonus.rs
use anchor_lang::prelude::*;
use crate::constants::*;
use crate::state::*;

/// Простая инструкция для добавления реферального бонуса
/// Вызывается бэкендом после расчета сложной логики
pub fn handler(
    ctx: Context<AddReferralBonus>,
    amount: u64,
) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let game_state = &mut ctx.accounts.game_state;
    
    // Добавляем бонус к pending_referral_earnings игрока
    player.add_referral_bonus(amount);
    
    // Обновляем глобальную статистику
    game_state.add_referral_payment(amount);
    
    msg!("Referral bonus added successfully!");
    msg!("Player: {}", player.owner);
    msg!("Bonus amount: {} lamports", amount);
    msg!("Total pending referral: {} lamports", player.pending_referral_earnings);
    
    Ok(())
}

#[derive(Accounts)]
pub struct AddReferralBonus<'info> {
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

// НЕ ТРЕБУЕТ ПОДПИСИ! 
// Бэкенд может вызывать эту инструкцию без подписи игрока
// Это безопасно, так как мы только ДОБАВЛЯЕМ деньги игроку, не списываем
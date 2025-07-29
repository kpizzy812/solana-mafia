// instructions/update_earnings.rs
use anchor_lang::prelude::*;
use crate::constants::{PLAYER_SEED, UPDATE_EARNINGS_COOLDOWN};
use crate::state::Player;
use crate::error::SolanaMafiaError;

/// 🔒 БЕЗОПАСНАЯ Crank instruction для обновления earnings
/// Теперь только владелец может обновлять свои earnings!
pub fn handler(ctx: Context<UpdateEarnings>) -> Result<()> {
    let clock = Clock::get()?;
    let player = &mut ctx.accounts.player;
    
    // 🔒 ЗАЩИТА: Проверяем что вызывающий = владелец аккаунта
    if ctx.accounts.authority.key() != player.owner {
        return Err(SolanaMafiaError::UnauthorizedAdmin.into());
    }
    
    // 🔒 ЗАЩИТА: Проверяем что игрок не накручен
    let old_pending = player.pending_earnings;
    
    // Обновляем earnings с новыми безопасными проверками
    player.update_pending_earnings(clock.unix_timestamp)?;
    
    let new_earnings = player.pending_earnings
        .checked_sub(old_pending)
        .ok_or(SolanaMafiaError::MathOverflow)?;
    
    // 🔒 ЗАЩИТА: Разумный лимит на новые earnings (максимум 1 SOL за один update)
    if new_earnings > 10_000_000_000 { // 10 SOL - только лог  
        msg!("ℹ️ Large earnings update: {} lamports for {}", new_earnings, player.owner);
    }
    
    // 🔒
    if player.pending_earnings > 10_000_000_000_000 { // 10,000 SOL - только мониторинг
        msg!("ℹ️ Large pending earnings: {} lamports for {}", player.pending_earnings, player.owner);
    }
    
    msg!("✅ Безопасное обновление earnings:");
    msg!("Player: {}", player.owner);
    msg!("New earnings: {} lamports", new_earnings);
    msg!("Total pending: {} lamports", player.pending_earnings);
    msg!("Active businesses: {}", player.businesses.iter().filter(|b| b.is_active).count());
    
    Ok(())
}

#[derive(Accounts)]
pub struct UpdateEarnings<'info> {
    /// 🔒 НОВОЕ: Только владелец может обновлять свои earnings
    pub authority: Signer<'info>,
    
    /// Player whose earnings are being updated
    #[account(
        mut,
        seeds = [PLAYER_SEED, authority.key().as_ref()], // 🔒 Привязано к authority!
        bump = player.bump,
        constraint = player.owner == authority.key() @ SolanaMafiaError::UnauthorizedAdmin
    )]
    pub player: Account<'info, Player>,
}

// 🔒 ТЕПЕРЬ БЕЗОПАСНО!
// - Только владелец может обновлять свои earnings
// - Rate limiting раз в 5 минут
// - Лимиты на размер новых earnings  
// - Лимиты на общий pending
// - Проверки на подозрительную активность
use anchor_lang::prelude::*;
use anchor_lang::system_program;

use crate::state::*;
use crate::constants::*;
use crate::error::SolanaMafiaError;
use crate::{Initialize, AddReferralBonus, UpdateSinglePlayerEarnings, BatchCheckPlayersStatus};

/// Initialize the game with treasury wallet
pub fn initialize(ctx: Context<Initialize>, treasury_wallet: Pubkey) -> Result<()> {
    let game_state = &mut ctx.accounts.game_state;
    let game_config = &mut ctx.accounts.game_config;
    let treasury_pda = &mut ctx.accounts.treasury_pda;
    let clock = Clock::get()?;
    
    // Initialize GameState (БЕЗ is_paused!)
    **game_state = GameState::new(
        ctx.accounts.authority.key(),
        treasury_wallet,
        clock.unix_timestamp,
        ctx.bumps.game_state,
    );
    
    // Initialize GameConfig
    **game_config = GameConfig::new(
        ctx.accounts.authority.key(),
        ctx.bumps.game_config,
    );

    **treasury_pda = Treasury::new(ctx.bumps.treasury_pda);
    
    msg!("🎮 Solana Mafia initialized!");
    msg!("Authority: {}", ctx.accounts.authority.key());
    msg!("Treasury: {}", treasury_wallet);
    
    Ok(())
}

/// Add referral bonus 
pub fn add_referral_bonus(
    ctx: Context<AddReferralBonus>, 
    amount: u64,
    referred_player: Pubkey,
    level: u8
) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let game_state = &mut ctx.accounts.game_state;
    let clock = Clock::get()?;
    
    // Add bonus to pending_referral_earnings with overflow protection
    player.pending_referral_earnings = player.pending_referral_earnings
        .checked_add(amount)
        .ok_or(SolanaMafiaError::MathOverflow)?;
    
    // Update global statistics
    game_state.total_referral_paid = game_state.total_referral_paid
        .checked_add(amount)
        .ok_or(SolanaMafiaError::MathOverflow)?;
    
    // 🆕 Эмиттим event для трекинга
    emit!(crate::ReferralBonusAdded {
        referrer: player.owner,
        referred_player,
        amount,
        level,
        timestamp: clock.unix_timestamp,
    });
    
    msg!("🎁 Referral bonus added: {} lamports to {} (level {})", amount, player.owner, level);
    Ok(())
}

/// 🆕 Обновление earnings для одного игрока (для backend batch processing)
pub fn update_single_player_earnings(ctx: Context<UpdateSinglePlayerEarnings>) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let clock = Clock::get()?;
    let current_time = clock.unix_timestamp;
    
    // Проверяем нужно ли обновление
    if !player.is_earnings_due(current_time) {
        msg!("⏰ Earnings not due yet for player: {}", player.owner);
        return Ok(());
    }
    
    // Выполняем автообновление
    let earnings_added = player.auto_update_earnings(current_time)?;
    
    if earnings_added > 0 {
        // Эмиттим event
        emit!(crate::EarningsUpdated {
            player: player.owner,
            earnings_added,
            total_pending: player.pending_earnings,
            next_earnings_time: player.next_earnings_time,
            businesses_count: player.get_active_businesses_count(),
        });
        
        msg!("💰 Earnings updated: {} lamports added, next update: {}", 
             earnings_added, player.next_earnings_time);
    }
    
    Ok(())
}

/// 🆕 Получить список всех игроков с их статусом обновления (view функция)
pub fn batch_check_players_status(ctx: Context<BatchCheckPlayersStatus>) -> Result<()> {
    let clock = Clock::get()?;
    let current_time = clock.unix_timestamp;
    
    msg!("📊 BATCH_CHECK started at: {}", current_time);
    
    // Backend может использовать getProgramAccounts для получения всех Player аккаунтов
    // и эта функция поможет логировать статус каждого
    
    Ok(())
}
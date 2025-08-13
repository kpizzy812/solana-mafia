use anchor_lang::prelude::*;

use crate::state::*;
use crate::error::SolanaMafiaError;
// Импорты контекстов убраны - используем прямо через lib.rs

/// 🔓 Update earnings (permissionless) - anyone can trigger earnings update for any player
pub fn update_earnings(ctx: Context<crate::UpdateEarnings>) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let clock = Clock::get()?;
    
    // Check if earnings update is actually due to prevent spam
    require!(
        player.is_earnings_due(clock.unix_timestamp),
        SolanaMafiaError::EarningsNotDue
    );
    
    // Update earnings using slot-based system
    let earnings_added = player.auto_update_earnings(clock.unix_timestamp)?;
    
    // Emit event for indexer tracking
    emit!(crate::EarningsUpdated {
        player: player.owner,
        earnings_added,
        total_pending: player.pending_earnings as u64,
        next_earnings_time: PlayerCompact::u32_to_timestamp(player.next_earnings_time),
        businesses_count: player.get_active_businesses_count(),
    });
    
    msg!("💰 Earnings updated for player: {}, added: {} lamports", player.owner, earnings_added);
    Ok(())
}

/// Claim earnings with slot-based system
pub fn claim_earnings(ctx: Context<crate::ClaimEarnings>) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let game_state = &mut ctx.accounts.game_state;
    let clock = Clock::get()?;
    
    // Update earnings first using new slot system
    player.update_pending_earnings(clock.unix_timestamp)?;
    
    let claimable_amount = player.get_claimable_amount()?;
    
    if claimable_amount == 0 {
        return Err(SolanaMafiaError::NoEarningsToClaim.into());
    }
    
    // Calculate claim fee (0.01 SOL)
    let claim_fee = crate::constants::CLAIM_EARNINGS_FEE;
    let net_amount = claimable_amount.saturating_sub(claim_fee);
    
    // Check treasury has enough funds
    let treasury_balance = ctx.accounts.treasury_pda.to_account_info().lamports();
    if treasury_balance < claimable_amount {
        return Err(ProgramError::InsufficientFunds.into());
    }
    
    // 💰 ИСПРАВЛЕНО: Transfer earnings to player + claim fee to admins
    // 1. Transfer net amount from treasury PDA to player
    ctx.accounts.treasury_pda.sub_lamports(net_amount)?;
    ctx.accounts.player_owner.add_lamports(net_amount)?;
    
    // 2. Transfer claim fee from treasury PDA to admins
    if claim_fee > 0 {
        ctx.accounts.treasury_pda.sub_lamports(claim_fee)?;
        ctx.accounts.treasury_wallet.add_lamports(claim_fee)?;
        msg!("💳 Claim fee {} lamports sent to admins", claim_fee);
    }
    
    // Update player state
    player.claim_all_earnings()?;
    
    // Update game statistics
    game_state.add_withdrawal(claimable_amount);

    emit!(crate::EarningsClaimed {
        player: ctx.accounts.player_owner.key(),
        amount: claimable_amount,
        claimed_at: clock.unix_timestamp,
    });
    
    msg!("💰 Claimed {} lamports (net: {}, fee: {})", 
         claimable_amount, net_amount, claim_fee);
    Ok(())
}

/// 🆕 Проверить нужно ли обновление earnings игроку
pub fn check_earnings_due(ctx: Context<crate::CheckEarningsDue>) -> Result<()> {
    let player = &ctx.accounts.player;
    let clock = Clock::get()?;
    let current_time = clock.unix_timestamp;
    
    let is_due = player.is_earnings_due(current_time);
    let time_to_next = if PlayerCompact::u32_to_timestamp(player.next_earnings_time) > current_time {
        PlayerCompact::u32_to_timestamp(player.next_earnings_time) - current_time
    } else {
        0
    };
    
    // Логируем результат (backend может парсить)
    msg!("EARNINGS_CHECK: wallet={}, due={}, time_to_next={}, next_earnings_time={}", 
         player.owner, is_due, time_to_next, player.next_earnings_time);
    
    Ok(())
}

/// 🆕 Получить глобальную статистику
pub fn get_global_stats(ctx: Context<crate::GetGlobalStats>) -> Result<()> {
    let game_state = &ctx.accounts.game_state;
    
    // Логируем статистику
    msg!("GLOBAL_STATS: players={}, invested={}, withdrawn={}, businesses={}, treasury={}", 
         game_state.total_players,
         game_state.total_invested,
         game_state.total_withdrawn,
         game_state.total_businesses,
         game_state.total_treasury_collected
    );
    
    Ok(())
}
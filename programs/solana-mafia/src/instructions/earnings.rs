use anchor_lang::prelude::*;

use crate::state::*;
use crate::constants::*;
use crate::error::SolanaMafiaError;
use crate::{UpdateEarningsWithNFTCheck, ClaimEarningsWithNFTCheck, CheckEarningsDue, GetGlobalStats};

/// Update earnings (owner only)
pub fn update_earnings(ctx: Context<UpdateEarningsWithNFTCheck>) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let clock = Clock::get()?;
    
    // 🆕 Update earnings using new slot-based system
    player.update_pending_earnings(clock.unix_timestamp)?;
    
    msg!("💰 Earnings updated for player: {}", player.owner);
    Ok(())
}

/// Claim earnings with slot-based system
pub fn claim_earnings(ctx: Context<ClaimEarningsWithNFTCheck>) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let game_state = &mut ctx.accounts.game_state;
    let clock = Clock::get()?;
    
    // Update earnings first using new slot system
    player.update_pending_earnings(clock.unix_timestamp)?;
    
    let claimable_amount = player.get_claimable_amount()?;
    
    if claimable_amount == 0 {
        return Err(SolanaMafiaError::NoEarningsToClaim.into());
    }
    
    // Check treasury has enough funds
    let treasury_balance = ctx.accounts.treasury_pda.to_account_info().lamports();
    if treasury_balance < claimable_amount {
        return Err(ProgramError::InsufficientFunds.into());
    }
    
    // Transfer lamports from treasury to player
    **ctx.accounts.treasury_pda.to_account_info().try_borrow_mut_lamports()? -= claimable_amount;
    **ctx.accounts.player_owner.to_account_info().try_borrow_mut_lamports()? += claimable_amount;
    
    // Update player state
    player.claim_all_earnings()?;
    
    // Update game statistics
    game_state.add_withdrawal(claimable_amount);

    emit!(crate::EarningsClaimed {
        player: ctx.accounts.player_owner.key(),
        amount: claimable_amount,
        claimed_at: clock.unix_timestamp,
    });
    
    msg!("💰 Claimed {} lamports", claimable_amount);
    Ok(())
}

/// 🆕 Проверить нужно ли обновление earnings игроку
pub fn check_earnings_due(ctx: Context<CheckEarningsDue>) -> Result<()> {
    let player = &ctx.accounts.player;
    let clock = Clock::get()?;
    let current_time = clock.unix_timestamp;
    
    let is_due = player.is_earnings_due(current_time);
    let time_to_next = if player.next_earnings_time > current_time {
        player.next_earnings_time - current_time
    } else {
        0
    };
    
    // Логируем результат (backend может парсить)
    msg!("EARNINGS_CHECK: wallet={}, due={}, time_to_next={}, next_earnings_time={}", 
         player.owner, is_due, time_to_next, player.next_earnings_time);
    
    Ok(())
}

/// 🆕 Получить глобальную статистику
pub fn get_global_stats(ctx: Context<GetGlobalStats>) -> Result<()> {
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
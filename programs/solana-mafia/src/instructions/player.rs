use anchor_lang::prelude::*;
use anchor_lang::system_program;

use crate::state::*;
use crate::error::SolanaMafiaError;
// Импорты контекстов убраны - используем прямо через lib.rs

/// Create new player (with entry fee)
pub fn create_player(ctx: Context<crate::CreatePlayer>) -> Result<()> {
    let game_config = &ctx.accounts.game_config;
    let game_state = &mut ctx.accounts.game_state;
    let player = &mut ctx.accounts.player;
    let clock = Clock::get()?;
    
    // 🔒 УБРАЛИ ПРОВЕРКУ is_paused - игра всегда активна!
    
    // 🔒 БЕЗОПАСНОСТЬ: Проверяем что treasury_wallet соответствует game_state
    if ctx.accounts.treasury_wallet.key() != game_state.treasury_wallet {
        return Err(SolanaMafiaError::UnauthorizedAdmin.into());
    }
    
    // Get current dynamic entry fee based on total players
    let current_total_players = game_state.total_players;
    let entry_fee = game_config.get_current_entry_fee(current_total_players);
    
    system_program::transfer(
        CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.owner.to_account_info(),
                to: ctx.accounts.treasury_wallet.to_account_info(),
            },
        ),
        entry_fee,
    )?;

    // 🔒 ПРОВЕРКА: Player уже существует?
    if player.owner != Pubkey::default() {
        return Err(SolanaMafiaError::PlayerAlreadyExists.into());
    }
    
    // Initialize player
    **player = Player::new(
        ctx.accounts.owner.key(),
        ctx.bumps.player,
        clock.unix_timestamp,
    );
    player.set_has_paid_entry(true);
    
    // Update game stats
    game_state.add_player();
    game_state.total_treasury_collected = game_state.total_treasury_collected
        .checked_add(entry_fee)
        .ok_or(SolanaMafiaError::MathOverflow)?;
    
    msg!("👤 Player created! Entry fee: {} lamports", entry_fee);
    // 🆕 Эмиттим event
    emit!(crate::PlayerCreated {
        wallet: ctx.accounts.owner.key(),
        entry_fee,
        created_at: clock.unix_timestamp,
        next_earnings_time: 0, // Будет установлено при первом бизнесе
    });
    Ok(())
}

/// Health check for player data
pub fn health_check_player(ctx: Context<crate::HealthCheckPlayer>) -> Result<()> {
    let player = &ctx.accounts.player;
    let clock = Clock::get()?;
    
    // Run health check
    player.health_check(clock.unix_timestamp)?;
    
    msg!("✅ Player health check passed");
    Ok(())
}

/// 🆕 Получить данные игрока для фронтенда (с новой системой слотов)
pub fn get_player_data(ctx: Context<crate::GetPlayerData>) -> Result<()> {
    let player = &ctx.accounts.player;
    let clock = Clock::get()?;

    // Get data using new slot system
    let active_businesses = player.get_active_businesses_count();
    let time_to_next_earnings = if PlayerCompact::u32_to_timestamp(player.next_earnings_time) > clock.unix_timestamp {
        PlayerCompact::u32_to_timestamp(player.next_earnings_time) - clock.unix_timestamp
    } else {
        0
    };
    
    // Логируем основные данные
    msg!("PLAYER_DATA: wallet={}, invested={}, pending={}, businesses={}, slots={}, next_earnings={}, time_to_next={}", 
         player.owner,
         player.total_invested,
         player.pending_earnings,
         active_businesses,
         player.business_slots.len(),
         player.next_earnings_time,
         time_to_next_earnings
    );
    
    Ok(())
}

/// 🆕 Получить только валидные (принадлежащие) бизнесы игрока
pub fn get_valid_player_businesses(ctx: Context<crate::GetValidPlayerBusinesses>) -> Result<()> {
    let player = &ctx.accounts.player;
    let all_businesses = player.get_all_businesses();
    
    msg!("VALID_BUSINESSES: player={}, total_slots={}, active_businesses={}", 
         player.owner, 
         player.business_slots.len(), 
         all_businesses.len()
    );
    
    // Логируем детали каждого слота
    for (index, slot) in player.business_slots.iter().enumerate() {
        if let Some(business) = &slot.business {
            msg!("SLOT_{}: type={}, unlocked={}, slot_type={:?}, business_type={}, invested={}, active={}", 
                 index,
                 slot.slot_type() as u8,
                 slot.is_unlocked(),
                 slot.slot_type(),
                 business.business_type.to_index(),
                 business.total_invested_amount,
                 business.is_active
            );
        } else {
            msg!("SLOT_{}: type={:?}, unlocked={}, empty", 
                 index, slot.slot_type(), slot.is_unlocked());
        }
    }
    
    Ok(())
}
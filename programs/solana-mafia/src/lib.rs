use anchor_lang::prelude::*;
use anchor_lang::system_program;

pub mod constants; 
pub mod error;
pub mod state;
pub mod utils; 

use state::*;
use constants::*;
use error::SolanaMafiaError;

// ============ EVENTS ============
#[event]
pub struct PlayerCreated {
    pub wallet: Pubkey,
    pub entry_fee: u64,
    pub created_at: i64,
    pub next_earnings_time: i64,
}

#[event]
pub struct BusinessCreated {
    pub player: Pubkey,
    pub business_type: u8,
    pub invested_amount: u64,
    pub daily_rate: u16,
    pub treasury_fee: u64,
    pub created_at: i64,
}

#[event]
pub struct EarningsUpdated {
    pub player: Pubkey,
    pub earnings_added: u64,
    pub total_pending: u64,
    pub next_earnings_time: i64,
    pub businesses_count: u8,
}

#[event]
pub struct EarningsClaimed {
    pub player: Pubkey,
    pub amount: u64,
    pub claimed_at: i64,
}

#[event]
pub struct BusinessUpgraded {
    pub player: Pubkey,
    pub business_index: u8,
    pub new_level: u8,
    pub upgrade_cost: u64,
    pub new_daily_rate: u16,
}

#[event]
pub struct BusinessSold {
    pub player: Pubkey,
    pub business_index: u8,
    pub days_held: u64,
    pub sell_fee_percent: u8,
    pub return_amount: u64,
}

// ============ FRONTEND DATA STRUCTURES ============
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Debug)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub struct PlayerFrontendData {
    pub wallet: Pubkey,
    pub total_invested: u64,
    pub pending_earnings: u64,
    pub estimated_pending_earnings: u64,
    pub businesses_count: u8,
    pub next_earnings_time: i64,
    pub time_to_next_earnings: i64,
    pub active_businesses: u8,
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Debug)]
#[cfg_attr(feature = "serde", derive(serde::Serialize, serde::Deserialize))]
pub struct GlobalStats {
    pub total_players: u64,
    pub total_invested: u64,
    pub total_withdrawn: u64,
    pub total_businesses: u64,
    pub total_treasury_collected: u64,
}

declare_id!("Hnyyopg1fsQGY1JqEsp8CPZk1KjDKsAoosBJJi5ZpegU");

#[program]
pub mod solana_mafia {
    use super::*;

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

    /// Create new player (with entry fee)
    pub fn create_player(ctx: Context<CreatePlayer>) -> Result<()> {
        let game_config = &ctx.accounts.game_config;
        let game_state = &mut ctx.accounts.game_state;
        let player = &mut ctx.accounts.player;
        let clock = Clock::get()?;
        
        // 🔒 УБРАЛИ ПРОВЕРКУ is_paused - игра всегда активна!
        
        // 🔒 БЕЗОПАСНОСТЬ: Проверяем что treasury_wallet соответствует game_state
        if ctx.accounts.treasury_wallet.key() != game_state.treasury_wallet {
            return Err(SolanaMafiaError::UnauthorizedAdmin.into());
        }
        
        // Pay entry fee
        let entry_fee = game_config.entry_fee;
        
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
        
        // Initialize player
        **player = Player::new(
            ctx.accounts.owner.key(),
            None, // No referrer for now
            clock.unix_timestamp,
            ctx.bumps.player,
        );
        player.has_paid_entry = true;
        
        // Update game stats
        game_state.add_player();
        game_state.total_treasury_collected = game_state.total_treasury_collected
            .checked_add(entry_fee)
            .ok_or(SolanaMafiaError::MathOverflow)?;
        
        msg!("👤 Player created! Entry fee: {} lamports", entry_fee);
        // 🆕 Эмиттим event
    emit!(PlayerCreated {
        wallet: ctx.accounts.owner.key(),
        entry_fee,
        created_at: clock.unix_timestamp,
        next_earnings_time: 0, // Будет установлено при первом бизнесе
    });
        Ok(())
    }

    /// Create business (requires existing player)
    pub fn create_business(
        ctx: Context<CreateBusiness>,
        business_type: u8,
        deposit_amount: u64,
    ) -> Result<()> {
        let game_config = &ctx.accounts.game_config;
        let game_state = &mut ctx.accounts.game_state;
        let player = &mut ctx.accounts.player;
        let clock = Clock::get()?;
        
        // 🔒 УБРАЛИ ПРОВЕРКУ is_paused - игра всегда активна!
        
        // 🔒 БЕЗОПАСНОСТЬ: Проверяем что treasury_wallet соответствует game_state
        if ctx.accounts.treasury_wallet.key() != game_state.treasury_wallet {
            return Err(SolanaMafiaError::UnauthorizedAdmin.into());
        }
        
        // Validate business type
        if business_type as usize >= BUSINESS_TYPES_COUNT {
            return Err(SolanaMafiaError::InvalidBusinessType.into());
        }
        
        // Get business rate and validate deposit
        let daily_rate = game_config.get_business_rate(business_type as usize);
        let min_deposit = game_config.get_min_deposit(business_type as usize);
        
        if deposit_amount < min_deposit {
            return Err(SolanaMafiaError::InsufficientDeposit.into());
        }
        
        // Check business limit
        if player.businesses.len() >= MAX_BUSINESSES_PER_PLAYER as usize {
            return Err(SolanaMafiaError::MaxBusinessesReached.into());
        }
        
        // Calculate treasury fee (20% to team)
        let treasury_fee = deposit_amount * game_config.treasury_fee_percent as u64 / 100;
        let game_pool_amount = deposit_amount - treasury_fee;
        
        // Transfer treasury fee to team wallet
        system_program::transfer(
            CpiContext::new(
                ctx.accounts.system_program.to_account_info(),
                system_program::Transfer {
                    from: ctx.accounts.owner.to_account_info(),
                    to: ctx.accounts.treasury_wallet.to_account_info(),
                },
            ),
            treasury_fee,
        )?;
        
        // Transfer game pool to treasury PDA
        system_program::transfer(
            CpiContext::new(
                ctx.accounts.system_program.to_account_info(),
                system_program::Transfer {
                    from: ctx.accounts.owner.to_account_info(),
                    to: ctx.accounts.treasury_pda.to_account_info(),
                },
            ),
            game_pool_amount,
        )?;
        
        // Create business
        let business_enum = BusinessType::from_index(business_type).unwrap();
        let business = Business::new(
            business_enum,
            deposit_amount,
            daily_rate,
            clock.unix_timestamp,
        );
        
        // Add to player
        player.add_business(business)?;
        
        // Update game statistics
        game_state.add_investment(deposit_amount);
        game_state.add_treasury_collection(treasury_fee);
        game_state.add_business();
        
        // 🆕 Устанавливаем расписание начислений для первого бизнеса
        if player.businesses.len() == 1 {
            let player_seed = ctx.accounts.owner.key().to_bytes()[0] as u64;
            player.set_earnings_schedule(clock.unix_timestamp, player_seed)?;
        }

        // 🆕 Эмиттим event
        emit!(BusinessCreated {
            player: ctx.accounts.owner.key(),
            business_type,
            invested_amount: deposit_amount,
            daily_rate,
            treasury_fee,
            created_at: clock.unix_timestamp,
        });

        msg!("🏪 Business created! Type: {}, Investment: {} lamports", business_type, deposit_amount);
        Ok(())
    }

    /// Update earnings (owner only)
    pub fn update_earnings(ctx: Context<UpdateEarnings>) -> Result<()> {
        let player = &mut ctx.accounts.player;
        let clock = Clock::get()?;
        
        // Update pending earnings with safety checks
        player.update_pending_earnings(clock.unix_timestamp)?;
        
        msg!("💰 Earnings updated for player: {}", player.owner);
        msg!("Pending earnings: {} lamports", player.pending_earnings);
        
        Ok(())
    }

    /// Claim earnings with safety checks
    pub fn claim_earnings(ctx: Context<ClaimEarnings>) -> Result<()> {
        let player = &mut ctx.accounts.player;
        let game_state = &mut ctx.accounts.game_state;
        let clock = Clock::get()?;
        
        // Update earnings first
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
        
        // 🔧 ИСПРАВЛЕНО: Программный трансфер lamports без system_program
        **ctx.accounts.treasury_pda.to_account_info().try_borrow_mut_lamports()? -= claimable_amount;
        **ctx.accounts.player_owner.to_account_info().try_borrow_mut_lamports()? += claimable_amount;
        
        // Update player state
        player.claim_all_earnings()?;
        
        // Update game statistics
        game_state.add_withdrawal(claimable_amount);

        // 🆕 Эмиттим event
        emit!(EarningsClaimed {
            player: ctx.accounts.player_owner.key(),
            amount: claimable_amount,
            claimed_at: clock.unix_timestamp,
        });
        
        msg!("💰 Claimed {} lamports", claimable_amount);
        Ok(())
    }

    /// Upgrade business (donation to team)
    pub fn upgrade_business(ctx: Context<UpgradeBusiness>, business_index: u8) -> Result<()> {
        let player = &mut ctx.accounts.player;
        let game_state = &mut ctx.accounts.game_state;
        let game_config = &ctx.accounts.game_config;
        
        // Get business
        if business_index as usize >= player.businesses.len() {
            return Err(SolanaMafiaError::BusinessNotFound.into());
        }
        
        let business = &mut player.businesses[business_index as usize];
        
        if !business.is_active {
            return Err(SolanaMafiaError::BusinessNotFound.into());
        }
        
        // Check upgrade level
        if business.upgrade_level >= MAX_UPGRADE_LEVEL {
            return Err(SolanaMafiaError::InvalidUpgradeLevel.into());
        }
        
        let next_level = business.upgrade_level + 1;
        let upgrade_cost = game_config.get_upgrade_cost(next_level)
            .ok_or(SolanaMafiaError::InvalidUpgradeLevel)?;
        
        // Transfer upgrade cost to team
        system_program::transfer(
            CpiContext::new(
                ctx.accounts.system_program.to_account_info(),
                system_program::Transfer {
                    from: ctx.accounts.player_owner.to_account_info(),
                    to: ctx.accounts.treasury_wallet.to_account_info(),
                },
            ),
            upgrade_cost,
        )?;
        
        // Apply upgrade
        business.upgrade_level = next_level;
        let bonus = game_config.get_upgrade_bonus(next_level);
        business.daily_rate = business.daily_rate
            .checked_add(bonus)
            .ok_or(SolanaMafiaError::MathOverflow)?;
        
        // Update statistics
        game_state.total_treasury_collected = game_state.total_treasury_collected
            .checked_add(upgrade_cost)
            .ok_or(SolanaMafiaError::MathOverflow)?;

        // 🆕 Эмиттим event
        emit!(BusinessUpgraded {
            player: ctx.accounts.player_owner.key(),
            business_index,
            new_level: next_level,
            upgrade_cost,
            new_daily_rate: business.daily_rate,
        });
        
        msg!("⬆️ Business upgraded to level {}", next_level);
        msg!("Cost: {} lamports, New rate: {} bp", upgrade_cost, business.daily_rate);
        
        Ok(())
    }

    /// Health check for player data
    pub fn health_check_player(ctx: Context<HealthCheckPlayer>) -> Result<()> {
        let player = &ctx.accounts.player;
        let clock = Clock::get()?;
        
        // Run health check
        player.health_check(clock.unix_timestamp)?;
        
        msg!("✅ Player health check passed");
        Ok(())
    }

    /// Sell business with early exit fees
    pub fn sell_business(
        ctx: Context<SellBusiness>,
        business_index: u8,
    ) -> Result<()> {
        let player = &mut ctx.accounts.player;
        let game_state = &mut ctx.accounts.game_state;
        let clock = Clock::get()?;
        
        // Get business
        if business_index as usize >= player.businesses.len() {
            return Err(SolanaMafiaError::BusinessNotFound.into());
        }
        
        let business = &mut player.businesses[business_index as usize];
        
        if !business.is_active {
            return Err(SolanaMafiaError::BusinessNotFound.into());
        }
        
        // Calculate days held
        let days_held = business.days_since_created(clock.unix_timestamp);
        
        // Calculate early sell fee using constants
        let sell_fee_percent = match days_held {
            0..=7 => 25,
            8..=14 => 20,
            15..=21 => 15,
            22..=28 => 10,
            29..=30 => 5,
            _ => 0,
        };
        
        let sell_fee = business.invested_amount * sell_fee_percent / 100;
        let return_amount = business.invested_amount - sell_fee;
        
        // Check if treasury has enough funds
        let treasury_balance = ctx.accounts.treasury_pda.to_account_info().lamports();
        if treasury_balance < return_amount {
            return Err(ProgramError::InsufficientFunds.into());
        }
        
        // 🔧 ИСПРАВЛЕНО: Программный трансфер lamports без system_program
        **ctx.accounts.treasury_pda.to_account_info().try_borrow_mut_lamports()? -= return_amount;
        **ctx.accounts.player_owner.to_account_info().try_borrow_mut_lamports()? += return_amount;
        
        // Deactivate business
        business.is_active = false;
        
        // Update statistics
        game_state.add_withdrawal(return_amount);
        
        msg!("🔥 Business sold! Days held: {}, Fee: {}%, Return: {} lamports", 
             days_held, sell_fee_percent, return_amount);
        
        Ok(())
    }

    /// ✅ ОСТАВЛЯЕМ: Add referral bonus (admin only) - НУЖНА ДЛЯ РЕФЕРАЛЬНОЙ СИСТЕМЫ
    pub fn add_referral_bonus(ctx: Context<AddReferralBonus>, amount: u64) -> Result<()> {
        let player = &mut ctx.accounts.player;
        let game_state = &mut ctx.accounts.game_state;
        
        // Add bonus to pending_referral_earnings with overflow protection
        player.pending_referral_earnings = player.pending_referral_earnings
            .checked_add(amount)
            .ok_or(SolanaMafiaError::MathOverflow)?;
        
        // Update global statistics
        game_state.total_referral_paid = game_state.total_referral_paid
            .checked_add(amount)
            .ok_or(SolanaMafiaError::MathOverflow)?;
        
        msg!("🎁 Referral bonus added: {} lamports", amount);
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
        emit!(EarningsUpdated {
            player: player.owner,
            earnings_added,
            total_pending: player.pending_earnings,
            next_earnings_time: player.next_earnings_time,
            businesses_count: player.businesses.len() as u8,
        });
        
        msg!("💰 Earnings updated: {} lamports added, next update: {}", 
             earnings_added, player.next_earnings_time);
    }
    
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

/// 🆕 Получить список всех игроков с их статусом обновления (view функция)
pub fn batch_check_players_status(ctx: Context<BatchCheckPlayersStatus>) -> Result<()> {
    let clock = Clock::get()?;
    let current_time = clock.unix_timestamp;
    
    msg!("📊 BATCH_CHECK started at: {}", current_time);
    
    // Backend может использовать getProgramAccounts для получения всех Player аккаунтов
    // и эта функция поможет логировать статус каждого
    
    Ok(())
}

/// 🆕 Получить данные игрока для фронтенда
pub fn get_player_data(ctx: Context<GetPlayerData>) -> Result<()> {
    let player = &ctx.accounts.player;
    let clock = Clock::get()?;
    
    let frontend_data = player.get_frontend_data(clock.unix_timestamp);
    
    // Логируем основные данные
    msg!("PLAYER_DATA: wallet={}, invested={}, pending={}, businesses={}, next_earnings={}", 
         frontend_data.wallet,
         frontend_data.total_invested,
         frontend_data.pending_earnings,
         frontend_data.businesses_count,
         frontend_data.next_earnings_time
    );
    
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


}

// ===== ACCOUNT CONTEXTS =====

#[derive(Accounts)]
pub struct Initialize<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    #[account(
        init,
        payer = authority,
        space = GameState::SIZE,
        seeds = [GAME_STATE_SEED],
        bump
    )]
    pub game_state: Account<'info, GameState>,
    
    #[account(
        init,
        payer = authority,
        space = GameConfig::SIZE,
        seeds = [GAME_CONFIG_SEED],
        bump
    )]
    pub game_config: Account<'info, GameConfig>,
    
    #[account(
        init,
        payer = authority,
        space = Treasury::SIZE,
        seeds = [TREASURY_SEED],
        bump
    )]
    pub treasury_pda: Account<'info, Treasury>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct CreatePlayer<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,

    #[account(
        init,
        payer = owner,
        space = Player::SIZE,
        seeds = [PLAYER_SEED, owner.key().as_ref()],
        bump
    )]
    pub player: Account<'info, Player>,

    #[account(
        seeds = [GAME_CONFIG_SEED],
        bump = game_config.bump
    )]
    pub game_config: Account<'info, GameConfig>,

    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,

    /// Treasury wallet where entry fee goes
    /// CHECK: This is validated against game_state.treasury_wallet
    #[account(mut)]
    pub treasury_wallet: AccountInfo<'info>,

    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct CreateBusiness<'info> {
    #[account(mut)]
    pub owner: Signer<'info>,

    #[account(
        mut,
        seeds = [PLAYER_SEED, owner.key().as_ref()],
        bump = player.bump,
        constraint = player.owner == owner.key()
    )]
    pub player: Account<'info, Player>,

    #[account(
        seeds = [GAME_CONFIG_SEED],
        bump = game_config.bump
    )]
    pub game_config: Account<'info, GameConfig>,

    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,

    /// Treasury wallet where team fees go
    /// CHECK: This is validated against game_state.treasury_wallet
    #[account(mut)]
    pub treasury_wallet: AccountInfo<'info>,

    #[account(
        mut,
        seeds = [TREASURY_SEED],
        bump = treasury_pda.bump
    )]
    pub treasury_pda: Account<'info, Treasury>,

    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct UpdateEarnings<'info> {
    pub authority: Signer<'info>,
    
    #[account(
        mut,
        seeds = [PLAYER_SEED, authority.key().as_ref()],
        bump = player.bump,
        constraint = player.owner == authority.key()
    )]
    pub player: Account<'info, Player>,
}

#[derive(Accounts)]
pub struct ClaimEarnings<'info> {
    #[account(mut)]
    pub player_owner: Signer<'info>,
    
    #[account(
        mut,
        seeds = [PLAYER_SEED, player_owner.key().as_ref()],
        bump = player.bump,
        constraint = player.owner == player_owner.key()
    )]
    pub player: Account<'info, Player>,

    #[account(
        mut,
        seeds = [TREASURY_SEED],
        bump = treasury_pda.bump
    )]
    pub treasury_pda: Account<'info, Treasury>,

    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,

    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct UpgradeBusiness<'info> {
    #[account(mut)]
    pub player_owner: Signer<'info>,
    
    #[account(
        mut,
        seeds = [PLAYER_SEED, player_owner.key().as_ref()],
        bump = player.bump,
        constraint = player.owner == player_owner.key()
    )]
    pub player: Account<'info, Player>,
    
    /// Treasury wallet where upgrade fees go
    /// CHECK: This is validated against game_state.treasury_wallet
    #[account(
        mut,
        address = game_state.treasury_wallet
    )]
    pub treasury_wallet: AccountInfo<'info>,
    
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
    
    #[account(
        seeds = [GAME_CONFIG_SEED],
        bump = game_config.bump
    )]
    pub game_config: Account<'info, GameConfig>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct HealthCheckPlayer<'info> {
    #[account(
        seeds = [PLAYER_SEED, player.owner.as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
}

#[derive(Accounts)]
pub struct SellBusiness<'info> {
    #[account(mut)]
    pub player_owner: Signer<'info>,
    
    #[account(
        mut,
        seeds = [PLAYER_SEED, player_owner.key().as_ref()],
        bump = player.bump,
        constraint = player.owner == player_owner.key()
    )]
    pub player: Account<'info, Player>,
    
    #[account(
        mut,
        seeds = [TREASURY_SEED],
        bump = treasury_pda.bump
    )]
    pub treasury_pda: Account<'info, Treasury>,
    
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct AddReferralBonus<'info> {
    /// Authority (admin) - ТОЛЬКО ОНИ МОГУТ ДОБАВЛЯТЬ БОНУСЫ!
    #[account(
        constraint = authority.key() == game_state.authority @ SolanaMafiaError::UnauthorizedAdmin
    )]
    pub authority: Signer<'info>,
    
    #[account(
        mut,
        seeds = [PLAYER_SEED, player.owner.as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
    
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
}

#[derive(Accounts)]
pub struct BatchUpdateEarnings<'info> {
    /// Authority (только admin может запускать batch update)
    #[account(
        constraint = authority.key() == game_state.authority @ SolanaMafiaError::UnauthorizedAdmin
    )]
    pub authority: Signer<'info>,
    
    #[account(
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
}

#[derive(Accounts)]
pub struct GetPlayerData<'info> {
    #[account(
        seeds = [PLAYER_SEED, player.owner.as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
}

#[derive(Accounts)]
pub struct GetGlobalStats<'info> {
    #[account(
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
}

#[derive(Accounts)]
pub struct UpdateSinglePlayerEarnings<'info> {
    /// Authority (только admin может запускать updates)
    #[account(
        constraint = authority.key() == game_state.authority @ SolanaMafiaError::UnauthorizedAdmin
    )]
    pub authority: Signer<'info>,
    
    #[account(
        mut,
        seeds = [PLAYER_SEED, player.owner.as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
    
    #[account(
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
}

#[derive(Accounts)]
pub struct CheckEarningsDue<'info> {
    #[account(
        seeds = [PLAYER_SEED, player.owner.as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
}

#[derive(Accounts)]
pub struct BatchCheckPlayersStatus<'info> {
    /// Authority для batch операций
    #[account(
        constraint = authority.key() == game_state.authority @ SolanaMafiaError::UnauthorizedAdmin
    )]
    pub authority: Signer<'info>,
    
    #[account(
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
}
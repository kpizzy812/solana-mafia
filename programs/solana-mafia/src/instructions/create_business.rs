// instructions/create_business.rs
use anchor_lang::prelude::*;
use anchor_lang::system_program;
use crate::constants::*;
use crate::state::*;
use crate::error::*;

/// 🔒 НОВАЯ ИНСТРУКЦИЯ: Создание игрока (отдельно от create_business)
pub fn create_player(ctx: Context<CreatePlayer>) -> Result<()> {
    let clock = Clock::get()?;
    let game_config = &ctx.accounts.game_config;
    let game_state = &mut ctx.accounts.game_state;
    let player = &mut ctx.accounts.player;
    
    // Validate game is not paused
    if game_state.is_paused {
        return Err(SolanaMafiaError::GamePaused.into());
    }
    
    // 🔒 Платим entry fee при создании игрока
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
    
    // Initialize new player
    player.owner = ctx.accounts.owner.key();
    player.businesses = Vec::new();
    player.total_invested = 0;
    player.total_earned = 0;
    player.pending_earnings = 0;
    player.pending_referral_earnings = 0;
    player.has_paid_entry = true;
    player.created_at = clock.unix_timestamp;
    player.bump = ctx.bumps.player;
    
    // Update game stats
    game_state.add_player();
    game_state.total_treasury_collected = game_state.total_treasury_collected
        .checked_add(entry_fee)
        .ok_or(SolanaMafiaError::MathOverflow)?;
    
    msg!("✅ Новый игрок создан!");
    msg!("Player: {}", player.owner);
    msg!("Entry fee paid: {} lamports", entry_fee);
    
    Ok(())
}

/// 🔒 БЕЗОПАСНАЯ инструкция создания бизнеса (требует existing player)
pub fn handler(
    ctx: Context<CreateBusiness>,
    business_type: u8,
    deposit_amount: u64,
) -> Result<()> {
    let clock = Clock::get()?;
    let game_config = &ctx.accounts.game_config;
    let game_state = &mut ctx.accounts.game_state;
    
    // Validate game is not paused
    if game_state.is_paused {
        return Err(SolanaMafiaError::GamePaused.into());
    }

    // Validate business type
    let business_enum = BusinessType::from_index(business_type)
        .ok_or(SolanaMafiaError::InvalidBusinessType)?;
    
    let business_index = business_enum.to_index();
    let min_deposit = game_config.get_min_deposit(business_index);
    let daily_rate = game_config.get_business_rate(business_index);
    
    // Validate minimum deposit
    if deposit_amount < min_deposit {
        return Err(SolanaMafiaError::InsufficientDeposit.into());
    }

    let player = &mut ctx.accounts.player;
    
    // 🔒 ЗАЩИТА 1: Проверяем что игрок уже существует и заплатил entry fee
    if !player.has_paid_entry {
        return Err(SolanaMafiaError::EntryFeeNotPaid.into());
    }
    
    // 🔒 ЗАЩИТА 2: Rate limiting между созданием бизнесов
    if let Some(last_business) = player.businesses.last() {
        let time_since_last = clock.unix_timestamp - last_business.created_at;
        if time_since_last < BUSINESS_CREATE_COOLDOWN {
            return Err(SolanaMafiaError::TooEarlyToCreateBusiness.into());
        }
    }

    // 🔒 ЗАЩИТА 3: Жесткая проверка лимита бизнесов
    if player.businesses.len() >= MAX_BUSINESSES_PER_PLAYER as usize {
        return Err(SolanaMafiaError::MaxBusinessesReached.into());
    }

    // 🔒 ЗАЩИТА 4: Лимит на общие инвестиции игрока (максимум 1000 SOL)
    let max_total_investment = 1000_000_000_000; // 1000 SOL
    let new_total_invested = player.total_invested
        .checked_add(deposit_amount)
        .ok_or(SolanaMafiaError::MathOverflow)?;
        
    if new_total_invested > max_total_investment {
        return Err(SolanaMafiaError::InsufficientDeposit.into());
    }

    // Calculate treasury fee (20% of deposit goes to team)
    let treasury_fee = deposit_amount
        .checked_mul(game_config.treasury_fee_percent as u64)
        .and_then(|x| x.checked_div(100))
        .ok_or(SolanaMafiaError::MathOverflow)?;
        
    // Transfer treasury amount to treasury wallet (team)
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

    // Transfer game pool portion to treasury PDA (80% of deposit)
    let game_pool_amount = deposit_amount
        .checked_sub(treasury_fee)
        .ok_or(SolanaMafiaError::MathOverflow)?;
        
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

    // Create business with health check
    let business = Business::new(
        business_enum,
        deposit_amount,
        daily_rate,
        clock.unix_timestamp,
    );
    
    // Проверяем здоровье бизнеса
    business.health_check(clock.unix_timestamp)?;

    // Add business to player (с защитой от overflow)
    player.add_business(business)?;

    // Update game statistics (с защитой от overflow)
    game_state.total_invested = game_state.total_invested
        .checked_add(deposit_amount)
        .ok_or(SolanaMafiaError::MathOverflow)?;
        
    game_state.total_treasury_collected = game_state.total_treasury_collected
        .checked_add(treasury_fee)
        .ok_or(SolanaMafiaError::MathOverflow)?;
        
    game_state.total_businesses = game_state.total_businesses
        .checked_add(1)
        .ok_or(SolanaMafiaError::MathOverflow)?;

    msg!("🏪 Бизнес безопасно создан!");
    msg!("Type: {:?}", business_enum);
    msg!("Investment: {} lamports", deposit_amount);
    msg!("Daily rate: {} basis points", daily_rate);
    msg!("Treasury fee: {} lamports", treasury_fee);
    msg!("Game pool: {} lamports", game_pool_amount);
    msg!("Total businesses: {}", player.businesses.len());

    Ok(())
}

#[derive(Accounts)]
pub struct CreatePlayer<'info> {
    /// Player creating account
    #[account(mut)]
    pub owner: Signer<'info>,

    /// 🔒 НОВОЕ: Player account (СТРОГО init, не init_if_needed!)
    #[account(
        init,
        payer = owner,
        space = Player::SIZE,
        seeds = [PLAYER_SEED, owner.key().as_ref()],
        bump
    )]
    pub player: Account<'info, Player>,

    /// Game configuration
    #[account(
        seeds = [GAME_CONFIG_SEED],
        bump = game_config.bump
    )]
    pub game_config: Account<'info, GameConfig>,

    /// Game state (for statistics)
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,

    /// Treasury wallet where entry fee goes
    /// CHECK: This is validated against game_state.treasury_wallet
    #[account(
        mut,
        address = game_state.treasury_wallet
    )]
    pub treasury_wallet: AccountInfo<'info>,

    /// System program
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
#[instruction(business_type: u8, deposit_amount: u64)]
pub struct CreateBusiness<'info> {
    /// Player creating business
    #[account(mut)]
    pub owner: Signer<'info>,

    /// 🔒 ИЗМЕНЕНО: Player account (УЖЕ должен существовать!)
    #[account(
        mut,
        seeds = [PLAYER_SEED, owner.key().as_ref()],
        bump = player.bump,
        constraint = player.owner == owner.key() @ SolanaMafiaError::UnauthorizedAdmin,
        constraint = player.has_paid_entry @ SolanaMafiaError::EntryFeeNotPaid
    )]
    pub player: Account<'info, Player>,

    /// Game configuration
    #[account(
        seeds = [GAME_CONFIG_SEED],
        bump = game_config.bump
    )]
    pub game_config: Account<'info, GameConfig>,

    /// Game state (for statistics)
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,

    /// Treasury wallet where team fees go
    /// CHECK: This is validated against game_state.treasury_wallet
    #[account(
        mut,
        address = game_state.treasury_wallet
    )]
    pub treasury_wallet: AccountInfo<'info>,

    /// Treasury PDA where game pool funds are stored
    #[account(
        mut,
        seeds = [TREASURY_SEED],
        bump
    )]
    pub treasury_pda: SystemAccount<'info>,

    /// System program
    pub system_program: Program<'info, System>,
}

// 🔒 ТЕПЕРЬ БЕЗОПАСНО!
// - Разделили создание игрока и бизнеса (нет race condition)
// - Жесткие проверки существования игрока
// - Лимиты на общие инвестиции
// - Rate limiting между созданием бизнесов
// - Health checks для всех данных
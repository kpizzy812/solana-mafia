use anchor_lang::prelude::*;
use anchor_lang::system_program;

pub mod constants; 
pub mod error;
pub mod state;
pub mod utils; 

use state::*;
use constants::*;
use error::SolanaMafiaError;

declare_id!("Hnyyopg1fsQGY1JqEsp8CPZk1KjDKsAoosBJJi5ZpegU");

#[program]
pub mod solana_mafia {
    use super::*;

    /// Initialize the game with treasury wallet
    pub fn initialize(ctx: Context<Initialize>, treasury_wallet: Pubkey) -> Result<()> {
        let game_state = &mut ctx.accounts.game_state;
        let game_config = &mut ctx.accounts.game_config;
        let clock = Clock::get()?;
        
        // Initialize GameState
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
        
        // Validate game is not paused
        if game_state.is_paused {
            return Err(SolanaMafiaError::GamePaused.into());
        }
        
        // 🔒 БЕЗОПАСНОСТЬ: Проверяем что treasury_wallet соответствует game_state
        if ctx.accounts.treasury_wallet.key() != game_state.treasury_wallet {
            return Err(SolanaMafiaError::UnauthorizedAdmin.into());
        }
        
        // Pay entry fee - ИСПРАВЛЕНО: используем system_program::transfer
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
        
        // Validate game is not paused
        if game_state.is_paused {
            return Err(SolanaMafiaError::GamePaused.into());
        }
        
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
        
        // ИСПРАВЛЕНО: Безопасные трансферы через system_program
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
        
        // ИСПРАВЛЕНО: Безопасный трансфер из treasury_pda к игроку используя signer
        let treasury_seeds = &[
            TREASURY_SEED,
            &[ctx.accounts.treasury_pda.bump],
        ];
        let treasury_signer = &[&treasury_seeds[..]];
    
        system_program::transfer(
            CpiContext::new_with_signer(
                ctx.accounts.system_program.to_account_info(),
                system_program::Transfer {
                    from: ctx.accounts.treasury_pda.to_account_info(),
                    to: ctx.accounts.player_owner.to_account_info(),
                },
                treasury_signer,
            ),
            claimable_amount,
        )?;
        
        // Update player state
        player.claim_all_earnings()?;
        
        // Update game statistics
        game_state.add_withdrawal(claimable_amount);
        
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
        
        // ИСПРАВЛЕНО: Безопасный трансфер upgrade cost к команде
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
        
        // ИСПРАВЛЕНО: Безопасный трансфер из treasury_pda к игроку используя signer
        let treasury_seeds = &[
            TREASURY_SEED,
            &[ctx.accounts.treasury_pda.bump],
        ];
        let treasury_signer = &[&treasury_seeds[..]];
    
        system_program::transfer(
            CpiContext::new_with_signer(
                ctx.accounts.system_program.to_account_info(),
                system_program::Transfer {
                    from: ctx.accounts.treasury_pda.to_account_info(),
                    to: ctx.accounts.player_owner.to_account_info(),
                },
                treasury_signer,
            ),
            return_amount,
        )?;
        
        // Deactivate business
        business.is_active = false;
        
        // Update statistics
        game_state.add_withdrawal(return_amount);
        
        msg!("🔥 Business sold! Days held: {}, Fee: {}%, Return: {} lamports", 
             days_held, sell_fee_percent, return_amount);
        
        Ok(())
    }

/// Add referral bonus (admin only)
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

/// Admin: Toggle game pause state
pub fn toggle_pause(ctx: Context<TogglePause>) -> Result<()> {
    let game_state = &mut ctx.accounts.game_state;
    
    // Only authority can pause
    if ctx.accounts.authority.key() != game_state.authority {
        return Err(SolanaMafiaError::UnauthorizedAdmin.into());
    }
    
    game_state.is_paused = !game_state.is_paused;
    
    msg!("⏸️ Game pause toggled. New state: {}", game_state.is_paused);
    
    Ok(())
}

/// Emergency: Stop all financial operations
pub fn emergency_pause(ctx: Context<EmergencyPause>) -> Result<()> {
    let game_state = &mut ctx.accounts.game_state;
    
    // Only authority can activate emergency
    if ctx.accounts.authority.key() != game_state.authority {
        return Err(SolanaMafiaError::UnauthorizedAdmin.into());
    }
    
    game_state.is_paused = true;
    
    msg!("🆘 EMERGENCY PAUSE ACTIVATED!");
    msg!("All financial operations are now disabled.");
    
    Ok(())
}

/// View: Get treasury statistics
pub fn get_treasury_stats(ctx: Context<GetTreasuryStats>) -> Result<()> {
    let game_state = &ctx.accounts.game_state;
    let treasury_balance = ctx.accounts.treasury_pda.to_account_info().lamports();
    
    msg!("📊 TREASURY STATISTICS:");
    msg!("Treasury balance: {} lamports", treasury_balance);
    msg!("Total invested: {} lamports", game_state.total_invested);
    msg!("Total withdrawn: {} lamports", game_state.total_withdrawn);
    msg!("Total players: {}", game_state.total_players);
    msg!("Game paused: {}", game_state.is_paused);
    
    let pending_in_system = game_state.total_invested
        .checked_sub(game_state.total_withdrawn)
        .unwrap_or(0);
    msg!("Pending in system: {} lamports", pending_in_system);
    
    if treasury_balance < pending_in_system {
        msg!("⚠️ WARNING: Treasury balance less than pending obligations!");
    } else {
        msg!("✅ Treasury health: OK");
    }
    
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
pub struct TogglePause<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
}

#[derive(Accounts)]
pub struct EmergencyPause<'info> {
    #[account(mut)]
    pub authority: Signer<'info>,
    
    #[account(
        mut,
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
}

#[derive(Accounts)]
pub struct GetTreasuryStats<'info> {
    #[account(
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
    
    #[account(
        seeds = [TREASURY_SEED],
        bump = treasury_pda.bump
    )]
    pub treasury_pda: Account<'info, Treasury>,
}
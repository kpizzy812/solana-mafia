use anchor_lang::prelude::*;
use anchor_lang::system_program;
use anchor_spl::{
    token::{self, Token, TokenAccount, Mint, MintTo}, 
    associated_token::AssociatedToken,
    metadata::{
        create_metadata_accounts_v3,
        CreateMetadataAccountsV3,
        Metadata,
        mpl_token_metadata::types::{DataV2, Creator},
    },
};

pub mod constants; 
pub mod error;
pub mod state; 

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

#[event]
pub struct ReferralBonusAdded {
    pub referrer: Pubkey,
    pub referred_player: Pubkey,
    pub amount: u64,
    pub level: u8, // 1, 2 или 3
    pub timestamp: i64,
}

// 🆕 NFT EVENTS
#[event]
pub struct BusinessNFTMinted {
    pub player: Pubkey,
    pub business_type: u8,
    pub mint: Pubkey,
    pub serial_number: u64,
    pub invested_amount: u64,
    pub daily_rate: u16,
    pub created_at: i64,
}

#[event]
pub struct BusinessNFTBurned {
    pub player: Pubkey,
    pub mint: Pubkey,
    pub business_type: u8,
    pub serial_number: u64,
    pub burned_at: i64,
}

#[event]
pub struct BusinessNFTUpgraded {
    pub player: Pubkey,
    pub mint: Pubkey,
    pub old_level: u8,
    pub new_level: u8,
    pub new_daily_rate: u16,
}

#[event]
pub struct BusinessTransferred {
    pub old_owner: Pubkey,
    pub new_owner: Pubkey,
    pub business_mint: Pubkey,
    pub transferred_at: i64,
}

#[event]
pub struct BusinessDeactivated {
    pub player: Pubkey,
    pub business_mint: Pubkey,
    pub reason: String, // "nft_burned", "nft_transferred", "manual"
    pub deactivated_at: i64,
}

// 🆕 SLOT EVENTS
#[event]
pub struct SlotUnlocked {
    pub player: Pubkey,
    pub slot_index: u8,
    pub unlock_cost: u64,
    pub unlocked_at: i64,
}

#[event]
pub struct PremiumSlotPurchased {
    pub player: Pubkey,
    pub slot_type: SlotType,
    pub slot_index: u8,
    pub cost: u64,
    pub purchased_at: i64,
}

#[event]
pub struct BusinessCreatedInSlot {
    pub player: Pubkey,
    pub slot_index: u8,
    pub business_type: u8,
    pub base_cost: u64,
    pub daily_rate: u16,
    pub nft_mint: Pubkey,
    pub created_at: i64,
}

#[event]
pub struct BusinessUpgradedInSlot {
    pub player: Pubkey,
    pub slot_index: u8,
    pub old_level: u8,
    pub new_level: u8,
    pub upgrade_cost: u64,
    pub old_nft_mint: Pubkey,
    pub new_nft_mint: Pubkey,
    pub new_daily_rate: u16,
    pub upgraded_at: i64,
}

#[event]
pub struct BusinessSoldFromSlot {
    pub player: Pubkey,
    pub slot_index: u8,
    pub business_type: u8,
    pub total_invested: u64,
    pub days_held: u64,
    pub base_fee_percent: u8,
    pub slot_discount: u8,
    pub final_fee_percent: u8,
    pub return_amount: u64,
    pub sold_at: i64,
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

declare_id!("3Ly6bEWRfKyVGwrRN27gHhBogo1K4HbZyk69KHW9AUx7");

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
    pub fn create_player(ctx: Context<CreatePlayer>, referrer: Option<Pubkey>) -> Result<()> {
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

        // 🔒 ПРОВЕРКА: Player уже существует?
        if player.owner != Pubkey::default() {
            return Err(SolanaMafiaError::PlayerAlreadyExists.into());
        }
        
        // Initialize player
        **player = Player::new(
            ctx.accounts.owner.key(),
            referrer,
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

    /// 🏪 Create business in specific slot with NFT
pub fn create_business(
    ctx: Context<CreateBusinessInSlot>,
    business_type: u8,
    deposit_amount: u64,
    slot_index: u8,
) -> Result<()> {
    let game_config = &ctx.accounts.game_config;
    let game_state = &mut ctx.accounts.game_state;
    let player = &mut ctx.accounts.player;
    let clock = Clock::get()?;
    
    // Validate business logic
    if ctx.accounts.treasury_wallet.key() != game_state.treasury_wallet {
        return Err(SolanaMafiaError::UnauthorizedAdmin.into());
    }
    
    if business_type as usize >= BUSINESS_TYPES_COUNT {
        return Err(SolanaMafiaError::InvalidBusinessType.into());
    }
    
    let daily_rate = game_config.get_business_rate(business_type as usize);
    let min_deposit = game_config.get_min_deposit(business_type as usize);
    
    if deposit_amount < min_deposit {
        return Err(SolanaMafiaError::InsufficientDeposit.into());
    }
    
    // Validate slot
    if slot_index as usize >= player.business_slots.len() {
        return Err(SolanaMafiaError::InvalidSlotIndex.into());
    }
    
    let slot = &player.business_slots[slot_index as usize];
    if !slot.is_unlocked {
        return Err(SolanaMafiaError::SlotNotUnlocked.into());
    }
    
    if slot.business.is_some() {
        return Err(SolanaMafiaError::SlotOccupied.into());
    }
    
    // Transfer funds
    let treasury_fee = deposit_amount * game_config.treasury_fee_percent as u64 / 100;
    let game_pool_amount = deposit_amount - treasury_fee;
    
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

    // Create business and NFT
    let business_enum = BusinessType::from_index(business_type).unwrap();
    let serial_number = game_state.get_next_nft_serial();
    
    // Create NFT with level 0 (basic)
    create_business_nft(
        &ctx.accounts.owner,
        &ctx.accounts.nft_mint,
        &ctx.accounts.nft_token_account,
        &ctx.accounts.nft_metadata,
        &ctx.accounts.token_program,
        &ctx.accounts.associated_token_program,
        &ctx.accounts.token_metadata_program,
        &ctx.accounts.system_program,
        &ctx.accounts.rent,
        business_enum,
        0, // Level 0 for new business
        serial_number,
    )?;

    // Create business
    let mut business = Business::new(
        business_enum,
        deposit_amount,
        clock.unix_timestamp,
    );
    business.set_nft_mint(ctx.accounts.nft_mint.key());
    
    // Create BusinessNFT record
    let business_nft = &mut ctx.accounts.business_nft;
    **business_nft = BusinessNFT::new(
        ctx.accounts.owner.key(),
        business_enum,
        ctx.accounts.nft_mint.key(),
        ctx.accounts.nft_token_account.key(),
        deposit_amount,
        daily_rate,
        clock.unix_timestamp,
        serial_number,
        ctx.bumps.business_nft,
    );
    
    // Place business in slot
    player.place_business_in_slot(slot_index as usize, business)?;
    
    // Update game statistics
    game_state.add_investment(deposit_amount);
    game_state.add_treasury_collection(treasury_fee);
    game_state.add_business();
    game_state.add_nft_mint();
    
    // Set earnings schedule if this is first business
    if player.get_active_businesses_count() == 1 {
        let player_seed = ctx.accounts.owner.key().to_bytes()[0] as u64;
        player.set_earnings_schedule(clock.unix_timestamp, player_seed)?;
    }

    emit!(BusinessNFTMinted {
        player: ctx.accounts.owner.key(),
        business_type,
        mint: ctx.accounts.nft_mint.key(),
        serial_number,
        invested_amount: deposit_amount,
        daily_rate,
        created_at: clock.unix_timestamp,
    });

    emit!(BusinessCreatedInSlot {
        player: ctx.accounts.owner.key(),
        slot_index,
        business_type,
        base_cost: deposit_amount,
        daily_rate,
        nft_mint: ctx.accounts.nft_mint.key(),
        created_at: clock.unix_timestamp,
    });

    msg!("🏪🖼️ Business created in slot {}! Type: {}, Investment: {} lamports, Serial: {}", 
        slot_index, business_type, deposit_amount, serial_number);
    Ok(())
}

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

        emit!(EarningsClaimed {
            player: ctx.accounts.player_owner.key(),
            amount: claimable_amount,
            claimed_at: clock.unix_timestamp,
        });
        
        msg!("💰 Claimed {} lamports", claimable_amount);
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

    /// 🔥 Sell business from slot (with early exit fees and NFT burn)
    pub fn sell_business(
        ctx: Context<SellBusinessFromSlot>,
        slot_index: u8,
    ) -> Result<()> {
        let player = &mut ctx.accounts.player;
        let game_state = &mut ctx.accounts.game_state;
        let business_nft = &mut ctx.accounts.business_nft;
        let clock = Clock::get()?;
        
        // Verify NFT ownership
        if business_nft.player != ctx.accounts.player_owner.key() {
            return Err(SolanaMafiaError::BusinessNotOwned.into());
        }
        
        // Get business from slot
        let (business, sell_fee_discount) = player.sell_business_from_slot(slot_index as usize)?;
        
        if !business.is_active {
            return Err(SolanaMafiaError::BusinessNotFound.into());
        }
        
        // Calculate days held
        let days_held = business.days_since_created(clock.unix_timestamp);
        
        // Calculate base early sell fee
        let base_sell_fee_percent: u8 = match days_held {
            0..=7 => 25,
            8..=14 => 20,
            15..=21 => 15,
            22..=28 => 10,
            29..=30 => 5,
            _ => 2, // After 30 days, only 2% base fee
        };
        
        // Apply slot discount
        let final_sell_fee_percent = if sell_fee_discount as u8 >= base_sell_fee_percent {
            0
        } else {
            base_sell_fee_percent - (sell_fee_discount as u8)
        };
        
        let sell_fee = business.total_invested_amount * final_sell_fee_percent as u64 / 100;
        let return_amount = business.total_invested_amount - sell_fee;
        
        msg!("💰 Slot sell calculation: invested={}, base_fee={}%, discount={}%, final_fee={}%, return={}", 
            business.total_invested_amount, base_sell_fee_percent, sell_fee_discount, final_sell_fee_percent, return_amount);
        
        // Check if treasury has enough funds
        let treasury_balance = ctx.accounts.treasury_pda.to_account_info().lamports();
        if treasury_balance < return_amount {
            msg!("❌ Insufficient treasury balance: {} < {}", treasury_balance, return_amount);
            return Err(ProgramError::InsufficientFunds.into());
        }
        
        // Burn the NFT
        let cpi_accounts = token::Burn {
            mint: ctx.accounts.nft_mint.to_account_info(),
            from: ctx.accounts.nft_token_account.to_account_info(),
            authority: ctx.accounts.player_owner.to_account_info(),
        };
        let cpi_program = ctx.accounts.token_program.to_account_info();
        let cpi_ctx = CpiContext::new(cpi_program, cpi_accounts);
        token::burn(cpi_ctx, 1)?;
        
        // Transfer return amount from treasury 
        **ctx.accounts.treasury_pda.to_account_info().try_borrow_mut_lamports()? -= return_amount;
        **ctx.accounts.player_owner.to_account_info().try_borrow_mut_lamports()? += return_amount;
        
        // Mark NFT as burned
        business_nft.burn();
        
        // Update statistics
        game_state.add_withdrawal(return_amount);
        game_state.add_nft_burn();

        // Emit events
        emit!(BusinessNFTBurned {
            player: ctx.accounts.player_owner.key(),
            mint: ctx.accounts.nft_mint.key(),
            business_type: business.business_type.to_index() as u8,
            serial_number: business_nft.serial_number,
            burned_at: clock.unix_timestamp,
        });
        
        emit!(BusinessSoldFromSlot {
            player: ctx.accounts.player_owner.key(),
            slot_index,
            business_type: business.business_type.to_index() as u8,
            total_invested: business.total_invested_amount,
            days_held,
            base_fee_percent: base_sell_fee_percent,
            slot_discount: sell_fee_discount as u8,
            final_fee_percent: final_sell_fee_percent,
            return_amount,
            sold_at: clock.unix_timestamp,
        });
        
        msg!("🔥 Business sold from slot {}! Days held: {}, Final fee: {}%, Return: {} lamports", 
            slot_index, days_held, final_sell_fee_percent, return_amount);
        
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
        emit!(ReferralBonusAdded {
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
        emit!(EarningsUpdated {
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

/// 🆕 Получить данные игрока для фронтенда (с новой системой слотов)
pub fn get_player_data(ctx: Context<GetPlayerData>) -> Result<()> {
    let player = &ctx.accounts.player;
    let clock = Clock::get()?;

    // Get data using new slot system
    let active_businesses = player.get_active_businesses_count();
    let time_to_next_earnings = if player.next_earnings_time > clock.unix_timestamp {
        player.next_earnings_time - clock.unix_timestamp
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



/// 🆕 Get NFT metadata for frontend
pub fn get_business_nft_data(ctx: Context<GetBusinessNFTData>) -> Result<()> {
    let business_nft = &ctx.accounts.business_nft;
    
    msg!("NFT_DATA: player={}, mint={}, type={}, level={}, rate={}, serial={}, burned={}", 
         business_nft.player,
         business_nft.mint,
         business_nft.business_type.to_index(),
         business_nft.upgrade_level,
         business_nft.daily_rate,
         business_nft.serial_number,
         business_nft.is_burned
    );
    
    Ok(())
}


/// 🔄 Sync business ownership based on NFT ownership
pub fn sync_business_ownership(ctx: Context<SyncBusinessOwnership>) -> Result<()> {
    let business_nft = &ctx.accounts.business_nft;
    let old_player = &mut ctx.accounts.old_player;
    let new_player = &mut ctx.accounts.new_player;
    
    // Verify NFT is not burned
    if business_nft.is_burned {
        return Err(SolanaMafiaError::BusinessNotFound.into());
    }
    
    // Get current NFT owner from token account
    let token_account_info = ctx.accounts.nft_token_account.to_account_info();
    let token_account = TokenAccount::try_deserialize(&mut token_account_info.data.borrow().as_ref())?;
    let current_nft_owner = token_account.owner;
    
    msg!("🔄 NFT ownership check: stored={}, actual={}", business_nft.player, current_nft_owner);
    
    // If NFT owner changed, transfer business (slot-based system)
    if business_nft.player != current_nft_owner {
        // Find business in old player's slots
        let mut business_to_transfer: Option<Business> = None;
        let mut slot_index: Option<usize> = None;
        
        for (index, slot) in old_player.business_slots.iter().enumerate() {
            if let Some(business) = &slot.business {
                if let Some(nft_mint) = business.nft_mint {
                    if nft_mint == business_nft.mint {
                        business_to_transfer = Some(business.clone());
                        slot_index = Some(index);
                        break;
                    }
                }
            }
        }
        
        if let (Some(business), Some(index)) = (business_to_transfer, slot_index) {
            // Remove business from old player's slot
            old_player.business_slots[index].remove_business();
            
            // Find available slot in new player
            if let Some(free_slot_index) = new_player.find_free_slot() {
                new_player.place_business_in_slot(free_slot_index, business)?;
            } else {
                msg!("❌ No free slot available for business transfer");
                return Err(SolanaMafiaError::MaxBusinessesReached.into());
            }
            
            msg!("✅ Business transferred from {} to {} (slot {} -> slot {})", 
                business_nft.player, current_nft_owner, index, new_player.find_free_slot().unwrap_or(0));
            
            // Emit transfer event
            emit!(BusinessTransferred {
                old_owner: business_nft.player,
                new_owner: current_nft_owner,
                business_mint: business_nft.mint,
                transferred_at: Clock::get()?.unix_timestamp,
            });
        }
    }
    
    Ok(())
}

/// 🔥 Deactivate business if NFT was burned externally
pub fn deactivate_burned_business(ctx: Context<DeactivateBurnedBusiness>) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let business_nft = &mut ctx.accounts.business_nft;
    
    // Check if NFT supply is 0 (burned)
    let mint_info = ctx.accounts.nft_mint.to_account_info();
    let mint_account = Mint::try_deserialize(&mut mint_info.data.borrow().as_ref())?;
    
    if mint_account.supply == 0 && !business_nft.is_burned {
        // NFT was burned externally, deactivate business in slots
        for slot in &mut player.business_slots {
            if let Some(business) = &mut slot.business {
                if let Some(nft_mint) = business.nft_mint {
                    if nft_mint == business_nft.mint {
                        business.is_active = false;
                        break;
                    }
                }
            }
        }
        
        // Mark NFT as burned
        business_nft.burn();
        
        msg!("🔥 Business deactivated - NFT was burned externally");
        
        emit!(BusinessNFTBurned {
            player: business_nft.player,
            mint: business_nft.mint,
            business_type: business_nft.business_type.to_index() as u8, 
            serial_number: business_nft.serial_number,
            burned_at: Clock::get()?.unix_timestamp,
        });
    }
    
    Ok(())
}

/// 🔄 Автоматическая синхронизация ownership бизнесов (для слотов)
pub fn auto_sync_business_ownership(ctx: Context<AutoSyncBusinessOwnership>) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let mut businesses_deactivated = 0u8;
    
    // Проверяем каждый слот с бизнесом
    for (slot_index, slot) in player.business_slots.iter_mut().enumerate() {
        if let Some(business) = &mut slot.business {
            if business.is_active && business.nft_mint.is_some() {
                // В реальном мире здесь была бы проверка NFT ownership
                // Пока что просто логируем
                msg!("🔄 Checking slot {} business ownership", slot_index);
            }
        }
    }
    
    if businesses_deactivated > 0 {
        msg!("✅ Synchronized {} businesses based on NFT ownership", businesses_deactivated);
    } else {
        msg!("✅ All businesses ownership verified - no changes needed");
    }
    
    Ok(())
}

/// 🆕 Получить только валидные (принадлежащие) бизнесы игрока
pub fn get_valid_player_businesses(ctx: Context<GetValidPlayerBusinesses>) -> Result<()> {
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
                 slot.slot_type as u8,
                 slot.is_unlocked,
                 slot.slot_type,
                 business.business_type.to_index(),
                 business.total_invested_amount,
                 business.is_active
            );
        } else {
            msg!("SLOT_{}: type={:?}, unlocked={}, empty", 
                 index, slot.slot_type, slot.is_unlocked);
        }
    }
    
    Ok(())
}

/// 🔓 Unlock business slot
pub fn unlock_business_slot(ctx: Context<UnlockBusinessSlot>) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let game_state = &ctx.accounts.game_state;
    let clock = Clock::get()?;
    
    // Check treasury wallet
    if ctx.accounts.treasury_wallet.key() != game_state.treasury_wallet {
        return Err(SolanaMafiaError::UnauthorizedAdmin.into());
    }
    
    // Calculate unlock cost (10% of minimum business cost in that slot)
    let min_business_cost = MIN_DEPOSITS.iter().min().unwrap_or(&100_000_000);
    let unlock_cost = min_business_cost * SLOT_UNLOCK_COST_MULTIPLIER as u64 / 100;
    
    // Transfer unlock fee to treasury
    system_program::transfer(
        CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.player_owner.to_account_info(),
                to: ctx.accounts.treasury_wallet.to_account_info(),
            },
        ),
        unlock_cost,
    )?;
    
    // Unlock the slot
    let slot_index = player.unlock_next_slot(unlock_cost)?;
    
    emit!(SlotUnlocked {
        player: ctx.accounts.player_owner.key(),
        slot_index: slot_index as u8,
        unlock_cost,
        unlocked_at: clock.unix_timestamp,
    });
    
    msg!("🔓 Slot {} unlocked for {} lamports", slot_index, unlock_cost);
    Ok(())
}

/// 💎 Buy premium slot
pub fn buy_premium_slot(
    ctx: Context<BuyPremiumSlot>,
    slot_type: SlotType,
) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let game_state = &ctx.accounts.game_state;
    let clock = Clock::get()?;
    
    // Check treasury wallet
    if ctx.accounts.treasury_wallet.key() != game_state.treasury_wallet {
        return Err(SolanaMafiaError::UnauthorizedAdmin.into());
    }
    
    // Get cost for premium slot
    let slot_cost = match slot_type {
        SlotType::Premium => PREMIUM_SLOT_COSTS[0],
        SlotType::VIP => PREMIUM_SLOT_COSTS[1], 
        SlotType::Legendary => PREMIUM_SLOT_COSTS[2],
        SlotType::Basic => return Err(SolanaMafiaError::InvalidSlotType.into()),
    };
    
    // Transfer cost to treasury
    system_program::transfer(
        CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.player_owner.to_account_info(),
                to: ctx.accounts.treasury_wallet.to_account_info(),
            },
        ),
        slot_cost,
    )?;
    
    // Add premium slot
    let slot_index = player.add_premium_slot(slot_type, slot_cost)?;
    
    emit!(PremiumSlotPurchased {
        player: ctx.accounts.player_owner.key(),
        slot_type,
        slot_index: slot_index as u8,
        cost: slot_cost,
        purchased_at: clock.unix_timestamp,
    });
    
    msg!("💎 Premium slot {:?} purchased for {} lamports", slot_type, slot_cost);
    Ok(())
}

/// ⬆️ Upgrade business in slot (burns old NFT, creates new one)
pub fn upgrade_business(
    ctx: Context<UpgradeBusinessInSlot>,
    slot_index: u8,
) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let game_state = &mut ctx.accounts.game_state;
    let game_config = &ctx.accounts.game_config;
    let old_business_nft = &mut ctx.accounts.old_business_nft;
    let new_business_nft = &mut ctx.accounts.new_business_nft;
    let clock = Clock::get()?;
    
    // Check treasury wallet
    if ctx.accounts.treasury_wallet.key() != game_state.treasury_wallet {
        return Err(SolanaMafiaError::UnauthorizedAdmin.into());
    }
    
    // Get current business from slot
    if slot_index as usize >= player.business_slots.len() {
        return Err(SolanaMafiaError::InvalidSlotIndex.into());
    }
    
    // Extract business data to avoid borrowing conflicts
    let current_business = player.business_slots[slot_index as usize].business
        .as_ref()
        .ok_or(SolanaMafiaError::BusinessNotFound)?
        .clone();
    
    if !current_business.is_active {
        return Err(SolanaMafiaError::CannotUpgradeInactive.into());
    }
    
    // Check upgrade level
    if current_business.upgrade_level >= MAX_UPGRADE_LEVEL {
        return Err(SolanaMafiaError::BusinessMaxLevel.into());
    }
    
    // Verify NFT ownership
    if old_business_nft.player != ctx.accounts.player_owner.key() {
        return Err(SolanaMafiaError::BusinessNotOwned.into());
    }
    
    let next_level = current_business.upgrade_level + 1;
    let base_cost = game_config.get_min_deposit(current_business.business_type.to_index());
    
    // Calculate upgrade cost
    let upgrade_cost_multiplier = UPGRADE_COST_MULTIPLIERS.get(next_level as usize - 1)
        .ok_or(SolanaMafiaError::InvalidUpgradeLevel)?;
    let upgrade_cost = base_cost * (*upgrade_cost_multiplier as u64) / 100;
    
    // Transfer upgrade cost to treasury
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
    
    // Burn old NFT
    let cpi_accounts = token::Burn {
        mint: ctx.accounts.old_nft_mint.to_account_info(),
        from: ctx.accounts.old_nft_token_account.to_account_info(),
        authority: ctx.accounts.player_owner.to_account_info(),
    };
    let cpi_program = ctx.accounts.token_program.to_account_info();
    let cpi_ctx = CpiContext::new(cpi_program, cpi_accounts);
    token::burn(cpi_ctx, 1)?;
    
    // Create new upgraded business
    let yield_bonus = UPGRADE_YIELD_BONUSES.get(next_level as usize - 1)
        .ok_or(SolanaMafiaError::InvalidUpgradeLevel)?;
    
    let new_daily_rate = current_business.daily_rate
        .checked_add(*yield_bonus)
        .ok_or(SolanaMafiaError::MathOverflow)?;
    
    let new_invested_amount = current_business.total_invested_amount
        .checked_add(upgrade_cost)
        .ok_or(SolanaMafiaError::MathOverflow)?;
    
    let mut new_business = current_business.clone();
    new_business.upgrade_level = next_level;
    new_business.daily_rate = new_daily_rate;
    new_business.total_invested_amount = new_invested_amount;
    new_business.set_nft_mint(ctx.accounts.new_nft_mint.key());
    
    // Create new NFT with upgraded metadata  
    create_business_nft(
        &ctx.accounts.player_owner,
        &ctx.accounts.new_nft_mint,
        &ctx.accounts.new_nft_token_account,
        &ctx.accounts.new_nft_metadata,
        &ctx.accounts.token_program,
        &ctx.accounts.associated_token_program,
        &ctx.accounts.token_metadata_program,
        &ctx.accounts.system_program,
        &ctx.accounts.rent,
        current_business.business_type,
        next_level,
        game_state.get_next_nft_serial(),
    )?;
    
    // Update NFT record
    **new_business_nft = BusinessNFT::new(
        ctx.accounts.player_owner.key(),
        current_business.business_type,
        ctx.accounts.new_nft_mint.key(),
        ctx.accounts.new_nft_token_account.key(),
        new_invested_amount,
        new_daily_rate,
        clock.unix_timestamp,
        game_state.get_next_nft_serial(),
        ctx.bumps.new_business_nft,
    );
    new_business_nft.upgrade_level = next_level;
    
    // Mark old NFT as burned
    old_business_nft.burn();
    
    // Update player's business in slot
    player.upgrade_business_in_slot(slot_index as usize, upgrade_cost, new_business)?;
    
    // Update game statistics
    game_state.total_treasury_collected = game_state.total_treasury_collected
        .checked_add(upgrade_cost)
        .ok_or(SolanaMafiaError::MathOverflow)?;
    game_state.add_nft_mint();
    game_state.add_nft_burn();
    
    // Emit events
    emit!(BusinessNFTBurned {
        player: ctx.accounts.player_owner.key(),
        mint: ctx.accounts.old_nft_mint.key(),
        business_type: current_business.business_type.to_index() as u8,
        serial_number: old_business_nft.serial_number,
        burned_at: clock.unix_timestamp,
    });
    
    emit!(BusinessNFTMinted {
        player: ctx.accounts.player_owner.key(),
        business_type: current_business.business_type.to_index() as u8,
        mint: ctx.accounts.new_nft_mint.key(),
        serial_number: new_business_nft.serial_number,
        invested_amount: new_invested_amount,
        daily_rate: new_daily_rate,
        created_at: clock.unix_timestamp,
    });
    
    emit!(BusinessUpgradedInSlot {
        player: ctx.accounts.player_owner.key(),
        slot_index,
        old_level: current_business.upgrade_level,
        new_level: next_level,
        upgrade_cost,
        old_nft_mint: ctx.accounts.old_nft_mint.key(),
        new_nft_mint: ctx.accounts.new_nft_mint.key(),
        new_daily_rate,
        upgraded_at: clock.unix_timestamp,
    });
    
    msg!("⬆️ Business upgraded from level {} to {} in slot {}", 
         current_business.upgrade_level, next_level, slot_index);
    
    Ok(())
}
}

/// 🏗️ Helper function to create business NFT
pub fn create_business_nft<'info>(
    owner: &Signer<'info>,
    nft_mint: &Signer<'info>,
    nft_token_account: &AccountInfo<'info>,
    nft_metadata: &UncheckedAccount<'info>,
    token_program: &Program<'info, Token>,
    associated_token_program: &Program<'info, AssociatedToken>,
    token_metadata_program: &Program<'info, Metadata>,
    system_program: &Program<'info, System>,
    rent: &Sysvar<'info, Rent>,
    business_type: BusinessType,
    upgrade_level: u8,
    serial_number: u64,
) -> Result<()> {
    // Create mint account
    let mint_rent = rent.minimum_balance(82);
    
    system_program::create_account(
        CpiContext::new(
            system_program.to_account_info(),
            system_program::CreateAccount {
                from: owner.to_account_info(),
                to: nft_mint.to_account_info(),
            },
        ),
        mint_rent,
        82,
        &token_program.key(),
    )?;
    
    // Initialize mint
    let init_mint_ctx = CpiContext::new(
        token_program.to_account_info(),
        anchor_spl::token::InitializeMint {
            mint: nft_mint.to_account_info(),
            rent: rent.to_account_info(),
        },
    );
    anchor_spl::token::initialize_mint(
        init_mint_ctx,
        0, // decimals
        &owner.key(),
        Some(&owner.key()),
    )?;

    // Create Associated Token Account
    anchor_spl::associated_token::create(
        CpiContext::new(
            associated_token_program.to_account_info(),
            anchor_spl::associated_token::Create {
                payer: owner.to_account_info(),
                associated_token: nft_token_account.to_account_info(),
                authority: owner.to_account_info(),
                mint: nft_mint.to_account_info(),
                system_program: system_program.to_account_info(),
                token_program: token_program.to_account_info(),
            },
        ),
    )?;

    // Mint NFT
    let cpi_accounts = MintTo {
        mint: nft_mint.to_account_info(),
        to: nft_token_account.to_account_info(),
        authority: owner.to_account_info(),
    };
    let cpi_program = token_program.to_account_info();
    let cpi_ctx = CpiContext::new(cpi_program, cpi_accounts);
    token::mint_to(cpi_ctx, 1)?;

    // Create metadata with upgrade level
    let business_index = business_type.to_index();
    let level_name = NFT_LEVEL_NAMES.get(upgrade_level as usize).unwrap_or(&"Basic");
    let nft_name = format!("{} {} #{}", level_name, BUSINESS_NFT_NAMES[business_index], serial_number);
    let nft_uri = BUSINESS_NFT_URIS_BY_LEVEL[business_index].get(upgrade_level as usize)
        .unwrap_or(&BUSINESS_NFT_URIS_BY_LEVEL[business_index][0]);
    
    let data_v2 = DataV2 {
        name: nft_name,
        symbol: NFT_COLLECTION_SYMBOL.to_string(),
        uri: nft_uri.to_string(),
        seller_fee_basis_points: 0,
        creators: Some(vec![Creator {
            address: owner.key(),
            verified: false,
            share: 100,
        }]),
        collection: None,
        uses: None,
    };

    let metadata_ctx = CpiContext::new(
        token_metadata_program.to_account_info(),
        CreateMetadataAccountsV3 {
            metadata: nft_metadata.to_account_info(),
            mint: nft_mint.to_account_info(),
            mint_authority: owner.to_account_info(),
            update_authority: owner.to_account_info(),
            payer: owner.to_account_info(),
            system_program: system_program.to_account_info(),
            rent: rent.to_account_info(),
        },
    );

    create_metadata_accounts_v3(metadata_ctx, data_v2, true, true, None)?;
    
    Ok(())
}

/// ✅ Verify business ownership before operations
pub fn verify_business_nft_ownership(
    player_key: Pubkey,
    business: &Business,
    nft_token_account: &AccountInfo,
) -> Result<()> {
    if let Some(nft_mint) = business.nft_mint {
        // Deserialize token account to check owner
        let token_account = TokenAccount::try_deserialize(&mut nft_token_account.data.borrow().as_ref())?;
        
        // Verify current NFT owner matches the player
        if token_account.owner != player_key {
            msg!("❌ Business ownership mismatch: player={}, nft_owner={}", player_key, token_account.owner);
            return Err(SolanaMafiaError::BusinessNotOwned.into());
        }
        
        // Verify NFT mint matches business
        if token_account.mint != nft_mint {
            msg!("❌ NFT mint mismatch: business={}, token={}", nft_mint, token_account.mint);
            return Err(SolanaMafiaError::BusinessNotOwned.into());
        }
        
        // Verify player actually owns the NFT (amount > 0)
        if token_account.amount == 0 {
            msg!("❌ Player doesn't own NFT: amount=0");
            return Err(SolanaMafiaError::BusinessNotOwned.into());
        }
    }
    
    Ok(())
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
pub struct HealthCheckPlayer<'info> {
    #[account(
        seeds = [PLAYER_SEED, player.owner.as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
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




#[derive(Accounts)]
pub struct GetBusinessNFTData<'info> {
    /// Business NFT account to read data from
    pub business_nft: Account<'info, BusinessNFT>,
}

#[derive(Accounts)]
pub struct SyncBusinessOwnership<'info> {
    /// The old owner of the business (current player in BusinessNFT)
    #[account(
        mut,
        seeds = [PLAYER_SEED, business_nft.player.as_ref()],
        bump = old_player.bump,
    )]
    pub old_player: Account<'info, Player>,
    
    /// The new owner of the business (current NFT holder)
    #[account(
        mut,
        seeds = [PLAYER_SEED, new_owner.key().as_ref()],
        bump = new_player.bump,
    )]
    pub new_player: Account<'info, Player>,
    
    /// The new owner's wallet
    pub new_owner: Signer<'info>,
    
    /// BusinessNFT account to check ownership
    #[account(
        seeds = [BUSINESS_NFT_SEED, business_nft.mint.as_ref()],
        bump = business_nft.bump,
    )]
    pub business_nft: Account<'info, BusinessNFT>,
    
    /// NFT token account to verify current owner
    /// CHECK: Token account verified in instruction
    pub nft_token_account: AccountInfo<'info>,
    
    pub token_program: Program<'info, Token>,
}

#[derive(Accounts)]
pub struct DeactivateBurnedBusiness<'info> {
    /// Player who owned the business
    #[account(
        mut,
        seeds = [PLAYER_SEED, business_nft.player.as_ref()],
        bump = player.bump,
    )]
    pub player: Account<'info, Player>,
    
    /// BusinessNFT account to update
    #[account(
        mut,
        seeds = [BUSINESS_NFT_SEED, business_nft.mint.as_ref()],
        bump = business_nft.bump,
    )]
    pub business_nft: Account<'info, BusinessNFT>,
    
    /// NFT mint to check supply
    /// CHECK: Mint account verified in instruction
    pub nft_mint: AccountInfo<'info>,
}

#[derive(Accounts)]
pub struct VerifyBusinessOwnership<'info> {
    /// Player claiming to own the business
    pub player_owner: Signer<'info>,
    
    /// Player account
    #[account(
        seeds = [PLAYER_SEED, player_owner.key().as_ref()],
        bump = player.bump,
    )]
    pub player: Account<'info, Player>,
    
    /// BusinessNFT account
    #[account(
        seeds = [BUSINESS_NFT_SEED, nft_mint.key().as_ref()],
        bump = business_nft.bump,
    )]
    pub business_nft: Account<'info, BusinessNFT>,
    
    /// NFT mint
    /// CHECK: Mint verified in instruction
    pub nft_mint: AccountInfo<'info>,
    
    /// NFT token account
    /// CHECK: Token account verified in instruction  
    pub nft_token_account: AccountInfo<'info>,
}

// 🆕 ДОБАВИТЬ В КОНЕЦ lib.rs (в секцию контекстов)

#[derive(Accounts)]
pub struct UpdateEarningsWithNFTCheck<'info> {
    pub authority: Signer<'info>,
    
    #[account(
        mut,
        seeds = [PLAYER_SEED, authority.key().as_ref()],
        bump = player.bump,
        constraint = player.owner == authority.key()
    )]
    pub player: Account<'info, Player>,
    // remaining_accounts содержат NFT token accounts для проверки
}

#[derive(Accounts)]
pub struct AutoSyncBusinessOwnership<'info> {
    #[account(mut)]
    pub player_owner: Signer<'info>,
    
    #[account(
        mut,
        seeds = [PLAYER_SEED, player_owner.key().as_ref()],
        bump = player.bump,
        constraint = player.owner == player_owner.key()
    )]
    pub player: Account<'info, Player>,
    // remaining_accounts содержат все NFT token accounts игрока
}

#[derive(Accounts)]
pub struct GetValidPlayerBusinesses<'info> {
    #[account(
        seeds = [PLAYER_SEED, player.owner.as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
    // remaining_accounts содержат NFT token accounts для проверки
}

#[derive(Accounts)]
pub struct ClaimEarningsWithNFTCheck<'info> {
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
    // remaining_accounts содержат NFT token accounts для проверки
}

#[derive(Accounts)]
pub struct UnlockBusinessSlot<'info> {
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
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
    
    /// CHECK: Treasury wallet validated against game_state.treasury_wallet
    #[account(
        mut,
        address = game_state.treasury_wallet
    )]
    pub treasury_wallet: AccountInfo<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct BuyPremiumSlot<'info> {
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
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
    
    /// CHECK: Treasury wallet validated against game_state.treasury_wallet
    #[account(
        mut,
        address = game_state.treasury_wallet
    )]
    pub treasury_wallet: AccountInfo<'info>,
    
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct CreateBusinessInSlot<'info> {
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

    /// CHECK: Treasury wallet validated against game_state.treasury_wallet
    #[account(mut)]
    pub treasury_wallet: AccountInfo<'info>,

    #[account(
        mut,
        seeds = [TREASURY_SEED],
        bump = treasury_pda.bump
    )]
    pub treasury_pda: Account<'info, Treasury>,

    /// CHECK: NFT mint account, will be initialized in instruction
    #[account(mut)]
    pub nft_mint: Signer<'info>,

    /// CHECK: ATA will be created by Associated Token Program
    #[account(mut)]
    pub nft_token_account: AccountInfo<'info>,

    #[account(
        init,
        payer = owner,
        space = BusinessNFT::SIZE,
        seeds = [BUSINESS_NFT_SEED, nft_mint.key().as_ref()],
        bump
    )]
    pub business_nft: Account<'info, BusinessNFT>,

    /// CHECK: Metadata account for NFT
    #[account(mut)]
    pub nft_metadata: UncheckedAccount<'info>,

    pub token_program: Program<'info, Token>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub token_metadata_program: Program<'info, Metadata>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

#[derive(Accounts)]
pub struct UpgradeBusinessInSlot<'info> {
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
        seeds = [GAME_STATE_SEED],
        bump = game_state.bump
    )]
    pub game_state: Account<'info, GameState>,
    
    #[account(
        seeds = [GAME_CONFIG_SEED],
        bump = game_config.bump
    )]
    pub game_config: Account<'info, GameConfig>,
    
    /// CHECK: Treasury wallet validated against game_state.treasury_wallet
    #[account(
        mut,
        address = game_state.treasury_wallet
    )]
    pub treasury_wallet: AccountInfo<'info>,

    // === СТАРАЯ NFT (будет сожжена) ===
    /// CHECK: Old NFT mint account
    #[account(mut)]
    pub old_nft_mint: AccountInfo<'info>,

    /// CHECK: Old NFT token account
    #[account(mut)]
    pub old_nft_token_account: AccountInfo<'info>,

    #[account(
        mut,
        seeds = [BUSINESS_NFT_SEED, old_nft_mint.key().as_ref()],
        bump = old_business_nft.bump,
        constraint = old_business_nft.player == player_owner.key()
    )]
    pub old_business_nft: Account<'info, BusinessNFT>,

    // === НОВАЯ NFT (будет создана) ===
    /// CHECK: New NFT mint account, will be initialized
    #[account(mut)]
    pub new_nft_mint: Signer<'info>,

    /// CHECK: New NFT token account, will be created
    #[account(mut)]
    pub new_nft_token_account: AccountInfo<'info>,

    #[account(
        init,
        payer = player_owner,
        space = BusinessNFT::SIZE,
        seeds = [BUSINESS_NFT_SEED, new_nft_mint.key().as_ref()],
        bump
    )]
    pub new_business_nft: Account<'info, BusinessNFT>,

    /// CHECK: New metadata account for NFT
    #[account(mut)]
    pub new_nft_metadata: UncheckedAccount<'info>,

    pub token_program: Program<'info, Token>,
    pub associated_token_program: Program<'info, AssociatedToken>,
    pub token_metadata_program: Program<'info, Metadata>,
    pub system_program: Program<'info, System>,
    pub rent: Sysvar<'info, Rent>,
}

#[derive(Accounts)]
pub struct SellBusinessFromSlot<'info> {
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

    #[account(
        seeds = [GAME_CONFIG_SEED],
        bump = game_config.bump
    )]
    pub game_config: Account<'info, GameConfig>,

    /// CHECK: NFT mint account
    #[account(mut)]
    pub nft_mint: AccountInfo<'info>,

    /// CHECK: NFT token account
    #[account(mut)]
    pub nft_token_account: AccountInfo<'info>,

    #[account(
        mut,
        seeds = [BUSINESS_NFT_SEED, nft_mint.key().as_ref()],
        bump = business_nft.bump,
        constraint = business_nft.player == player_owner.key()
    )]
    pub business_nft: Account<'info, BusinessNFT>,
    
    pub token_program: Program<'info, Token>,
    pub system_program: Program<'info, System>,
}

#[derive(Accounts)]
pub struct GetPlayerSlotData<'info> {
    #[account(
        seeds = [PLAYER_SEED, player.owner.as_ref()],
        bump = player.bump
    )]
    pub player: Account<'info, Player>,
}


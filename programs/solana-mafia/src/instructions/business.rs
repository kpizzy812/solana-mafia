use anchor_lang::prelude::*;
use anchor_lang::system_program;
use anchor_spl::token::{self, Token};

use crate::state::*;
use crate::constants::*;
use crate::error::SolanaMafiaError;
use crate::create_business_nft;
use crate::{CreateBusinessInSlot, UpgradeBusinessInSlot, SellBusinessFromSlot};

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

    emit!(crate::BusinessNFTMinted {
        player: ctx.accounts.owner.key(),
        business_type,
        mint: ctx.accounts.nft_mint.key(),
        serial_number,
        invested_amount: deposit_amount,
        daily_rate,
        created_at: clock.unix_timestamp,
    });

    emit!(crate::BusinessCreatedInSlot {
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
    emit!(crate::BusinessNFTBurned {
        player: ctx.accounts.player_owner.key(),
        mint: ctx.accounts.old_nft_mint.key(),
        business_type: current_business.business_type.to_index() as u8,
        serial_number: old_business_nft.serial_number,
        burned_at: clock.unix_timestamp,
    });
    
    emit!(crate::BusinessNFTMinted {
        player: ctx.accounts.player_owner.key(),
        business_type: current_business.business_type.to_index() as u8,
        mint: ctx.accounts.new_nft_mint.key(),
        serial_number: new_business_nft.serial_number,
        invested_amount: new_invested_amount,
        daily_rate: new_daily_rate,
        created_at: clock.unix_timestamp,
    });
    
    emit!(crate::BusinessUpgradedInSlot {
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
    emit!(crate::BusinessNFTBurned {
        player: ctx.accounts.player_owner.key(),
        mint: ctx.accounts.nft_mint.key(),
        business_type: business.business_type.to_index() as u8,
        serial_number: business_nft.serial_number,
        burned_at: clock.unix_timestamp,
    });
    
    emit!(crate::BusinessSoldFromSlot {
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
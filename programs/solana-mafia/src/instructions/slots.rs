use anchor_lang::prelude::*;
use anchor_lang::system_program;

use crate::state::*;
use crate::constants::*;
use crate::error::SolanaMafiaError;
use crate::{UnlockBusinessSlot, BuyPremiumSlot};

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
    
    emit!(crate::SlotUnlocked {
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
    
    emit!(crate::PremiumSlotPurchased {
        player: ctx.accounts.player_owner.key(),
        slot_type,
        slot_index: slot_index as u8,
        cost: slot_cost,
        purchased_at: clock.unix_timestamp,
    });
    
    msg!("💎 Premium slot {:?} purchased for {} lamports", slot_type, slot_cost);
    Ok(())
}
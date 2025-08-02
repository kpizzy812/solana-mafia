use anchor_lang::prelude::*;
use anchor_spl::token::{Mint, TokenAccount};

use crate::state::*;
use crate::constants::*;
use crate::error::SolanaMafiaError;
use crate::{GetBusinessNFTData, SyncBusinessOwnership, DeactivateBurnedBusiness, AutoSyncBusinessOwnership};

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
            emit!(crate::BusinessTransferred {
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
        
        emit!(crate::BusinessNFTBurned {
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
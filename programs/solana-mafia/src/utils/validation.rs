use anchor_lang::prelude::*;
use anchor_spl::token::TokenAccount;
use crate::constants::*;
use crate::error::*;
use crate::state::Business;

/// Validate business type index
pub fn validate_business_type(business_type: u8) -> Result<()> {
    if business_type as usize >= BUSINESS_TYPES_COUNT {
        return Err(SolanaMafiaError::InvalidBusinessType.into());
    }
    Ok(())
}

/// Validate deposit amount against minimum
pub fn validate_deposit_amount(deposit_amount: u64, min_deposit: u64) -> Result<()> {
    if deposit_amount < min_deposit {
        return Err(SolanaMafiaError::InsufficientDeposit.into());
    }
    Ok(())
}

/// Validate upgrade level
pub fn validate_upgrade_level(level: u8) -> Result<()> {
    if level == 0 || level > MAX_UPGRADE_LEVEL {
        return Err(SolanaMafiaError::InvalidUpgradeLevel.into());
    }
    Ok(())
}

/// Проверяет владение NFT и возвращает индексы валидных бизнесов
pub fn verify_and_filter_owned_businesses(
    remaining_accounts: &[AccountInfo],
    businesses: &[Business],
    expected_owner: Pubkey,
) -> Result<Vec<usize>> {
    let mut valid_business_indices = Vec::new();
    let mut nft_account_index = 0;
    
    for (business_index, business) in businesses.iter().enumerate() {
        if !business.is_active {
            continue; // Пропускаем неактивные
        }
        
        if let Some(_nft_mint) = business.nft_mint {
            // NFT бизнес - проверяем владение
            if nft_account_index < remaining_accounts.len() {
                let token_account_info = &remaining_accounts[nft_account_index];
                
                match TokenAccount::try_deserialize(&mut token_account_info.data.borrow().as_ref()) {
                    Ok(token_account) => {
                        if token_account.owner == expected_owner && token_account.amount > 0 {
                            valid_business_indices.push(business_index);
                        }
                    }
                    Err(_) => {
                        // Не валидный token account - пропускаем
                        msg!("⚠️ Invalid token account for business {}", business_index);
                    }
                }
                nft_account_index += 1;
            }
        } else {
            // Обычный бизнес - всегда валиден  
            valid_business_indices.push(business_index);
        }
    }
    
    Ok(valid_business_indices)
}

/// 🔄 Автоматическая синхронизация ownership бизнесов
pub fn auto_sync_business_ownership(ctx: Context<AutoSyncBusinessOwnership>) -> Result<()> {
    let player = &mut ctx.accounts.player;
    let ownership_status = verify_all_nft_ownership(
        &ctx.remaining_accounts, 
        &player.businesses, 
        ctx.accounts.player_owner.key()
    )?;
    
    let mut businesses_deactivated = 0u8;
    
    // Деактивируем бизнесы, NFT которых больше не принадлежат игроку
    for (index, owns_nft) in ownership_status.iter().enumerate() {
        if let Some(business) = player.businesses.get_mut(index) {
            if business.is_active && business.nft_mint.is_some() && !owns_nft {
                business.is_active = false;
                businesses_deactivated += 1;
                
                msg!("🔄 Deactivated business {} - NFT no longer owned", index);
                
                emit!(BusinessDeactivated {
                    player: ctx.accounts.player_owner.key(),
                    business_mint: business.nft_mint.unwrap(),
                    reason: "nft_transferred".to_string(),
                    deactivated_at: Clock::get()?.unix_timestamp,
                });
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
    let valid_indices = verify_and_filter_owned_businesses(
        &ctx.remaining_accounts, 
        &player.businesses, 
        player.owner
    )?;
    
    msg!("VALID_BUSINESSES: player={}, total={}, valid={}, indices={:?}", 
         player.owner, 
         player.businesses.len(), 
         valid_indices.len(),
         valid_indices
    );
    
    // Логируем детали каждого валидного бизнеса
    for &index in &valid_indices {
        if let Some(business) = player.businesses.get(index) {
            msg!("BUSINESS_{}: type={}, invested={}, active={}, has_nft={}", 
                 index,
                 business.business_type.to_index(),
                 business.invested_amount,
                 business.is_active,
                 business.nft_mint.is_some()
            );
        }
    }
    
    Ok(())
}

/// Проверяет владение NFT для всех бизнесов
pub fn verify_all_nft_ownership(
    remaining_accounts: &[AccountInfo],
    businesses: &[Business],
    expected_owner: Pubkey,
) -> Result<Vec<bool>> {
    let mut ownership_status = Vec::new();
    let mut account_index = 0;
    
    for business in businesses {
        if business.is_active && business.nft_mint.is_some() {
            if account_index < remaining_accounts.len() {
                let token_account_info = &remaining_accounts[account_index];
                
                match TokenAccount::try_deserialize(&mut token_account_info.data.borrow().as_ref()) {
                    Ok(token_account) => {
                        let owns_nft = token_account.owner == expected_owner && token_account.amount > 0;
                        ownership_status.push(owns_nft);
                        
                        if !owns_nft {
                            msg!("⚠️ NFT ownership lost for business with mint: {}", business.nft_mint.unwrap());
                        }
                    }
                    Err(_) => {
                        ownership_status.push(false);
                        msg!("❌ Failed to deserialize token account");
                    }
                }
                account_index += 1;
            } else {
                ownership_status.push(false);
                msg!("❌ Missing token account for NFT business");
            }
        } else {
            ownership_status.push(true); // Non-NFT businesses are always "owned"
        }
    }
    
    Ok(ownership_status)
}

/// Безопасная проверка владения одним NFT
pub fn verify_single_nft_ownership(
    token_account_info: &AccountInfo,
    expected_owner: Pubkey,
    expected_mint: Pubkey,
) -> Result<bool> {
    match TokenAccount::try_deserialize(&mut token_account_info.data.borrow().as_ref()) {
        Ok(token_account) => {
            Ok(token_account.owner == expected_owner 
               && token_account.mint == expected_mint 
               && token_account.amount > 0)
        }
        Err(_) => {
            msg!("❌ Failed to deserialize token account");
            Ok(false)
        }
    }
}
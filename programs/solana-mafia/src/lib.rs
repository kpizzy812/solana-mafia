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
pub mod instructions;
pub mod state; 

use state::*;
use constants::*;
use error::SolanaMafiaError;
use instructions::*;

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
        instructions::admin::initialize(ctx, treasury_wallet)
    }

    /// Create new player (with entry fee)
    pub fn create_player(ctx: Context<CreatePlayer>, referrer: Option<Pubkey>) -> Result<()> {
        instructions::player::create_player(ctx, referrer)
    }

    /// 🏪 Create business in specific slot with NFT
    pub fn create_business(
        ctx: Context<CreateBusinessInSlot>,
        business_type: u8,
        deposit_amount: u64,
        slot_index: u8,
    ) -> Result<()> {
        instructions::business::create_business(ctx, business_type, deposit_amount, slot_index)
    }

    /// Update earnings (owner only)
    pub fn update_earnings(ctx: Context<UpdateEarningsWithNFTCheck>) -> Result<()> {
        instructions::earnings::update_earnings(ctx)
    }

    /// Claim earnings with slot-based system
    pub fn claim_earnings(ctx: Context<ClaimEarningsWithNFTCheck>) -> Result<()> {
        instructions::earnings::claim_earnings(ctx)
    }

    /// Health check for player data
    pub fn health_check_player(ctx: Context<HealthCheckPlayer>) -> Result<()> {
        instructions::player::health_check_player(ctx)
    }

    /// 🔥 Sell business from slot (with early exit fees and NFT burn)
    pub fn sell_business(
        ctx: Context<SellBusinessFromSlot>,
        slot_index: u8,
    ) -> Result<()> {
        instructions::business::sell_business(ctx, slot_index)
    }

    /// Add referral bonus 
    pub fn add_referral_bonus(
        ctx: Context<AddReferralBonus>, 
        amount: u64,
        referred_player: Pubkey,
        level: u8
    ) -> Result<()> {
        instructions::admin::add_referral_bonus(ctx, amount, referred_player, level)
    }

    /// 🆕 Обновление earnings для одного игрока (для backend batch processing)
    pub fn update_single_player_earnings(ctx: Context<UpdateSinglePlayerEarnings>) -> Result<()> {
        instructions::admin::update_single_player_earnings(ctx)
    }

    /// 🆕 Проверить нужно ли обновление earnings игроку
    pub fn check_earnings_due(ctx: Context<CheckEarningsDue>) -> Result<()> {
        instructions::earnings::check_earnings_due(ctx)
    }

    /// 🆕 Получить список всех игроков с их статусом обновления (view функция)
    pub fn batch_check_players_status(ctx: Context<BatchCheckPlayersStatus>) -> Result<()> {
        instructions::admin::batch_check_players_status(ctx)
    }

    /// 🆕 Получить данные игрока для фронтенда (с новой системой слотов)
    pub fn get_player_data(ctx: Context<GetPlayerData>) -> Result<()> {
        instructions::player::get_player_data(ctx)
    }

    /// 🆕 Получить глобальную статистику
    pub fn get_global_stats(ctx: Context<GetGlobalStats>) -> Result<()> {
        instructions::earnings::get_global_stats(ctx)
    }



    /// 🆕 Get NFT metadata for frontend
    pub fn get_business_nft_data(ctx: Context<GetBusinessNFTData>) -> Result<()> {
        instructions::nft::get_business_nft_data(ctx)
    }


    /// 🔄 Sync business ownership based on NFT ownership
    pub fn sync_business_ownership(ctx: Context<SyncBusinessOwnership>) -> Result<()> {
        instructions::nft::sync_business_ownership(ctx)
    }

    /// 🔥 Deactivate business if NFT was burned externally
    pub fn deactivate_burned_business(ctx: Context<DeactivateBurnedBusiness>) -> Result<()> {
        instructions::nft::deactivate_burned_business(ctx)
    }

    /// 🔄 Автоматическая синхронизация ownership бизнесов (для слотов)
    pub fn auto_sync_business_ownership(ctx: Context<AutoSyncBusinessOwnership>) -> Result<()> {
        instructions::nft::auto_sync_business_ownership(ctx)
    }

    /// 🆕 Получить только валидные (принадлежащие) бизнесы игрока
    pub fn get_valid_player_businesses(ctx: Context<GetValidPlayerBusinesses>) -> Result<()> {
        instructions::player::get_valid_player_businesses(ctx)
    }

    /// 🔓 Unlock business slot
    pub fn unlock_business_slot(ctx: Context<UnlockBusinessSlot>) -> Result<()> {
        instructions::slots::unlock_business_slot(ctx)
    }

    /// 💎 Buy premium slot
    pub fn buy_premium_slot(
        ctx: Context<BuyPremiumSlot>,
        slot_type: SlotType,
    ) -> Result<()> {
        instructions::slots::buy_premium_slot(ctx, slot_type)
    }

    /// ⬆️ Upgrade business in slot (burns old NFT, creates new one)
    pub fn upgrade_business(
        ctx: Context<UpgradeBusinessInSlot>,
        slot_index: u8,
    ) -> Result<()> {
        instructions::business::upgrade_business(ctx, slot_index)
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
    let level_name = business_type.get_upgrade_name(upgrade_level);
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


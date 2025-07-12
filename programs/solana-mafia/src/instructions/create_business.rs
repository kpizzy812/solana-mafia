// instructions/create_business.rs
use anchor_lang::prelude::*;
use anchor_lang::system_program;
use crate::constants::*;
use crate::state::*;
use crate::error::*;

pub fn handler(
    ctx: Context<CreateBusiness>,
    business_type: u8,
    deposit_amount: u64,
    referrer: Option<Pubkey>,
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

    // Validate referrer (cannot refer yourself)
    if let Some(ref_key) = referrer {
        if ref_key == ctx.accounts.owner.key() {
            return Err(SolanaMafiaError::CannotReferYourself.into());
        }
    }

    // Initialize player if this is a new account
    let player = &mut ctx.accounts.player;
    let is_new_player = player.owner == Pubkey::default();
    let mut total_fees = 0u64;
    
    if is_new_player {
        // New player - require entry fee ($10)
        let entry_fee = game_config.entry_fee;
        
        // Transfer entry fee to treasury
        system_program::transfer(
            CpiContext::new(
                ctx.accounts.system_program.to_account_info(),
                system_program::Transfer {
                    from: ctx.accounts.owner.to_account_info(),
                    to: ctx.accounts.treasury.to_account_info(),
                },
            ),
            entry_fee,
        )?;
        
        total_fees += entry_fee;

        // Initialize player
        player.owner = ctx.accounts.owner.key();
        player.referrer = referrer;
        player.has_paid_entry = true;
        player.total_invested = 0;
        player.total_claimed = 0;
        player.referral_earnings = 0;
        player.businesses = Vec::new();
        player.created_at = clock.unix_timestamp;
        player.last_claim = clock.unix_timestamp;
        player.bump = ctx.bumps.player;
        
        // Update game stats for new player
        game_state.add_player();
        game_state.add_treasury_collection(entry_fee);
        
        msg!("New player registered! Entry fee: {} lamports", entry_fee);
    }

    // Validate player can create more businesses
    if !player.can_create_business() {
        return Err(SolanaMafiaError::MaxBusinessesReached.into());
    }

    // Calculate treasury fee (20% of deposit goes to team)
    let treasury_fee = (deposit_amount * game_config.treasury_fee_percent as u64) / 100;
    total_fees += treasury_fee;
    
    // Transfer treasury fee to treasury wallet
    system_program::transfer(
        CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.owner.to_account_info(),
                to: ctx.accounts.treasury.to_account_info(),
            },
        ),
        treasury_fee,
    )?;

    // Process referral bonus (5% of deposit to level 1 referrer)
    let mut referral_paid = 0u64;
    if let Some(referrer_key) = player.referrer {
        if let Some(ref mut referrer_account) = ctx.accounts.referrer_player {
            let bonus = (deposit_amount * REFERRAL_RATES[0] as u64) / 100; // 5%
            
            // Начисляем бонус рефереру на баланс
            referrer_account.referral_earnings += bonus;
            referral_paid = bonus;
            
            // Обновляем статистику
            game_state.add_referral_payment(bonus);
            
            msg!("Referral bonus: {} lamports paid to {}", bonus, referrer_key);
        }
    }

    // Create business
    let business = Business::new(
        business_enum.clone(),
        deposit_amount,
        daily_rate,
        clock.unix_timestamp,
    );

    // Add business to player
    player.add_business(business)?;
    player.total_invested += deposit_amount;

    // Update game statistics
    game_state.add_investment(deposit_amount);
    game_state.add_treasury_collection(treasury_fee);
    game_state.add_business();

    msg!("Business created successfully!");
    msg!("Type: {:?}", business_enum);
    msg!("Investment: {} lamports", deposit_amount);
    msg!("Daily rate: {} basis points", daily_rate);
    msg!("Entry fee: {} lamports", if is_new_player { game_config.entry_fee } else { 0 });
    msg!("Treasury fee: {} lamports", treasury_fee);
    msg!("Referral bonus: {} lamports", referral_paid);
    msg!("Game pool: {} lamports", deposit_amount - treasury_fee - referral_paid);

    Ok(())
}

#[derive(Accounts)]
#[instruction(business_type: u8, deposit_amount: u64, referrer: Option<Pubkey>)]
pub struct CreateBusiness<'info> {
    /// Player who is creating the business
    #[account(mut)]
    pub owner: Signer<'info>,

    /// Player account (created if doesn't exist)
    #[account(
        init_if_needed,
        payer = owner,
        space = Player::MAX_SIZE,
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

    /// Treasury wallet where fees go
    /// CHECK: This is validated against game_state.treasury_wallet
    #[account(
        mut,
        address = game_state.treasury_wallet
    )]
    pub treasury: AccountInfo<'info>,

    /// Referrer player account (optional - only if referrer is provided)
    #[account(
        mut,
        seeds = [PLAYER_SEED, referrer.unwrap_or_default().as_ref()],
        bump,
        // Только проверяем если referrer передан
    )]
    pub referrer_player: Option<Account<'info, Player>>,

    /// System program
    pub system_program: Program<'info, System>,
}
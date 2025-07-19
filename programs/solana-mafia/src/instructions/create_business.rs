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
    let entry_fee = game_config.entry_fee;
    let mut total_payment = deposit_amount;
    
    // Check if this is a new player (first business)
    let is_new_player = player.businesses.is_empty();
    
    if is_new_player {
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
        
        // Add entry fee to total payment
        total_payment += entry_fee;
        
        // Update game stats for new player
        game_state.add_player();
        
        msg!("New player registered with entry fee: {} lamports", entry_fee);
    }

    // Validate player can create more businesses
    if !player.can_create_business() {
        return Err(SolanaMafiaError::MaxBusinessesReached.into());
    }

    // Calculate treasury fee (20% of deposit goes to team)
    let treasury_fee = (deposit_amount * game_config.treasury_fee_percent as u64) / 100;
    let total_treasury = if is_new_player { entry_fee + treasury_fee } else { treasury_fee };
    
    // Transfer treasury amount to treasury wallet (team)
    system_program::transfer(
        CpiContext::new(
            ctx.accounts.system_program.to_account_info(),
            system_program::Transfer {
                from: ctx.accounts.owner.to_account_info(),
                to: ctx.accounts.treasury_wallet.to_account_info(),
            },
        ),
        total_treasury,
    )?;

    // Transfer game pool portion to treasury PDA (80% of deposit)
    let game_pool_amount = deposit_amount - treasury_fee;
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
    let business = Business::new(
        business_enum,
        deposit_amount,
        daily_rate,
        clock.unix_timestamp,
    );

    // Add business to player
    player.add_business(business)?;
    player.total_invested += deposit_amount;

    // Update game statistics
    game_state.add_investment(deposit_amount);
    game_state.add_treasury_collection(total_treasury);
    game_state.add_business();

    msg!("Business created successfully!");
    msg!("Type: {:?}", business_enum);
    msg!("Investment: {} lamports", deposit_amount);
    msg!("Daily rate: {} basis points", daily_rate);
    if is_new_player {
        msg!("Entry fee: {} lamports", entry_fee);
    }
    msg!("Treasury fee: {} lamports", treasury_fee);
    msg!("Game pool: {} lamports", game_pool_amount);
    msg!("Total businesses: {}", player.businesses.len());

    Ok(())
}

#[derive(Accounts)]
#[instruction(business_type: u8, deposit_amount: u64)]
pub struct CreateBusiness<'info> {
    /// Player who is creating the business
    #[account(mut)]
    pub owner: Signer<'info>,

    /// Player account (init_if_needed for new players)
    #[account(
        init_if_needed,
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
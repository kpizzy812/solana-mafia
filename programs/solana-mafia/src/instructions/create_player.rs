// instructions/create_player.rs
use anchor_lang::prelude::*;
use anchor_lang::system_program;
use crate::constants::*;
use crate::state::*;
use crate::error::*;

/// 🔒 Создание нового игрока (отдельно от create_business)
pub fn handler(ctx: Context<CreatePlayer>) -> Result<()> {
    let clock = Clock::get()?;
    let game_config = &ctx.accounts.game_config;
    let game_state = &mut ctx.accounts.game_state;
    let player = &mut ctx.accounts.player;
    
    // Validate game is not paused
    if game_state.is_paused {
        return Err(SolanaMafiaError::GamePaused.into());
    }
    
    // 🔒 БЕЗОПАСНОСТЬ: Проверяем что treasury_wallet соответствует game_state
    if ctx.accounts.treasury_wallet.key() != game_state.treasury_wallet {
        return Err(SolanaMafiaError::UnauthorizedAdmin.into());
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

#[derive(Accounts)]
pub struct CreatePlayer<'info> {
    /// Player creating account
    #[account(mut)]
    pub owner: Signer<'info>,

    /// Player account
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
    #[account(mut)]
    pub treasury_wallet: AccountInfo<'info>,

    /// System program
    pub system_program: Program<'info, System>,
}
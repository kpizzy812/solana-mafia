use anchor_lang::prelude::*;

// Import modules
pub mod constants;
pub mod error;
pub mod state;
pub mod instructions;

// Re-export for convenience
pub use constants::*;
pub use error::*;
pub use state::*;
pub use instructions::*;

declare_id!("93zp2Qtgaiud9NTG1fYb4qqDddSi98AAx9Px7Gyv3CnM");

#[program]
pub mod solana_mafia {
    use super::*;

    /// Initialize the game with config and state
    pub fn initialize(ctx: Context<Initialize>, treasury_wallet: Pubkey) -> Result<()> {
        instructions::initialize::handler(ctx, treasury_wallet)
    }
}
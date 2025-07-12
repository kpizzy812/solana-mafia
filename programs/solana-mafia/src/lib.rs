use anchor_lang::prelude::*;

// Import modules
pub mod constants;
pub mod error;

// Re-export for convenience
pub use constants::*;
pub use error::*;

declare_id!("93zp2Qtgaiud9NTG1fYb4qqDddSi98AAx9Px7Gyv3CnM");

#[program]
pub mod solana_mafia {
    use super::*;

    /// Initialize the game - basic version for testing
    pub fn initialize(ctx: Context<Initialize>) -> Result<()> {
        msg!("Greetings from Solana Mafia: {:?}", ctx.program_id);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct Initialize {}
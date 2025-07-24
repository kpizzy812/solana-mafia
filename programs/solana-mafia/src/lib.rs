use anchor_lang::prelude::*;

pub mod constants;
pub mod error;
pub mod state;
pub mod utils;

use state::*;

declare_id!("Hnyyopg1fsQGY1JqEsp8CPZk1KjDKsAoosBJJi5ZpegU");

#[program]
pub mod solana_mafia {
    use super::*;

    pub fn test_function(ctx: Context<TestAccounts>) -> Result<()> {
        msg!("Test function called - all modules loaded successfully!");
        msg!("Entry fee: {}", constants::ENTRY_FEE);
        Ok(())
    }
}

#[derive(Accounts)]
pub struct TestAccounts<'info> {
    #[account(mut)]
    pub signer: Signer<'info>,
    pub system_program: Program<'info, System>,
}
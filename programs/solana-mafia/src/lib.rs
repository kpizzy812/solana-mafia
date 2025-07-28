use anchor_lang::prelude::*;

// Нужны для initialize.rs!
pub mod constants;
pub mod error;      
pub mod instructions; 
pub mod state;
pub mod utils;

use instructions::{
    initialize_handler,
    Initialize,
};

declare_id!("Hnyyopg1fsQGY1JqEsp8CPZk1KjDKsAoosBJJi5ZpegU");

#[program]
pub mod solana_mafia {
    use super::*;

    pub fn initialize(ctx: Context<Initialize>, treasury_wallet: Pubkey) -> Result<()> {
        initialize_handler(ctx, treasury_wallet)
    }
}
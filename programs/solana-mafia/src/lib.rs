// Импортируем handlers из instructions (ТОЛЬКО initialize)
use instructions::{
    initialize_handler,
};

// Импортируем контексты из instructions (ТОЛЬКО initialize)
use instructions::{
    Initialize,
};

#[program]
pub mod solana_mafia {
    use super::*;

    /// Initialize the game with treasury wallet
    pub fn initialize(ctx: Context<Initialize>, treasury_wallet: Pubkey) -> Result<()> {
        initialize_handler(ctx, treasury_wallet)
    }
}
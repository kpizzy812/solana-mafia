pub mod business;
pub mod game_config;
pub mod game_state;  
pub mod player;

pub use business::*;
pub use game_config::*;
pub use game_state::*;
pub use player::*;

use anchor_lang::prelude::*;

/// Treasury PDA для хранения средств
#[account]
pub struct Treasury {
    pub bump: u8,
}

impl Treasury {
    pub const SIZE: usize = 8 + 1; // discriminator + bump
}
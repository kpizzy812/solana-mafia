use anchor_lang::prelude::*;

#[account]
pub struct Treasury {
    pub bump: u8,
}

impl Treasury {
    pub const SIZE: usize = 8 + 1; // discriminator + bump
}
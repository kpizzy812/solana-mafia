use anchor_lang::prelude::*;
use crate::state::business::BusinessType;

/// NFT metadata для бизнеса
#[account]
pub struct BusinessNFT {
    pub player: Pubkey,           // Владелец NFT
    pub business_type: BusinessType, // Тип бизнеса
    pub mint: Pubkey,             // NFT mint address
    pub token_account: Pubkey,    // Token account владельца
    pub total_invested_amount: u64, // 🆕 Общая сумма инвестиций (база + улучшения)
    pub daily_rate: u16,          // Дневная ставка
    pub upgrade_level: u8,        // Уровень апгрейда
    pub created_at: i64,          // Время создания
    pub serial_number: u64,       // Серийный номер NFT
    pub is_burned: bool,          // Сожжен ли NFT
    pub bump: u8,                 // PDA bump
}

impl BusinessNFT {
    pub const SIZE: usize = 8 + // discriminator
        32 + // player
        1 +  // business_type
        32 + // mint
        32 + // token_account
        8 +  // total_invested_amount
        2 +  // daily_rate
        1 +  // upgrade_level
        8 +  // created_at
        8 +  // serial_number
        1 +  // is_burned
        1;   // bump

    pub fn new(
        player: Pubkey,
        business_type: BusinessType,
        mint: Pubkey,
        token_account: Pubkey,
        total_invested_amount: u64,
        daily_rate: u16,
        created_at: i64,
        serial_number: u64,
        bump: u8,
    ) -> Self {
        Self {
            player,
            business_type,
            mint,
            token_account,
            total_invested_amount,
            daily_rate,
            upgrade_level: 0,
            created_at,
            serial_number,
            is_burned: false,
            bump,
        }
    }

    /// Update upgrade level
    pub fn upgrade(&mut self, new_level: u8, new_daily_rate: u16) {
        self.upgrade_level = new_level;
        self.daily_rate = new_daily_rate;
    }

    /// Mark as burned
    pub fn burn(&mut self) {
        self.is_burned = true;
    }
}
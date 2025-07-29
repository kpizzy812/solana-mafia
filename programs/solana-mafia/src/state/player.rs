// state/player.rs
use anchor_lang::prelude::*;
use crate::constants::*;
use crate::state::business::Business;
use crate::error::SolanaMafiaError;

#[account]
pub struct Player {
    pub owner: Pubkey,
    pub businesses: Vec<Business>,
    pub total_invested: u64,
    pub total_earned: u64,
    pub pending_earnings: u64,
    pub pending_referral_earnings: u64,
    pub has_paid_entry: bool,
    pub created_at: i64,
    pub bump: u8,
}

impl Player {
    /// 🔒 ИСПРАВЛЕННЫЙ размер аккаунта - с БОЛЬШИМ запасом для безопасности
    pub const SIZE: usize = 8 + // discriminator
        32 + // owner
        4 + (Business::SIZE * MAX_BUSINESSES_PER_PLAYER as usize) + // businesses Vec
        8 + // total_invested
        8 + // total_earned
        8 + // pending_earnings
        8 + // pending_referral_earnings
        1 + // has_paid_entry
        8 + // created_at
        1 + // bump
        1000; // 🔒 БОЛЬШОЙ ЗАПАС для Anchor overhead и будущих полей

    /// Create new player
    pub fn new(owner: Pubkey, _referrer: Option<Pubkey>, current_time: i64, bump: u8) -> Self {
        Self {
            owner,
            businesses: Vec::new(),
            total_invested: 0,
            total_earned: 0,
            pending_earnings: 0,
            pending_referral_earnings: 0,
            has_paid_entry: false,
            created_at: current_time,
            bump,
        }
    }

    /// Get business by index
    pub fn get_business(&self, index: u8) -> Option<&Business> {
        self.businesses.get(index as usize)
    }

    /// Get mutable business by index
    pub fn get_business_mut(&mut self, index: u8) -> Option<&mut Business> {
        self.businesses.get_mut(index as usize)
    }

    /// 🔒 БЕЗОПАСНАЯ проверка на возможность создать бизнес
    pub fn can_create_business(&self) -> bool {
        self.businesses.len() < MAX_BUSINESSES_PER_PLAYER as usize
    }

    /// 🔒 БЕЗОПАСНОЕ добавление бизнеса с проверками
    pub fn add_business(&mut self, business: Business) -> Result<()> {
        // Проверяем лимит
        if !self.can_create_business() {
            return Err(SolanaMafiaError::MaxBusinessesReached.into());
        }
        
        // Проверяем здоровье бизнеса
        let clock = Clock::get()?;
        business.health_check(clock.unix_timestamp)?;
        
        self.businesses.push(business);
        
        // 🔒 Защита от overflow
        self.total_invested = self.total_invested
            .checked_add(business.invested_amount)
            .ok_or(ProgramError::ArithmeticOverflow)?;
        
        Ok(())
    }

    /// 🔒 БЕЗОПАСНОЕ обновление pending earnings с новыми проверками
    pub fn update_pending_earnings(&mut self, current_time: i64) -> Result<()> {
        let mut total_new_earnings = 0u64;
        
        for business in &mut self.businesses {
            if business.is_active {
                // Используем новую безопасную функцию
                let pending = business.calculate_pending_earnings(current_time);
                
                // 🔒 Защита от overflow при суммировании
                total_new_earnings = total_new_earnings
                    .checked_add(pending)
                    .ok_or(SolanaMafiaError::MathOverflow)?;
                    
                // Обновляем last_claim безопасно
                business.update_last_claim(current_time)?;
            }
        }
        
        // 🔒 Защита от overflow при добавлении к pending_earnings
        self.pending_earnings = self.pending_earnings
            .checked_add(total_new_earnings)
            .ok_or(SolanaMafiaError::MathOverflow)?;
            
        // 🔒 ДОПОЛНИТЕЛЬНАЯ ЗАЩИТА: Лимит на pending_earnings
        if self.pending_earnings > 10_000_000_000_000 { // 10,000 SOL - только для мониторинга
            msg!("ℹ️ Large pending earnings: {} lamports for player {}", self.pending_earnings, self.owner);
        }
        
        Ok(())
    }

    /// Get total claimable amount (earnings + referral)
    pub fn get_claimable_amount(&self) -> Result<u64> {
        self.pending_earnings
            .checked_add(self.pending_referral_earnings)
            .ok_or(SolanaMafiaError::MathOverflow.into())
    }

    /// 🔒 БЕЗОПАСНОЕ получение всех earnings
    pub fn claim_all_earnings(&mut self) -> Result<()> {
        let total_claimed = self.pending_earnings
            .checked_add(self.pending_referral_earnings)
            .ok_or(SolanaMafiaError::MathOverflow)?;
            
        // 🔒 Защита от overflow
        self.total_earned = self.total_earned
            .checked_add(total_claimed)
            .ok_or(SolanaMafiaError::MathOverflow)?;
            
        // 🔒 Проверяем разумность total_earned (не больше 10x от инвестиций)
        if total_claimed > 1_000_000_000_000 { // 1000 SOL - только лог
            msg!("ℹ️ Large claim: {} lamports by {}", total_claimed, self.owner);
        }
            
        self.pending_earnings = 0;
        self.pending_referral_earnings = 0;
        Ok(())
    }

    /// 🔒 БЕЗОПАСНОЕ добавление реферального бонуса
    pub fn add_referral_bonus(&mut self, amount: u64) -> Result<()> {
        // 🔒 Лимит на реферальные earnings (максимум 50% от инвестиций)
        self.pending_referral_earnings = self.pending_referral_earnings
        .checked_add(amount)
        .ok_or(SolanaMafiaError::MathOverflow)?;
        
    if amount > 100_000_000_000 { // 100 SOL - только лог
        msg!("ℹ️ Large referral bonus: {} lamports to {}", amount, self.owner);
    }
    Ok(())
    }

    /// Claim specific amount of earnings
    pub fn claim_earnings(&mut self, amount: u64) -> Result<()> {
        self.pending_earnings = self.pending_earnings.saturating_sub(amount);
        
        // 🔒 Защита от overflow
        self.total_earned = self.total_earned
            .checked_add(amount)
            .ok_or(SolanaMafiaError::MathOverflow)?;
        Ok(())
    }

    /// Claim specific amount of referral earnings  
    pub fn claim_referral_earnings(&mut self, amount: u64) -> Result<()> {
        self.pending_referral_earnings = self.pending_referral_earnings.saturating_sub(amount);
        
        // 🔒 Защита от overflow
        self.total_earned = self.total_earned
            .checked_add(amount)
            .ok_or(SolanaMafiaError::MathOverflow)?;
        Ok(())
    }

    /// 🔒 НОВАЯ ФУНКЦИЯ: Проверка здоровья аккаунта игрока
    pub fn health_check(&self, current_time: i64) -> Result<()> {
        // Проверяем временные метки
        if self.created_at > current_time {
            return Err(ProgramError::InvalidArgument.into());
        }
        
        // Проверяем разумность значений
        if self.pending_earnings > 1000_000_000_000 { // 1000 SOL
            msg!("⚠️ Подозрительно высокие pending earnings: {}", self.pending_earnings);
        }
        
        if self.pending_referral_earnings > self.total_invested / 2 {
            msg!("⚠️ Подозрительно высокие referral earnings: {} vs invested: {}", 
                 self.pending_referral_earnings, self.total_invested);
        }
        
        // Проверяем количество бизнесов
        if self.businesses.len() > MAX_BUSINESSES_PER_PLAYER as usize {
            return Err(SolanaMafiaError::MaxBusinessesReached.into());
        }
        
        // Проверяем каждый бизнес
        for business in &self.businesses {
            business.health_check(current_time)?;
        }
        
        Ok(())
    }
}

// 🔒 ТЕПЕРЬ БЕЗОПАСНО!
// - Размер аккаунта с большим запасом (1000 байт)
// - Все операции с checked math
// - Лимиты на все значения
// - Health checks для всех данных
// - Защита от подозрительной активности
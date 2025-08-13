// state/business.rs - ОБНОВЛЕНО ДЛЯ СИСТЕМЫ УЛУЧШЕНИЙ
use anchor_lang::prelude::*;
use crate::constants::*;

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Debug)]
pub enum BusinessType {
    TobaccoShop = 0,       // 0.1 SOL базовая
    FuneralService = 1,    // 0.5 SOL базовая
    CarWorkshop = 2,       // 2 SOL базовая
    ItalianRestaurant = 3, // 0.1 SOL (можно в любой слот)
    GentlemenClub = 4,     // 0.5 SOL
    CharityFund = 5,       // 2 SOL
}

impl BusinessType {
    pub fn to_index(&self) -> usize {
        match self {
            BusinessType::TobaccoShop => 0,
            BusinessType::FuneralService => 1,
            BusinessType::CarWorkshop => 2,
            BusinessType::ItalianRestaurant => 3,
            BusinessType::GentlemenClub => 4,
            BusinessType::CharityFund => 5,
        }
    }

    pub fn from_index(index: u8) -> Option<Self> {
        match index {
            0 => Some(BusinessType::TobaccoShop),
            1 => Some(BusinessType::FuneralService),
            2 => Some(BusinessType::CarWorkshop),
            3 => Some(BusinessType::ItalianRestaurant),
            4 => Some(BusinessType::GentlemenClub),
            5 => Some(BusinessType::CharityFund),
            _ => None,
        }
    }

    /// 🆕 Получить базовую стоимость бизнеса
    pub fn get_base_cost(&self) -> u64 {
        MIN_DEPOSITS[self.to_index()]
    }

    /// 🆕 Получить базовую доходность
    pub fn get_base_rate(&self) -> u16 {
        BUSINESS_RATES[self.to_index()]
    }


    // Убрано get_upgrade_name - было для NFT метадаты
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Debug)]
pub struct Business {
    pub business_type: BusinessType,
    pub base_invested_amount: u64,       // 🆕 Базовая стоимость (без улучшений)
    pub total_invested_amount: u64,      // 🆕 Общая стоимость (база + все улучшения)
    pub daily_rate: u16,                 // Текущая доходность (база + бонусы улучшений)
    pub upgrade_level: u8,               // 🆕 Уровень улучшения (0-3)
    pub upgrade_history: [u64; 3],       // 🆕 История трат на каждое улучшение
    pub total_earned: u64,
    pub last_claim: i64,
    pub created_at: i64,
    pub is_active: bool,
}

impl Business {
    pub const SIZE: usize = 
        1 +  // business_type
        8 +  // base_invested_amount
        8 +  // total_invested_amount
        2 +  // daily_rate
        1 +  // upgrade_level
        24 + // upgrade_history [u64; 3]
        8 +  // total_earned
        8 +  // last_claim
        8 +  // created_at
        1 +  // is_active
        1;   // is_active bool

    /// Создать новый базовый бизнес
    pub fn new(
        business_type: BusinessType,
        base_amount: u64,
        current_time: i64,
    ) -> Self {
        let base_rate = business_type.get_base_rate();
        
        Self {
            business_type,
            base_invested_amount: base_amount,
            total_invested_amount: base_amount, // Изначально равна базовой
            daily_rate: base_rate,
            upgrade_level: 0,
            upgrade_history: [0; 3],
            total_earned: 0,
            last_claim: current_time,
            created_at: current_time,
            is_active: true,
        }
    }

    /// 🆕 Создать улучшенный бизнес
    pub fn create_upgraded(
        business_type: BusinessType,
        base_amount: u64,
        target_level: u8,
        upgrade_costs: [u64; 3],
        current_time: i64,
    ) -> Result<Self> {
        if target_level > MAX_UPGRADE_LEVEL {
            return Err(ProgramError::InvalidArgument.into());
        }

        let mut business = Self::new(business_type, base_amount, current_time);
        
        // Применяем все улучшения до целевого уровня
        for level in 1..=target_level {
            let upgrade_cost = upgrade_costs[(level - 1) as usize];
            business.apply_upgrade(level, upgrade_cost)?;
        }
        
        Ok(business)
    }

    /// 🆕 Применить улучшение
    pub fn apply_upgrade(&mut self, new_level: u8, upgrade_cost: u64) -> Result<()> {
        if new_level != self.upgrade_level + 1 || new_level > MAX_UPGRADE_LEVEL {
            return Err(ProgramError::InvalidArgument.into());
        }

        // Сохраняем стоимость улучшения
        self.upgrade_history[(new_level - 1) as usize] = upgrade_cost;
        
        // Обновляем общую инвестицию
        self.total_invested_amount = self.total_invested_amount
            .checked_add(upgrade_cost)
            .ok_or(ProgramError::ArithmeticOverflow)?;
        
        // 🔧 ИСПРАВЛЕНИЕ: daily_rate НЕ зависит от уровня апгрейда!
        // Уровни апгрейда увеличивают только invested_amount, но НЕ процентную ставку
        // daily_rate остается базовым для всех уровней
        let base_rate = self.business_type.get_base_rate();
        self.daily_rate = base_rate;  // Всегда базовая ставка, без бонусов
        
        // Обновляем уровень
        self.upgrade_level = new_level;
        
        Ok(())
    }

    /// 🆕 Рассчитать стоимость следующего улучшения
    pub fn calculate_next_upgrade_cost(&self) -> Option<u64> {
        let next_level = self.upgrade_level + 1;
        if next_level > MAX_UPGRADE_LEVEL {
            return None;
        }

        let multiplier = UPGRADE_COST_MULTIPLIERS[(next_level - 1) as usize];
        Some(self.base_invested_amount * multiplier as u64 / 100)
    }

    /// 🆕 Проверить возможность улучшения
    pub fn can_upgrade(&self) -> bool {
        self.upgrade_level < MAX_UPGRADE_LEVEL && self.is_active
    }

    /// 🆕 Получить полную стоимость для возврата при продаже
    pub fn get_total_investment_for_refund(&self) -> u64 {
        self.total_invested_amount // База + все улучшения
    }

    /// Получить стоимость улучшения для определенного уровня
    pub fn get_upgrade_cost(&self, target_level: u8) -> Result<u64> {
        if target_level <= self.upgrade_level || target_level > MAX_UPGRADE_LEVEL {
            return Err(ProgramError::InvalidArgument.into());
        }

        let multiplier = UPGRADE_COST_MULTIPLIERS[(target_level - 1) as usize];
        let upgrade_cost = self.base_invested_amount
            .checked_mul(multiplier as u64)
            .and_then(|x| x.checked_div(100))
            .ok_or(ProgramError::ArithmeticOverflow)?;
        
        Ok(upgrade_cost)
    }

    /// Улучшить бизнес до определенного уровня
    pub fn upgrade_to_level(&mut self, target_level: u8, upgrade_cost: u64) -> Result<()> {
        if target_level != self.upgrade_level + 1 || target_level > MAX_UPGRADE_LEVEL {
            return Err(ProgramError::InvalidArgument.into());
        }

        // Проверяем корректность стоимости
        let expected_cost = self.get_upgrade_cost(target_level)?;
        if upgrade_cost != expected_cost {
            return Err(ProgramError::InvalidArgument.into());
        }

        // Применяем улучшение
        self.apply_upgrade(target_level, upgrade_cost)
    }


    /// Calculate daily earnings with current rate
    pub fn calculate_daily_earnings(&self) -> u64 {
        let base_earnings = (self.total_invested_amount as u128)
            .checked_mul(self.daily_rate as u128)
            .and_then(|x| x.checked_div(10_000))
            .unwrap_or(0) as u64;
            
        base_earnings
    }

    /// Calculate pending earnings
    pub fn calculate_pending_earnings(&self, current_time: i64) -> u64 {
        if !self.is_active || current_time <= self.last_claim {
            return 0;
        }
    
        let seconds_since_claim = (current_time - self.last_claim) as u64;
        let daily_earnings = self.calculate_daily_earnings();
        
        let total_earnings = daily_earnings
            .checked_mul(seconds_since_claim)
            .and_then(|x| x.checked_div(86_400))
            .unwrap_or(0);
        
        total_earnings
    }

    /// Update last claim time
    pub fn update_last_claim(&mut self, current_time: i64) -> Result<()> {
        if current_time < self.last_claim {
            return Err(ProgramError::InvalidArgument.into());
        }
        
        self.last_claim = current_time;
        Ok(())
    }

    /// Add to total earned
    pub fn add_to_total_earned(&mut self, amount: u64) -> Result<()> {
        self.total_earned = self.total_earned
            .checked_add(amount)
            .ok_or(ProgramError::ArithmeticOverflow)?;
        Ok(())
    }

    /// Calculate days since creation
    pub fn days_since_created(&self, current_time: i64) -> u64 {
        if current_time <= self.created_at {
            return 0;
        }
        
        let seconds_diff = (current_time - self.created_at) as u64;
        seconds_diff / 86_400
    }

    /// Calculate earnings for specific period
    pub fn calculate_earnings_for_period(&self, seconds: i64) -> u64 {
        if !self.is_active || seconds <= 0 {
            return 0;
        }
        
        let daily_earnings = self.calculate_daily_earnings();
        // Используем более точный расчет для избежания потери точности при малых числах
        let total_earnings = (daily_earnings as u128)
            .checked_mul(seconds as u128)
            .and_then(|x| x.checked_div(86_400))
            .unwrap_or(0);
            
        total_earnings.min(u64::MAX as u128) as u64
    }

    /// Health check
    pub fn health_check(&self, current_time: i64) -> Result<()> {
        if self.created_at > current_time {
            return Err(ProgramError::InvalidArgument.into());
        }
        
        if self.last_claim > current_time {
            return Err(ProgramError::InvalidArgument.into());
        }
        
        if self.last_claim < self.created_at {
            return Err(ProgramError::InvalidArgument.into());
        }
        
        // Проверяем разумность доходности (максимум 100% в день = 10000 bp)
        if self.daily_rate > 10000 {
            return Err(ProgramError::InvalidArgument.into());
        }
        
        // Проверяем уровень улучшения
        if self.upgrade_level > MAX_UPGRADE_LEVEL {
            return Err(ProgramError::InvalidArgument.into());
        }
        
        // Проверяем что total >= base
        if self.total_invested_amount < self.base_invested_amount {
            return Err(ProgramError::InvalidArgument.into());
        }
        
        Ok(())
    }
}
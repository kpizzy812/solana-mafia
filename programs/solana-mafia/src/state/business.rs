use anchor_lang::prelude::*;

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy, Debug)]
pub enum BusinessType {
    CryptoKiosk = 0,
    MemeCasino = 1,
    NFTLaundry = 2,
    MiningFarm = 3,
    DeFiEmpire = 4,
    SolanaCartel = 5,
}

impl BusinessType {
    /// Get the array index for this business type
    pub fn to_index(&self) -> usize {
        match self {
            BusinessType::CryptoKiosk => 0,
            BusinessType::MemeCasino => 1,
            BusinessType::NFTLaundry => 2,
            BusinessType::MiningFarm => 3,
            BusinessType::DeFiEmpire => 4,
            BusinessType::SolanaCartel => 5,
        }
    }

    /// Create business type from index
    pub fn from_index(index: u8) -> Option<Self> {
        match index {
            0 => Some(BusinessType::CryptoKiosk),
            1 => Some(BusinessType::MemeCasino),
            2 => Some(BusinessType::NFTLaundry),
            3 => Some(BusinessType::MiningFarm),
            4 => Some(BusinessType::DeFiEmpire),
            5 => Some(BusinessType::SolanaCartel),
            _ => None,
        }
    }
}

#[derive(AnchorSerialize, AnchorDeserialize, Clone, Copy)]
pub struct Business {
    pub business_type: BusinessType,
    pub invested_amount: u64,
    pub daily_rate: u16,
    pub upgrade_level: u8,
    pub total_earned: u64,
    pub last_claim: i64,
    pub created_at: i64,
    pub is_active: bool,
}

impl Business {
    /// Size of Business struct for serialization
    pub const SIZE: usize = 
        1 + // business_type enum (1 byte)
        8 + // invested_amount
        2 + // daily_rate
        1 + // upgrade_level
        8 + // total_earned
        8 + // last_claim
        8 + // created_at
        1;  // is_active

    /// Create a new business
    pub fn new(
        business_type: BusinessType,
        invested_amount: u64,
        daily_rate: u16,
        current_time: i64,
    ) -> Self {
        Self {
            business_type,
            invested_amount,
            daily_rate,
            upgrade_level: 0,
            total_earned: 0,
            last_claim: current_time,
            created_at: current_time,
            is_active: true,
        }
    }

    /// Calculate days since creation (БЕЗОПАСНО)
    pub fn days_since_created(&self, current_time: i64) -> u64 {
        if current_time <= self.created_at {
            return 0;
        }
        
        let seconds_diff = (current_time - self.created_at) as u64;
        seconds_diff / 86_400
    }

    /// Calculate current daily earnings with upgrades (БЕЗОПАСНО)
    pub fn calculate_daily_earnings(&self) -> u64 {
        // 🔒 ЗАЩИТА: Используем checked_mul для предотвращения overflow
        let base_earnings = (self.invested_amount as u128)
            .checked_mul(self.daily_rate as u128)
            .and_then(|x| x.checked_div(10_000))
            .unwrap_or(0) as u64;
            
        base_earnings
    }

    /// 🔒 БЕЗОПАСНЫЙ расчет pending earnings (ИСПРАВЛЕНО!)
    pub fn calculate_pending_earnings(&self, current_time: i64) -> u64 {
        if !self.is_active {
            return 0;
        }

        // 🔒 ЗАЩИТА 1: Проверяем что время корректное
        if current_time <= self.last_claim {
            return 0;
        }

        let seconds_since_claim = (current_time - self.last_claim) as u64;
        
        // 🔒 ЗАЩИТА 2: МАКСИМУМ 30 дней earnings (предотвращает huge overflows)
        const MAX_CLAIM_PERIOD: u64 = 30 * 86_400; // 30 дней в секундах
        let capped_seconds = seconds_since_claim.min(MAX_CLAIM_PERIOD);
        
        let daily_earnings = self.calculate_daily_earnings();
        
        // 🔒 ЗАЩИТА 3: Используем checked math для предотвращения overflow
        let total_earnings = daily_earnings
            .checked_mul(capped_seconds)
            .and_then(|x| x.checked_div(86_400))
            .unwrap_or(0);
        
        // 🔒 ЗАЩИТА 4: Дополнительный лимит - не больше 10x от invested_amount
        let max_allowed_earnings = self.invested_amount
            .checked_mul(10)
            .unwrap_or(u64::MAX);
            
        total_earnings.min(max_allowed_earnings)
    }

    /// 🔒 БЕЗОПАСНОЕ обновление last_claim (с проверками)
    pub fn update_last_claim(&mut self, current_time: i64) -> Result<()> {
        // Проверяем что время не идет назад
        if current_time < self.last_claim {
            return Err(ProgramError::InvalidArgument.into());
        }
        
        self.last_claim = current_time;
        Ok(())
    }

    /// 🔒 БЕЗОПАСНОЕ добавление к total_earned
    pub fn add_to_total_earned(&mut self, amount: u64) -> Result<()> {
        self.total_earned = self.total_earned
            .checked_add(amount)
            .ok_or(ProgramError::ArithmeticOverflow)?;
        Ok(())
    }

    /// Проверка здоровья бизнеса
    pub fn health_check(&self, current_time: i64) -> Result<()> {
        // Проверяем что времена логичные
        if self.created_at > current_time {
            return Err(ProgramError::InvalidArgument.into());
        }
        
        if self.last_claim > current_time {
            return Err(ProgramError::InvalidArgument.into());
        }
        
        if self.last_claim < self.created_at {
            return Err(ProgramError::InvalidArgument.into());
        }
        
        // Проверяем что daily_rate разумный (максимум 10% в день = 1000 bp)
        if self.daily_rate > 1000 {
            return Err(ProgramError::InvalidArgument.into());
        }
        
        Ok(())
    }
}
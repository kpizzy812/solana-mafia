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

    /// Calculate days since creation
    pub fn days_since_created(&self, current_time: i64) -> u64 {
        ((current_time - self.created_at) / 86_400) as u64
    }

    /// Calculate current daily earnings with upgrades
    pub fn calculate_daily_earnings(&self) -> u64 {
        let base_earnings = (self.invested_amount as u128 * self.daily_rate as u128) / 10_000;
        base_earnings as u64
    }

    /// Calculate pending earnings since last claim
    pub fn calculate_pending_earnings(&self, current_time: i64) -> u64 {
        if !self.is_active {
            return 0;
        }

        let seconds_since_claim = (current_time - self.last_claim) as u64;
        let daily_earnings = self.calculate_daily_earnings();
        
        // Calculate earnings per second and multiply by elapsed time
        (daily_earnings * seconds_since_claim) / 86_400
    }
}
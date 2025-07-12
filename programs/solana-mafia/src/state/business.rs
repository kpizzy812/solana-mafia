// state/business.rs
use anchor_lang::prelude::*;

/// Types of businesses available in the game
#[derive(AnchorSerialize, AnchorDeserialize, Clone, PartialEq, Debug)]
pub enum BusinessType {
    CryptoKiosk,    // 0.1 SOL - 0.8%/day
    MemeCasino,     // 0.5 SOL - 0.9%/day  
    NFTLaundry,     // 2 SOL - 1.0%/day
    MiningFarm,     // 5 SOL - 1.1%/day
    DeFiEmpire,     // 20 SOL - 1.3%/day
    SolanaCartel,   // 100 SOL - 1.5%/day
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

/// Individual business owned by a player
#[derive(AnchorSerialize, AnchorDeserialize, Clone, Debug)]
pub struct Business {
    /// Type of business
    pub business_type: BusinessType,
    
    /// Amount invested in this business (in lamports)
    pub invested_amount: u64,
    
    /// Current daily rate in basis points (includes upgrades)
    pub daily_rate: u16,
    
    /// Current upgrade level (0-5)
    pub upgrade_level: u8,
    
    /// Total amount earned from this business
    pub total_earned: u64,
    
    /// Timestamp of last earnings claim
    pub last_claim: i64,
    
    /// Timestamp when business was created
    pub created_at: i64,
    
    /// Whether business is active
    pub is_active: bool,
}

impl Business {
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
}
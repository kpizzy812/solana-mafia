pub mod initialize;
pub mod create_player;
pub mod create_business;
pub mod claim_earnings;
pub mod process_referral_bonus;
pub mod update_earnings;
pub mod admin;
pub mod sell_business;
pub mod upgrade_business;
pub mod add_referral_bonus;

// 🔧 Реэкспортируем нужные модули для инструкций
pub use super::constants::*;
pub use super::state::*;
pub use super::error::*;

// Handler functions
pub use initialize::handler as initialize_handler;
pub use create_player::handler as create_player_handler;
pub use create_business::handler as create_business_handler;
pub use claim_earnings::handler as claim_earnings_handler;
pub use process_referral_bonus::handler as process_referral_bonus_handler;
pub use update_earnings::handler as update_earnings_handler;
pub use sell_business::handler as sell_business_handler;
pub use upgrade_business::handler as upgrade_business_handler;
pub use add_referral_bonus::handler as add_referral_bonus_handler;

// Contexts
pub use initialize::Initialize;
pub use create_player::CreatePlayer;
pub use create_business::CreateBusiness;
pub use claim_earnings::ClaimEarnings;
pub use update_earnings::UpdateEarnings;
pub use sell_business::SellBusiness;
pub use upgrade_business::UpgradeBusiness;
pub use add_referral_bonus::AddReferralBonus;

// Admin contexts
pub use admin::{
    TogglePause,
    EmergencyPause,
    UpdateTreasuryFee,
    UpdateBusinessRates,
    GetTreasuryStats
};
pub mod initialize;
pub mod create_business;
pub mod claim_earnings;
pub mod process_referral_bonus;
pub mod update_earnings;
pub mod admin;
pub mod sell_business;
pub mod upgrade_business;
pub mod add_referral_bonus;

// ИСПРАВЛЕНО: Используем конкретные имена функций вместо glob imports
// чтобы избежать конфликтов с именем handler

pub use initialize::handler as initialize_handler;
pub use create_business::{handler as create_business_handler, create_player};
pub use claim_earnings::handler as claim_earnings_handler;
pub use process_referral_bonus::handler as process_referral_bonus_handler;
pub use update_earnings::handler as update_earnings_handler;
pub use admin::*; // admin функции имеют уникальные имена
pub use sell_business::handler as sell_business_handler;
pub use upgrade_business::handler as upgrade_business_handler;
pub use add_referral_bonus::handler as add_referral_bonus_handler;

// Также экспортируем Accounts structs
pub use initialize::Initialize;
pub use create_business::{CreatePlayer, CreateBusiness};
pub use claim_earnings::ClaimEarnings;
pub use process_referral_bonus::AddReferralEarnings;
pub use update_earnings::UpdateEarnings;
pub use sell_business::SellBusiness;
pub use upgrade_business::UpgradeBusiness;
pub use add_referral_bonus::AddReferralBonus;
// error.rs
use anchor_lang::prelude::*;

#[error_code]
pub enum SolanaMafiaError {
    #[msg("Entry fee not paid")]
    EntryFeeNotPaid,
    
    #[msg("Insufficient deposit amount")]
    InsufficientDeposit,
    
    #[msg("Invalid business type")]
    InvalidBusinessType,
    
    #[msg("Maximum businesses limit reached")]
    MaxBusinessesReached,
    
    #[msg("Business not found")]
    BusinessNotFound,
    
    #[msg("Business not owned by player")]
    BusinessNotOwned,
    
    #[msg("No earnings to claim")]
    NoEarningsToClaim,
    
    #[msg("Invalid upgrade level")]
    InvalidUpgradeLevel,
    
    #[msg("Insufficient funds for upgrade")]
    InsufficientFundsForUpgrade,
    
    #[msg("Invalid referrer")]
    InvalidReferrer,
    
    #[msg("Cannot refer yourself")]
    CannotReferYourself,
    
    #[msg("Referrer chain too deep")]
    ReferrerChainTooDeep,
    
    #[msg("Game is paused")]
    GamePaused,
    
    #[msg("Unauthorized admin action")]
    UnauthorizedAdmin,
    
    #[msg("Invalid fee percentage")]
    InvalidFeePercentage,
    
    #[msg("Math overflow")]
    MathOverflow,
    
    #[msg("Business still has active earnings")]
    BusinessHasActiveEarnings,
}
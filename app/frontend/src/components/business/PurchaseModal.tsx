/**
 * Purchase Modal for business purchases
 * 
 * REFACTORED: This file now uses modular architecture with components in:
 * - ./purchase/components - UI components (BusinessSelector, LevelSelector, etc.)
 * - ./purchase/hooks - Business logic hooks
 * - ./purchase/types - Type definitions
 */

// Re-export from the new modular structure
export { PurchaseModal } from './purchase/PurchaseModal';
export type { SlotData, PurchaseModalProps, PurchaseCalculation } from './purchase/types';
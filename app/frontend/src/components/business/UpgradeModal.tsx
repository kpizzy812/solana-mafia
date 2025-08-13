/**
 * UpgradeModal re-export from modular structure
 * 
 * REFACTORED: This file now uses modular architecture with components in:
 * - ./upgrade/components - UI components (BusinessInfo, LevelSelector, etc.)
 * - ./upgrade/hooks - Business logic hooks (useUpgradeLogic)
 * - ./upgrade/types - Type definitions
 */

// Re-export from the new modular structure
export { UpgradeModal } from './upgrade/UpgradeModal';
export type { BusinessData, UpgradeModalProps, UpgradeCalculations } from './upgrade/types';
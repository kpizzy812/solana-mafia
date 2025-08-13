/**
 * Refactored UpgradeModal using modular components
 */

'use client';

import React from 'react';
import { cn } from '@/lib/utils';
import { UpgradeModalProps } from './types';
import { useUpgradeLogic } from './hooks/useUpgradeLogic';
import {
  BusinessInfo,
  LevelSelector,
  UpgradePreview,
  BusinessDetails,
  MaxLevelWarning,
  ModalHeader,
  ActionButtons
} from './components';

export const UpgradeModal: React.FC<UpgradeModalProps> = ({
  isOpen,
  onClose,
  onUpgrade,
  businessData,
  userBalance = 0,
  language = 'en'
}) => {
  const {
    targetLevel,
    setTargetLevel,
    isUpgrading,
    businessType,
    currentLevel,
    maxLevel,
    calculations,
    handleUpgrade,
  } = useUpgradeLogic({
    businessData,
    userBalance,
    isOpen,
    language,
    onUpgrade,
    onClose
  });

  if (!businessData || !businessType) {
    return null;
  }

  return (
    <div className={cn(
      'fixed inset-0 z-50 flex items-center justify-center',
      isOpen ? 'visible' : 'invisible'
    )}>
      {/* Backdrop */}
      <div 
        className={cn(
          'absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity',
          isOpen ? 'opacity-100' : 'opacity-0'
        )}
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className={cn(
        'relative bg-card rounded-xl shadow-2xl border border-border w-full max-w-lg',
        'max-h-[90vh] overflow-hidden transition-all',
        isOpen ? 'scale-100 opacity-100' : 'scale-95 opacity-0'
      )}>
        {/* Header with Balance */}
        <ModalHeader
          userBalance={userBalance}
          canAfford={calculations.canAfford}
          onClose={onClose}
          isUpgrading={isUpgrading}
        />
        
        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-8rem)] p-6 space-y-6">
          {/* Current Business Info */}
          <BusinessInfo
            businessType={businessType}
            businessData={businessData}
            currentLevel={currentLevel}
          />

          {/* Max Level Warning */}
          <MaxLevelWarning
            isMaxLevel={calculations.isMaxLevel}
          />

          {/* Level Selection */}
          <LevelSelector
            businessType={businessType}
            currentLevel={currentLevel}
            targetLevel={targetLevel}
            setTargetLevel={setTargetLevel}
            canUpgrade={calculations.canUpgrade}
          />

          {/* Upgrade Preview */}
          <UpgradePreview
            calculations={calculations}
            canUpgrade={calculations.canUpgrade}
          />

          {/* Business Info */}
          <BusinessDetails
            businessData={businessData}
          />

          {/* Action Buttons */}
          <ActionButtons
            calculations={calculations}
            isUpgrading={isUpgrading}
            onClose={onClose}
            onUpgrade={handleUpgrade}
          />
        </div>
      </div>
    </div>
  );
};
/**
 * Action buttons component for upgrade modal
 */

import React from 'react';
import { Button } from '@/components/ui/Button';
import { UpgradeCalculations } from '../types';

interface ActionButtonsProps {
  calculations: UpgradeCalculations;
  isUpgrading: boolean;
  onClose: () => void;
  onUpgrade: () => Promise<void>;
}

export const ActionButtons: React.FC<ActionButtonsProps> = ({
  calculations,
  isUpgrading,
  onClose,
  onUpgrade
}) => {
  const { canAfford, canUpgrade, isMaxLevel, upgradeCost } = calculations;

  return (
    <div className="flex gap-3 pt-2">
      <Button
        onClick={onClose}
        variant="secondary"
        className="flex-1"
        disabled={isUpgrading}
      >
        Cancel
      </Button>
      
      <Button
        onClick={onUpgrade}
        variant="primary"
        className="flex-1"
        disabled={!canAfford || !canUpgrade || isUpgrading || isMaxLevel}
      >
        {isUpgrading ? 'Upgrading...' : 
         isMaxLevel ? 'Max Level' :
         !canAfford ? 'Insufficient Funds' :
         !canUpgrade ? 'Cannot Upgrade' :
         `Upgrade for ${upgradeCost.toFixed(3)} SOL`}
      </Button>
    </div>
  );
};
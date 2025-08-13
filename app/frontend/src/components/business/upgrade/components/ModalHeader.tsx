/**
 * Modal header component with title and balance
 */

import React from 'react';
import { ChevronUp, Wallet, X } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ModalHeaderProps {
  userBalance: number;
  canAfford: boolean;
  onClose: () => void;
  isUpgrading: boolean;
}

export const ModalHeader: React.FC<ModalHeaderProps> = ({
  userBalance,
  canAfford,
  onClose,
  isUpgrading
}) => {
  return (
    <div className="flex items-center justify-between p-4 border-b border-border">
      <h2 className="text-lg font-semibold text-card-foreground flex items-center gap-2">
        <ChevronUp className="w-5 h-5 text-primary" />
        Upgrade Business
      </h2>
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-1 bg-muted/50 rounded-lg px-2 py-1">
          <Wallet className="w-4 h-4 text-muted-foreground" />
          <span className={cn(
            'text-sm font-medium',
            canAfford ? 'text-success' : 'text-destructive'
          )}>
            {userBalance.toFixed(2)} SOL
          </span>
        </div>
        <button
          onClick={onClose}
          disabled={isUpgrading}
          className="p-1 rounded-lg hover:bg-muted transition-colors disabled:opacity-50"
        >
          <X className="w-5 h-5 text-muted-foreground" />
        </button>
      </div>
    </div>
  );
};
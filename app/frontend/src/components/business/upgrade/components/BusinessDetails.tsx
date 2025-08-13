/**
 * Business details component showing technical information
 */

import React from 'react';
import { BusinessData } from '../types';

interface BusinessDetailsProps {
  businessData: BusinessData;
}

export const BusinessDetails: React.FC<BusinessDetailsProps> = ({
  businessData
}) => {
  return (
    <div className="border-t border-border pt-4">
      <div className="bg-muted/50 rounded-lg p-3">
        <div className="text-xs text-muted-foreground mb-2">
          <strong>Business Details:</strong>
        </div>
        <div className="space-y-1 text-xs">
          <div className="flex justify-between">
            <span>Business ID:</span>
            <span className="font-mono">
              {businessData.businessId.slice(0, 8)}...{businessData.businessId.slice(-4)}
            </span>
          </div>
          <div className="flex justify-between">
            <span>Current Investment:</span>
            <span>{(businessData.totalInvestedAmount / 1e9).toFixed(3)} SOL</span>
          </div>
          <div className="flex justify-between">
            <span>Slot:</span>
            <span>#{businessData.slotIndex + 1}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
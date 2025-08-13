/**
 * Max level warning component
 */

import React from 'react';
import { AlertTriangle } from 'lucide-react';

interface MaxLevelWarningProps {
  isMaxLevel: boolean;
}

export const MaxLevelWarning: React.FC<MaxLevelWarningProps> = ({
  isMaxLevel
}) => {
  if (!isMaxLevel) return null;

  return (
    <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
      <div className="flex items-center gap-2 text-yellow-600">
        <AlertTriangle className="w-5 h-5" />
        <span className="font-medium">Maximum Level Reached</span>
      </div>
      <p className="text-sm text-yellow-600/80 mt-1">
        This business is already at its maximum level and cannot be upgraded further.
      </p>
    </div>
  );
};
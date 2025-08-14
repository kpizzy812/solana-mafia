/**
 * Business information display component
 */

import React from 'react';
import { BusinessData } from '../types';

interface BusinessInfoProps {
  businessType: any;
  businessData: BusinessData;
  currentLevel: number;
  targetLevel?: number; // Add targetLevel prop for upgrade preview
}

export const BusinessInfo: React.FC<BusinessInfoProps> = ({
  businessType,
  businessData,
  currentLevel,
  targetLevel
}) => {
  // Show target level image if upgrading, otherwise current level
  const displayLevel = targetLevel !== undefined ? targetLevel : currentLevel;
  const displayLevelData = businessType?.levels?.[displayLevel];
  const isUpgradePreview = targetLevel !== undefined;

  return (
    <div className="text-center">
      {/* NFT Business Card */}
      {displayLevelData?.imageUrl && (
        <div className="bg-card rounded-lg border border-border overflow-hidden mb-4">
          <img 
            src={displayLevelData.imageUrl} 
            alt={`${businessType.name} - ${displayLevelData.name}`}
            className="w-full aspect-square object-contain bg-muted/20 rounded-t-xl"
            onError={(e) => {
              // Fallback if image fails to load
              e.currentTarget.style.display = 'none';
            }}
          />
          <div className="p-4">
            <h3 className="text-lg font-bold text-card-foreground">{businessType.name}</h3>
            <p className="text-sm text-muted-foreground">{displayLevelData.name}</p>
            <p className="text-xs text-muted-foreground mt-1">{displayLevelData.description}</p>
            {isUpgradePreview && (
              <span className="inline-block text-sm bg-green-500/20 text-green-600 px-2 py-1 rounded-full mt-2">
                Upgrading to Level {displayLevel + 1}
              </span>
            )}
            {!isUpgradePreview && (
              <span className="inline-block text-sm bg-primary/20 text-primary px-2 py-1 rounded-full mt-2">
                Level {displayLevel + 1}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Fallback display if no image */}
      {!displayLevelData?.imageUrl && (
        <div>
          <h3 className="text-xl font-bold text-card-foreground">
            {businessType.name}
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            {businessData.name}
          </p>
          <div className="flex items-center justify-center gap-2 mt-2">
            <span className="text-lg">{businessType.emoji}</span>
            {isUpgradePreview && (
              <span className="text-sm bg-green-500/20 text-green-600 px-2 py-1 rounded-full">
                Upgrading to Level {displayLevel + 1}
              </span>
            )}
            {!isUpgradePreview && (
              <span className="text-sm bg-primary/20 text-primary px-2 py-1 rounded-full">
                Level {displayLevel + 1}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
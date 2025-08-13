/**
 * Business information display component
 */

import React from 'react';
import { BusinessData } from '../types';

interface BusinessInfoProps {
  businessType: any;
  businessData: BusinessData;
  currentLevel: number;
}

export const BusinessInfo: React.FC<BusinessInfoProps> = ({
  businessType,
  businessData,
  currentLevel
}) => {
  const currentLevelData = businessType?.levels?.[currentLevel];

  return (
    <div className="text-center">
      {/* NFT Business Card */}
      {currentLevelData?.imageUrl && (
        <div className="bg-card rounded-lg border border-border overflow-hidden mb-4">
          <img 
            src={currentLevelData.imageUrl} 
            alt={`${businessType.name} - ${currentLevelData.name}`}
            className="w-full aspect-square object-contain bg-muted/20 rounded-t-xl"
            onError={(e) => {
              // Fallback if image fails to load
              e.currentTarget.style.display = 'none';
            }}
          />
          <div className="p-4">
            <h3 className="text-lg font-bold text-card-foreground">{businessType.name}</h3>
            <p className="text-sm text-muted-foreground">{currentLevelData.name}</p>
            <p className="text-xs text-muted-foreground mt-1">{currentLevelData.description}</p>
            <span className="inline-block text-sm bg-primary/20 text-primary px-2 py-1 rounded-full mt-2">
              Level {currentLevel + 1}
            </span>
          </div>
        </div>
      )}

      {/* Fallback display if no image */}
      {!currentLevelData?.imageUrl && (
        <div>
          <h3 className="text-xl font-bold text-card-foreground">
            {businessType.name}
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            {businessData.name}
          </p>
          <div className="flex items-center justify-center gap-2 mt-2">
            <span className="text-lg">{businessType.emoji}</span>
            <span className="text-sm bg-primary/20 text-primary px-2 py-1 rounded-full">
              Level {currentLevel + 1}
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
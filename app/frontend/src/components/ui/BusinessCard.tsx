'use client';

import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { TrendingUp, DollarSign } from 'lucide-react';
import { UpgradeModal } from '@/components/business/UpgradeModal';
import { SellModal } from '@/components/business/SellModal';
import { formatSOL, lamportsToSOL } from '@/lib/api';

interface BusinessData {
  businessId: string;
  slotIndex: number;
  businessType: number;
  level: number;
  totalInvestedAmount: number;
  earningsPerHour: number;
  isActive: boolean;
  createdAt?: number; // Unix timestamp when business was created
}

interface BusinessCardProps {
  name: string;
  level: number;
  earning: number;
  totalEarned?: number;
  businessPrice: number;
  dailyYieldPercent: number;
  imageUrl?: string;
  levelName?: string;
  levelDescription?: string;
  className?: string;
  // Business data for upgrade/sell functionality
  businessData?: BusinessData;
  userBalance?: number;
  onUpgrade?: (businessId: string, currentLevel: number, targetLevel: number) => Promise<void>;
  onSell?: (businessId: string, slotIndex: number) => Promise<void>;
  needsSync?: boolean;
  isInactive?: boolean;
}

export const BusinessCard: React.FC<BusinessCardProps> = ({
  name,
  level,
  earning,
  totalEarned,
  businessPrice,
  dailyYieldPercent,
  imageUrl,
  levelName,
  levelDescription,
  className,
  businessData,
  userBalance = 0,
  onUpgrade,
  onSell,
  needsSync = false,
  isInactive = false,
}) => {
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  const [showSellModal, setShowSellModal] = useState(false);

  const handleUpgrade = async (businessId: string, currentLevel: number, targetLevel: number) => {
    if (onUpgrade) {
      await onUpgrade(businessId, currentLevel, targetLevel);
    }
    setShowUpgradeModal(false);
  };

  const handleSell = async (businessId: string, slotIndex: number) => {
    if (onSell) {
      await onSell(businessId, slotIndex);
    }
    setShowSellModal(false);
  };

  const isMaxLevel = businessData ? 
    (businessData.level >= 3) : // Max level is 3 (levels 0,1,2,3 in smart contract)
    false;

  const canUpgrade = businessData && onUpgrade && !isMaxLevel;
  return (
    <div className={cn(
      'bg-card rounded-xl shadow-lg w-[300px] snap-start overflow-hidden relative flex flex-col h-full',
      needsSync && 'ring-2 ring-yellow-400 ring-opacity-50',
      isInactive && 'opacity-60 ring-2 ring-gray-400 ring-opacity-50',
      className
    )}>
      {/* Status badges */}
      {needsSync && (
        <div className="absolute top-2 right-2 z-10">
          <div className="bg-yellow-400 text-yellow-900 text-xs px-2 py-1 rounded-full font-medium animate-pulse">
            ⚠️ Needs Sync
          </div>
        </div>
      )}
      {isInactive && !needsSync && (
        <div className="absolute top-2 right-2 z-10">
          <div className="bg-gray-400 text-gray-900 text-xs px-2 py-1 rounded-full font-medium">
            🔒 Inactive
          </div>
        </div>
      )}
      {/* Business Image Area - Square */}
      <div className="m-4">
        {imageUrl ? (
          <div className="aspect-square w-full rounded-2xl overflow-hidden bg-white flex items-center justify-center">
            <img 
              src={imageUrl} 
              alt={name}
              className="w-full h-full object-cover"
              onError={(e) => {
                // Fallback to emoji if image fails to load
                e.currentTarget.style.display = 'none';
                const fallback = e.currentTarget.parentElement?.nextElementSibling as HTMLElement;
                if (fallback) fallback.style.display = 'flex';
              }}
            />
          </div>
        ) : null}
        <div 
          className={`aspect-square w-full bg-primary/10 rounded-2xl flex items-center justify-center ${imageUrl ? 'hidden' : ''}`}
          style={{ display: imageUrl ? 'none' : 'flex' }}
        >
          <div className="text-6xl opacity-50">🏢</div>
        </div>
      </div>
      
      {/* Business Info */}
      <div className="p-4 pt-0 space-y-2 flex-1 flex flex-col">
        <div className="text-center">
          <h3 className="text-lg font-bold text-card-foreground">
            {name}
          </h3>
          <div className="space-y-1">
            <p className="text-sm font-semibold text-primary">
              {levelName || `Level ${level + 1}`}
            </p>
            <div className="h-8 flex items-center justify-center">
              {levelDescription && (
                <p className="text-xs text-muted-foreground line-clamp-2 text-center">
                  {levelDescription}
                </p>
              )}
            </div>
          </div>
        </div>
        
        {/* Statistics in purple containers */}
        <div className="space-y-1">
          {/* Business Cost */}
          <div className="bg-violet-500/20 backdrop-blur-sm rounded-lg p-2.5 flex justify-between items-center">
            <span className="text-xs text-muted-foreground">Business Cost</span>
            <span className="text-sm font-bold text-card-foreground">
              {formatSOL(businessPrice)}
            </span>
          </div>
          
          {/* Daily Yield */}
          <div className="bg-violet-500/20 backdrop-blur-sm rounded-lg p-2.5 flex justify-between items-center">
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <TrendingUp className="w-3 h-3" />
              Daily Yield
            </span>
            <div className="text-right flex items-baseline gap-1">
              <span className="text-sm font-bold text-success">
                +{formatSOL(earning)}
              </span>
              <span className="text-xs text-success font-medium">
                ({dailyYieldPercent.toFixed(2)}%)
              </span>
            </div>
          </div>
          
          {/* Total Earned - Hidden because backend doesn't track per-business earnings */}
          {/* 
          <div className="bg-violet-500/20 backdrop-blur-sm rounded-lg p-2.5 flex justify-between items-center">
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <DollarSign className="w-3 h-3" />
              Total Earned
            </span>
            <span className="text-sm font-bold text-card-foreground">
              {formatSOL(totalEarned || 0)}
            </span>
          </div>
          */}
        </div>
        
        {/* Action Buttons */}
        <div className="pt-2 mt-auto">
          <div className="flex space-x-2">
            <button 
              onClick={() => setShowUpgradeModal(true)}
              disabled={!canUpgrade}
              className={cn(
                "flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                canUpgrade
                  ? "bg-primary text-primary-foreground hover:bg-primary/90"
                  : "bg-muted text-muted-foreground cursor-not-allowed"
              )}
            >
              {isMaxLevel ? 'Max Level' : 'Upgrade'}
            </button>
            <button 
              onClick={() => setShowSellModal(true)}
              disabled={!onSell || !businessData}
              className={cn(
                "flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                onSell && businessData
                  ? "bg-secondary text-secondary-foreground hover:bg-secondary/80"
                  : "bg-muted text-muted-foreground cursor-not-allowed"
              )}
            >
              Sell
            </button>
          </div>
        </div>
      </div>

      {/* Upgrade Modal */}
      {businessData && (
        <UpgradeModal
          isOpen={showUpgradeModal}
          onClose={() => setShowUpgradeModal(false)}
          onUpgrade={handleUpgrade}
          businessData={businessData}
          userBalance={userBalance}
        />
      )}

      {/* Sell Modal */}
      {businessData && (
        <SellModal
          isOpen={showSellModal}
          onClose={() => setShowSellModal(false)}
          onSell={handleSell}
          businessData={businessData}
          userBalance={userBalance}
        />
      )}
    </div>
  );
};
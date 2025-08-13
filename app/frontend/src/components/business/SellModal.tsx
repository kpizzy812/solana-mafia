'use client';

import React, { useState, useEffect } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { BUSINESS_TYPES } from '@/data/businesses';
import { DollarSign, TrendingDown, Clock, X, Wallet, AlertTriangle, Calendar, ArrowDown } from 'lucide-react';
import { InfoTooltip } from '@/components/ui/InfoTooltip';
import { useTranslation } from '@/locales';
import { cn } from '@/lib/utils';
import { calculateSellDetails } from '@/lib/solana';
import { getSlotInfo, SlotType } from '@/data/slots';
import toast from 'react-hot-toast';

interface BusinessData {
  businessId: string;
  businessType: number;
  level: number;
  totalInvestedAmount: number;
  earningsPerHour: number;
  slotIndex: number;
  slotType?: SlotType; // Added slot type for discount calculation
  isActive: boolean;
  name: string;
  createdAt?: number; // Unix timestamp
}

interface SellModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSell: (businessId: string, slotIndex: number) => Promise<void>;
  businessData: BusinessData | null;
  userBalance?: number; // in SOL
  language?: 'en' | 'ru';
}

export const SellModal: React.FC<SellModalProps> = ({
  isOpen,
  onClose,
  onSell,
  businessData,
  userBalance = 0,
  language = 'en'
}) => {
  const [isSelling, setIsSelling] = useState(false);
  const [sellDetails, setSellDetails] = useState<any>(null);

  const t = useTranslation(language);

  // Get business type data
  const businessType = businessData ? BUSINESS_TYPES[businessData.businessType] : null;
  const currentLevel = businessData?.level || 0;
  const currentLevelData = businessType?.levels[currentLevel];

  // Calculate sell details when modal opens
  useEffect(() => {
    if (businessData && isOpen) {
      const totalInvestedSOL = businessData.totalInvestedAmount / 1e9; // Convert lamports to SOL
      const createdAt = businessData.createdAt || Math.floor(Date.now() / 1000); // Default to now if not available (should not happen with fixed data flow)
      
      // Get slot discount based on slot type
      const slotType = businessData.slotType || SlotType.Basic;
      const slotInfo = getSlotInfo(slotType);
      const slotDiscount = slotInfo.sellFeeDiscount;
      
      const details = calculateSellDetails(totalInvestedSOL, createdAt, slotDiscount);
      setSellDetails(details);
    }
  }, [businessData, isOpen]);

  if (!businessData || !businessType || !sellDetails) {
    return null;
  }

  const slotIndex = businessData.slotIndex;

  const handleSell = async () => {
    if (isSelling) return;
    
    setIsSelling(true);
    try {
      console.log('🔥 User clicked sell button, starting process...', {
        businessId: businessData.businessId,
        slotIndex,
        sellDetails
      });
      
      await onSell(businessData.businessId, slotIndex);
      toast.success(
        language === 'ru' 
          ? `Бизнес "${businessData.name}" продан за ${sellDetails.returnAmount.toFixed(3)} SOL`
          : `Business "${businessData.name}" sold for ${sellDetails.returnAmount.toFixed(3)} SOL`
      );
      onClose();
    } catch (error) {
      console.error('Sell failed:', error);
      toast.error(
        language === 'ru' 
          ? 'Ошибка при продаже бизнеса'
          : 'Failed to sell business'
      );
    } finally {
      setIsSelling(false);
    }
  };

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
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold text-card-foreground flex items-center gap-2">
            <TrendingDown className="w-5 h-5 text-destructive" />
            Sell Business
          </h2>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 bg-muted/50 rounded-lg px-2 py-1">
              <Wallet className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium text-card-foreground">
                {userBalance.toFixed(2)} SOL
              </span>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-muted transition-colors"
            >
              <X className="w-5 h-5 text-muted-foreground" />
            </button>
          </div>
        </div>
        
        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-8rem)] p-6 space-y-6">
          {/* Current Business Info */}
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

          {/* Early Sale Warning */}
          {sellDetails.daysHeld <= 30 && (
            <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
              <div className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="w-5 h-5" />
                <span className="font-medium">Early Sale Fee</span>
              </div>
              <p className="text-sm text-destructive/80 mt-1">
                Selling within {sellDetails.daysHeld <= 7 ? '7 days' : sellDetails.daysHeld <= 30 ? '30 days' : ''} 
                {' '}incurs a {sellDetails.baseSellFeePercent}% fee. Consider holding longer for better returns.
              </p>
            </div>
          )}

          {/* Sale Details */}
          <div className="space-y-3">
            {/* Days Held */}
            <div className="bg-blue-500/10 rounded-lg p-3">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-blue-500" />
                  <span className="text-sm text-muted-foreground">Days Held</span>
                </div>
                <span className="text-sm font-bold text-blue-500">{sellDetails.daysHeld} days</span>
              </div>
            </div>

            {/* Total Investment */}
            <div className="bg-violet-500/10 rounded-lg p-3">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-primary" />
                  <span className="text-sm text-muted-foreground">Total Investment</span>
                </div>
                <div className="text-right">
                  <div className="text-sm font-bold">{sellDetails.totalInvestedAmount.toFixed(3)} SOL</div>
                </div>
              </div>
            </div>

            {/* Fee Breakdown */}
            <div className="bg-destructive/10 rounded-lg p-3">
              <div className="flex justify-between items-center mb-2">
                <div className="flex items-center gap-2">
                  <TrendingDown className="w-4 h-4 text-destructive" />
                  <span className="text-sm text-muted-foreground">Sale Fee</span>
                  <InfoTooltip
                    content={
                      <div className="space-y-2 max-w-xs">
                        <div className="font-medium text-sm">Early Sale Fees</div>
                        <div className="text-xs text-muted-foreground">
                          • 0-7 days: 25% fee<br />
                          • 8-14 days: 20% fee<br />
                          • 15-21 days: 15% fee<br />
                          • 22-28 days: 10% fee<br />
                          • 29-30 days: 5% fee<br />
                          • 30+ days: 2% fee
                        </div>
                      </div>
                    }
                    position="left"
                    iconClassName="w-3 h-3"
                  />
                </div>
              </div>
              
              <div className="space-y-1">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Base fee ({sellDetails.daysHeld} days):</span>
                  <span className="text-destructive">{sellDetails.baseSellFeePercent}%</span>
                </div>
                {sellDetails.slotDiscount > 0 && (
                  <div className="flex justify-between text-xs">
                    <span className="text-success">Slot discount:</span>
                    <span className="text-success">-{sellDetails.slotDiscount}%</span>
                  </div>
                )}
                <div className="flex justify-between text-xs border-t border-destructive/20 pt-1">
                  <span className="text-destructive">Final fee:</span>
                  <span className="font-bold text-destructive">
                    {sellDetails.finalSellFeePercent}% ({sellDetails.sellFee.toFixed(3)} SOL)
                  </span>
                </div>
              </div>
            </div>

            {/* Return Amount */}
            <div className="bg-success/10 rounded-lg p-3">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2">
                  <ArrowDown className="w-4 h-4 text-success" />
                  <span className="text-sm text-muted-foreground">You Will Receive</span>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold text-success">
                    {sellDetails.returnAmount.toFixed(3)} SOL
                  </div>
                  <div className="text-xs text-success/80">
                    After {sellDetails.finalSellFeePercent}% fee
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Business Info */}
          <div className="border-t border-border pt-4">
            <div className="bg-muted/50 rounded-lg p-3">
              <div className="text-xs text-muted-foreground mb-2">
                <strong>Business Details:</strong>
              </div>
              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span>Business ID:</span>
                  <span className="font-mono">{businessData.businessId.slice(0, 8)}...{businessData.businessId.slice(-4)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Level:</span>
                  <span>{currentLevelData?.name || `Level ${currentLevel + 1}`}</span>
                </div>
                <div className="flex justify-between">
                  <span>Slot:</span>
                  <span>#{businessData.slotIndex + 1}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Warning */}
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-4">
            <div className="flex items-center gap-2 text-yellow-600">
              <AlertTriangle className="w-5 h-5" />
              <span className="font-medium">Warning</span>
            </div>
            <p className="text-sm text-yellow-600/80 mt-1">
              This action is irreversible. Your business will be sold and you will receive the calculated return amount.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <Button
              onClick={onClose}
              variant="secondary"
              className="flex-1"
              disabled={isSelling}
            >
              Cancel
            </Button>
            
            <Button
              onClick={handleSell}
              variant="destructive"
              className="flex-1"
              disabled={isSelling}
            >
              {isSelling 
                ? 'Selling...' 
                : `Sell for ${sellDetails.returnAmount.toFixed(3)} SOL`
              }
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
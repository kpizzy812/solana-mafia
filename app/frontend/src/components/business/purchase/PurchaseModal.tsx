/**
 * EXACT PurchaseModal as original - NFT from GitHub, proper spacing, purple slots, full localization
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/Button';
import { X, DollarSign, TrendingUp, Clock, AlertTriangle, Wallet } from 'lucide-react';
import { useTranslation } from '@/locales';
import { cn } from '@/lib/utils';
import toast from 'react-hot-toast';
import { BUSINESS_TYPES } from '@/data/businesses';
import { InfoTooltip } from '@/components/ui/InfoTooltip';

import { PurchaseModalProps } from './types';
import { usePurchaseLogic } from './hooks/usePurchaseLogic';

export const PurchaseModal: React.FC<PurchaseModalProps> = ({
  isOpen,
  onClose,
  onPurchase,
  availableSlots,
  userBalance = 0,
  language = 'en',
  isNewPlayer = false,
  entryFee = 0
}) => {
  const t = useTranslation(language);
  const [showHelpHint, setShowHelpHint] = useState(false);
  
  const {
    selectedBusinessIndex,
    selectedLevel,
    selectedSlot,
    showHint,
    isPurchasing,
    setSelectedBusinessIndex,
    setSelectedLevel,
    setSelectedSlot,
    setIsPurchasing,
    showHintAnimation,
    selectedBusiness,
    selectedSlotData,
    slotInfo,
    calculations
  } = usePurchaseLogic({
    availableSlots,
    userBalance,
    isNewPlayer,
    entryFee
  });

  // Show "tap for help" hint when modal opens
  useEffect(() => {
    if (isOpen) {
      setShowHelpHint(true);
      const timer = setTimeout(() => {
        setShowHelpHint(false);
      }, 3000); // Show for 3 seconds
      return () => clearTimeout(timer);
    }
  }, [isOpen]);

  const handlePurchase = async () => {
    if (!calculations.canAfford) {
      toast.error(t.insufficient);
      return;
    }

    if (!selectedSlotData?.isUnlocked) {
      toast.error(t.slotLocked);
      return;
    }

    setIsPurchasing(true);
    
    try {
      await onPurchase(selectedBusinessIndex, selectedSlot, selectedLevel);
      toast.success(language === 'ru' ? 'Бизнес куплен успешно!' : 'Business purchased successfully!');
      onClose();
    } catch (error) {
      console.error('Purchase failed:', error);
      toast.error(language === 'ru' ? 'Ошибка покупки' : 'Purchase failed');
    } finally {
      setIsPurchasing(false);
    }
  };

  const handleClose = () => {
    if (!isPurchasing) {
      onClose();
    }
  };

  const businessLevelData = selectedBusiness?.levels[selectedLevel];
  const paybackDays = calculations.dailyYield > 0 ? Math.ceil((isNewPlayer ? calculations.totalCost : calculations.totalPrice) / calculations.dailyYield) : 0;

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
        onClick={handleClose}
      />
      
      {/* Modal */}
      <div className={cn(
        'relative bg-card rounded-xl shadow-2xl border border-border w-full max-w-lg mx-4',
        'max-h-[90vh] overflow-hidden transition-all',
        isOpen ? 'scale-100 opacity-100' : 'scale-95 opacity-0'
      )}>
        {/* Header with balance */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold text-card-foreground">{t.title}</h2>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1 bg-muted/50 rounded-lg px-2 py-1">
              <Wallet className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-medium text-green-400">
                {userBalance.toFixed(2)} SOL
              </span>
            </div>
            <button
              onClick={handleClose}
              disabled={isPurchasing}
              className="p-1 rounded-lg hover:bg-muted transition-colors"
            >
              <X className="w-5 h-5 text-muted-foreground" />
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="overflow-y-auto max-h-[calc(90vh-8rem)] p-6 space-y-4">
          
          {/* NFT Business Card - Load from GitHub */}
          {businessLevelData?.imageUrl && (
            <div className="bg-card rounded-lg border border-border overflow-hidden">
              <img 
                src={businessLevelData.imageUrl} 
                alt={`${selectedBusiness?.name} - ${businessLevelData.name}`}
                className="w-full aspect-square object-contain bg-muted/20 rounded-t-xl"
                onError={(e) => {
                  // Fallback if image fails to load
                  e.currentTarget.style.display = 'none';
                }}
              />
              <div className="p-4 text-center">
                <h3 className="text-lg font-bold text-card-foreground">{selectedBusiness?.name}</h3>
                <p className="text-sm text-muted-foreground">{businessLevelData.name}</p>
                <p className="text-xs text-muted-foreground mt-1">{businessLevelData.description}</p>
                <p className="text-xs text-muted-foreground mt-1">{t.level} {selectedLevel}</p>
              </div>
            </div>
          )}

          {/* Business selection with arrows */}
          <div className="text-center">
            <div className="flex items-center justify-between mb-4">
              <button
                onClick={() => setSelectedBusinessIndex(selectedBusinessIndex === 0 ? BUSINESS_TYPES.length - 1 : selectedBusinessIndex - 1)}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <span className="text-2xl text-muted-foreground">←</span>
              </button>
              
              <div className="flex-1 mx-4">
                <h3 className="text-xl font-bold text-card-foreground mb-2">
                  {selectedBusiness?.name}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {selectedBusiness?.description}
                </p>
              </div>
              
              <button
                onClick={() => setSelectedBusinessIndex((selectedBusinessIndex + 1) % BUSINESS_TYPES.length)}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <span className="text-2xl text-muted-foreground">→</span>
              </button>
            </div>
          </div>

          {/* Choose Business Level */}
          <div>
            <div className="flex items-center gap-2 mb-3 relative">
              <span className="text-sm font-medium text-card-foreground">{t.level}</span>
              <InfoTooltip 
                content={
                  <div className="space-y-2 max-w-xs">
                    <div className="font-medium text-sm">{t.tooltips.businessLevels.title}</div>
                    <div className="text-xs text-muted-foreground">
                      {t.tooltips.businessLevels.content}
                    </div>
                  </div>
                }
              />
            </div>
            
            <div className="bg-muted rounded-lg p-1 flex gap-1 mb-4">
              {[0, 1, 2, 3].map((level) => (
                <button
                  key={level}
                  onClick={() => setSelectedLevel(level)}
                  className={cn(
                    'flex-1 py-2 px-3 rounded-md text-sm font-medium transition-all',
                    selectedLevel === level
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  )}
                >
                  {level + 1}
                </button>
              ))}
            </div>
            
            <div className="text-center text-muted-foreground text-sm">
              {t.level} {selectedLevel + 1}: {businessLevelData?.name}
            </div>
          </div>

          {/* Minimal spacing between price/yield/payback */}
          <div className="space-y-2">
            {/* Price Info */}
            <div className="bg-violet-500/10 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <DollarSign className="w-4 h-4 text-violet-400" />
                  <span className="text-muted-foreground">{t.price}</span>
                </div>
                <div className="text-right">
                  <span className="text-card-foreground font-bold">{calculations.totalPrice.toFixed(3)} SOL</span>
                  {(calculations.slotCost > 0 || (isNewPlayer && entryFee > 0)) && (
                    <div className="text-xs text-muted-foreground">
                      {isNewPlayer && entryFee > 0 ? (
                        calculations.slotCost > 0 
                          ? `Business: ${calculations.businessPrice.toFixed(3)} + Slot: ${calculations.slotCost.toFixed(3)}`
                          : `Business: ${calculations.businessPrice.toFixed(3)}`
                      ) : (
                        `Business: ${calculations.businessPrice.toFixed(3)} + Slot: ${calculations.slotCost.toFixed(3)}`
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Entry Fee для новых игроков */}
            {isNewPlayer && entryFee > 0 && (
              <div className="bg-orange-500/10 rounded-lg p-4 border border-orange-500/20">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <DollarSign className="w-4 h-4 text-orange-400" />
                    <span className="text-muted-foreground">
                      {t.entryFee}
                    </span>
                    <InfoTooltip 
                      content={
                        <div className="space-y-2 max-w-xs">
                          <div className="font-medium text-sm">{t.tooltips.entryFeeHelp.title}</div>
                          <div className="text-xs text-muted-foreground">
                            {t.tooltips.entryFeeHelp.content}
                          </div>
                        </div>
                      }
                    />
                  </div>
                  <div className="text-right">
                    <span className="text-orange-400 font-bold">{entryFee.toFixed(3)} SOL</span>
                    <div className="text-xs text-orange-400/80">
                      {t.newPlayerFee}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Итоговая стоимость для новых игроков */}
            {isNewPlayer && entryFee > 0 && (
              <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-lg p-4 border border-blue-500/20">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-card-foreground font-semibold">
                      {t.totalCost}
                    </span>
                  </div>
                  <div className="text-right">
                    <span className="text-card-foreground font-bold text-lg">
                      {calculations.totalCost.toFixed(3)} SOL
                    </span>
                    <div className="text-xs text-muted-foreground">
                      {calculations.slotCost > 0 
                        ? `${t.businessType} + ${t.slot} + ${t.entryFee}`
                        : `${t.businessType} + ${t.entryFee}`
                      }
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Daily Yield */}
            <div className="bg-green-500/10 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-green-400" />
                  <span className="text-muted-foreground">{t.dailyYield}</span>
                  <InfoTooltip 
                    content={
                      <div className="space-y-2 max-w-xs">
                        <div className="font-medium text-sm">{t.tooltips.dailyYieldHelp.title}</div>
                        <div className="text-xs text-muted-foreground">
                          {t.tooltips.dailyYieldHelp.content}
                        </div>
                      </div>
                    }
                  />
                </div>
                <div className="text-right">
                  <div className="text-green-400 font-bold">+{calculations.dailyYield.toFixed(5)} SOL</div>
                  <div className="text-green-400 text-sm">({calculations.dailyYieldPercent.toFixed(2)}%)</div>
                </div>
              </div>
            </div>

            {/* Payback Period */}
            <div className="bg-blue-500/10 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Clock className="w-4 h-4 text-blue-400" />
                  <span className="text-muted-foreground">{t.payback}</span>
                  <InfoTooltip 
                    content={
                      <div className="space-y-2 max-w-xs">
                        <div className="font-medium text-sm">{t.tooltips.paybackHelp.title}</div>
                        <div className="text-xs text-muted-foreground">
                          {t.tooltips.paybackHelp.content}
                        </div>
                      </div>
                    }
                  />
                </div>
                <span className="text-blue-400 font-bold">{paybackDays} {t.days}</span>
              </div>
            </div>
          </div>

          {/* Selling Fees - separate orange block */}
          <div className="bg-orange-500/10 rounded-lg p-4 border border-orange-500/20">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-4 h-4 text-orange-400" />
              <span className="text-card-foreground font-medium">{t.sellingFees}</span>
              <InfoTooltip 
                content={
                  <div className="space-y-2 max-w-xs">
                    <div className="font-medium text-sm">{t.tooltips.sellingFeesHelp.title}</div>
                    <div className="text-xs text-muted-foreground">
                      {t.tooltips.sellingFeesHelp.content}
                    </div>
                  </div>
                }
              />
            </div>
            
            <div className="text-orange-400 text-sm mb-3">
              {t.holdingPeriod}
            </div>
            
            <div className="grid grid-cols-3 gap-2 text-xs mb-3">
              <div className="text-center">
                <div className="text-muted-foreground">{t.day} 0-7</div>
                <div className="text-red-400 font-bold">25%</div>
              </div>
              <div className="text-center">
                <div className="text-muted-foreground">{t.day} 8-30</div>
                <div className="text-orange-400 font-bold">5-20%</div>
              </div>
              <div className="text-center">
                <div className="text-muted-foreground">{t.day} 30+</div>
                <div className="text-green-400 font-bold">2%</div>
              </div>
            </div>

            {/* Slot Fee Discount Info */}
            {slotInfo.sellFeeDiscount > 0 && (
              <div className="border-t border-orange-500/20 pt-3">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-sm font-medium text-green-400">Selected Slot Discount</span>
                </div>
                <div className="text-center bg-green-500/10 rounded-lg py-2">
                  <div className="text-green-400 font-bold">-{slotInfo.sellFeeDiscount}%</div>
                  <div className="text-xs text-green-400/80">{slotInfo.name} slot discount</div>
                </div>
              </div>
            )}
          </div>

          {/* Select Slot */}
          <div>
            <div className="flex items-center gap-2 mb-4">
              <span className="text-card-foreground font-medium">{t.selectSlot}</span>
              <div className="relative">
                <InfoTooltip 
                  content={
                    <div className="space-y-3 max-w-xs">
                      <div className="font-medium text-sm">{t.tooltips.slotSelection.title}</div>
                      <div className="text-xs text-muted-foreground mb-2">
                        {t.tooltips.slotSelection.content}
                      </div>
                      
                      <div className="space-y-2">
                        <div>
                          <div className="font-medium text-xs text-card-foreground">{t.tooltips.slotSelection.basicSlots}</div>
                          <div className="text-xs text-muted-foreground">{t.tooltips.slotSelection.basicDesc}</div>
                        </div>
                        
                        <div>
                          <div className="font-medium text-xs text-card-foreground">{t.tooltips.slotSelection.regularSlots}</div>
                          <div className="text-xs text-muted-foreground">{t.tooltips.slotSelection.regularDesc}</div>
                        </div>
                        
                        <div>
                          <div className="font-medium text-xs text-card-foreground">{t.tooltips.slotSelection.premiumSlots}</div>
                          <div className="text-xs text-muted-foreground">
                            • {t.tooltips.slotSelection.premiumDesc}<br/>
                            • {t.tooltips.slotSelection.vipDesc}<br/>
                            • {t.tooltips.slotSelection.legendaryDesc}
                          </div>
                        </div>
                      </div>
                    </div>
                  }
                />
                {showHelpHint && (
                  <div className="absolute -top-12 -left-8 flex flex-col items-center animate-in slide-in-from-bottom-2 fade-in-0 duration-300">
                    <div className="flex items-center gap-1 bg-primary text-primary-foreground text-xs px-2 py-1 rounded-md shadow-lg animate-bounce whitespace-nowrap">
                      <span>{t.hintText}</span>
                    </div>
                    <div className="text-primary text-lg animate-bounce" style={{ animationDelay: '0.1s' }}>
                      👇
                    </div>
                  </div>
                )}
              </div>
            </div>
            
            {/* Basic Slots - 6 in one row, purple background NO borders */}
            <div className="mb-4">
              <div className="text-muted-foreground text-sm mb-2">Basic Slots</div>
              <div className="grid grid-cols-6 gap-2">
                {availableSlots.slice(0, 6).map((slot, index) => {
                  const isOccupied = Boolean(slot.business);
                  const isFree = index < 3;
                  const basicSlotCost = isFree ? 0 : calculations.businessPrice * 0.1;
                  return (
                    <button
                      key={slot.index}
                      onClick={() => !isOccupied && setSelectedSlot(slot.index)}
                      disabled={isOccupied}
                      className={cn(
                        'p-2 rounded-lg text-center transition-all bg-violet-500/20',
                        selectedSlot === slot.index
                          ? 'ring-2 ring-violet-400'
                          : isOccupied
                          ? 'cursor-not-allowed opacity-50'
                          : 'hover:bg-violet-500/30'
                      )}
                    >
                      <div className="text-lg mb-1">🏪</div>
                      <div className={cn(
                        "text-xs font-medium",
                        isOccupied ? 'text-red-400' : 
                        isFree ? 'text-green-400' : 
                        'text-orange-400'
                      )}>
                        {isOccupied ? 'Busy' : 
                         isFree ? 'Free' : 
                         `${basicSlotCost.toFixed(3)} SOL`}
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Premium Slots - 3 larger slots, purple background NO borders */}
            <div>
              <div className="text-muted-foreground text-sm mb-2">Premium Slots</div>
              <div className="grid grid-cols-3 gap-3">
                {availableSlots.slice(6, 9).map((slot, index) => {
                  const icons = ['💎', '👑', '⭐'];
                  const costs = [1, 2, 5];
                  const names = ['Premium', 'VIP', 'Legendary'];
                  const bonuses = ['+0.5%', '+1.0%', '+2.0%'];
                  const sellDiscounts = ['', '-50%', '-100%']; // Правильные скидки
                  const isOccupied = Boolean(slot.business);
                  
                  return (
                    <button
                      key={slot.index}
                      onClick={() => !isOccupied && setSelectedSlot(slot.index)}
                      disabled={isOccupied}
                      className={cn(
                        'p-4 rounded-lg text-center transition-all bg-violet-500/20',
                        selectedSlot === slot.index
                          ? 'ring-2 ring-violet-400'
                          : isOccupied
                          ? 'cursor-not-allowed opacity-50'
                          : 'hover:bg-violet-500/30'
                      )}
                    >
                      <div className="text-2xl mb-2">{icons[index]}</div>
                      <div className="text-xs font-medium text-card-foreground mb-1">
                        {names[index]}
                      </div>
                      <div className="text-xs text-green-400 mb-1">{bonuses[index]}</div>
                      {sellDiscounts[index] && (
                        <div className="text-xs text-blue-400 mb-1">{sellDiscounts[index]} fee</div>
                      )}
                      <div className={cn(
                        "text-xs font-medium",
                        isOccupied ? 'text-red-400' : 'text-orange-400'
                      )}>
                        {isOccupied ? 'Busy' : `${costs[index]} SOL`}
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <Button
              variant="secondary"
              onClick={handleClose}
              disabled={isPurchasing}
              className="flex-1"
            >
              {t.cancel}
            </Button>
            
            <Button
              onClick={handlePurchase}
              variant="primary"
              disabled={!calculations.canAfford || isPurchasing || !selectedSlotData?.isUnlocked}
              className="flex-1"
            >
              {isPurchasing ? t.purchasing :
               !calculations.canAfford ? t.insufficient :
               !selectedSlotData?.isUnlocked ? t.slotLocked :
               `${language === 'ru' ? 'Купить бизнес' : 'Buy Now'}`}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
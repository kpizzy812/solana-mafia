/**
 * Slot selector component for purchase modal
 */

import React from 'react';
import { Button } from '@/components/ui/Button';
import { InfoTooltip } from '@/components/ui/InfoTooltip';
import { useTranslation } from '@/locales';
import { SlotData } from '../types';
import { getSlotInfo } from '@/data/slots';
import { cn } from '@/lib/utils';

interface SlotSelectorProps {
  availableSlots: SlotData[];
  selectedSlot: number;
  onSlotSelect: (slotIndex: number) => void;
  language: 'en' | 'ru';
}

export const SlotSelector: React.FC<SlotSelectorProps> = ({
  availableSlots,
  selectedSlot,
  onSlotSelect,
  language
}) => {
  const t = useTranslation(language);

  const getSlotDisplayInfo = (slot: SlotData) => {
    const slotInfo = getSlotInfo(slot.type);
    return {
      ...slotInfo,
      isAvailable: slot.isUnlocked && !slot.business,
      isOccupied: Boolean(slot.business)
    };
  };

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <label className="text-sm font-medium text-muted-foreground">
          {t.choose_slot}
        </label>
        <InfoTooltip content={t.slot_bonus_explanation} />
      </div>
      
      <div className="grid grid-cols-2 gap-2">
        {availableSlots.map((slot) => {
          const displayInfo = getSlotDisplayInfo(slot);
          
          return (
            <button
              key={slot.index}
              onClick={() => displayInfo.isAvailable && onSlotSelect(slot.index)}
              disabled={!displayInfo.isAvailable}
              className={cn(
                "p-3 text-left flex flex-col items-start justify-center h-auto transition-all rounded-lg border",
                selectedSlot === slot.index
                  ? "bg-primary/20 text-primary border-primary"
                  : displayInfo.isAvailable
                  ? "bg-muted/50 text-card-foreground border-border hover:bg-muted"
                  : "bg-muted/20 text-muted-foreground border-border/50 cursor-not-allowed",
                displayInfo.isOccupied && "opacity-50"
              )}
            >
              <div className="flex items-center gap-2 w-full">
                <span className="text-lg">{displayInfo.emoji}</span>
                <div className="flex-1">
                  <div className="text-xs font-medium">
                    {t.slot} {slot.index + 1}
                  </div>
                  <div className="text-xs opacity-80">
                    {displayInfo.name}
                  </div>
                </div>
              </div>
              
              {displayInfo.yieldBonus > 0 && (
                <div className="text-xs text-success mt-1">
                  +{(displayInfo.yieldBonus / 100).toFixed(1)}% {t.yield}
                </div>
              )}
              
              {displayInfo.isOccupied && (
                <div className="text-xs text-destructive mt-1">
                  {t.slot_occupied}
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};
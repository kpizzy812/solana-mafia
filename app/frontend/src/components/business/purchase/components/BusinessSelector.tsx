/**
 * Business selector component for purchase modal
 */

import React from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { BUSINESS_TYPES } from '@/data/businesses';
import { useTranslation } from '@/locales';
import { cn } from '@/lib/utils';

interface BusinessSelectorProps {
  selectedBusinessIndex: number;
  onBusinessSelect: (index: number) => void;
  showHint: boolean;
  language: 'en' | 'ru';
}

export const BusinessSelector: React.FC<BusinessSelectorProps> = ({
  selectedBusinessIndex,
  onBusinessSelect,
  showHint,
  language
}) => {
  const t = useTranslation(language);
  const selectedBusiness = BUSINESS_TYPES[selectedBusinessIndex];

  const nextBusiness = () => {
    onBusinessSelect((selectedBusinessIndex + 1) % BUSINESS_TYPES.length);
  };

  const prevBusiness = () => {
    onBusinessSelect(selectedBusinessIndex === 0 ? BUSINESS_TYPES.length - 1 : selectedBusinessIndex - 1);
  };

  return (
    <div className="text-center">
      <div className="flex items-center justify-between mb-4">
        <button
          onClick={prevBusiness}
          className="p-2 rounded-lg hover:bg-muted transition-colors"
        >
          <ChevronLeft className="w-5 h-5 text-muted-foreground" />
        </button>
        
        <div className="text-center flex-1 mx-4 relative">
          {/* Hint animation */}
          {showHint && (
            <div className="absolute -top-8 left-1/2 transform -translate-x-1/2 bg-primary text-primary-foreground px-2 py-1 rounded text-xs animate-bounce z-10">
              👈 {t.swipe_hint} 👉
            </div>
          )}
          
          <h3 className="text-xl font-bold text-card-foreground">
            {selectedBusiness.name}
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            {selectedBusiness.description}
          </p>
        </div>
        
        <button
          onClick={nextBusiness}
          className="p-2 rounded-lg hover:bg-muted transition-colors"
        >
          <ChevronRight className="w-5 h-5 text-muted-foreground" />
        </button>
      </div>

      {/* Business image */}
      <div className="flex justify-center">
        <div className="w-20 h-20 bg-muted/50 rounded-lg flex items-center justify-center">
          <span className="text-3xl">{selectedBusiness.emoji}</span>
        </div>
      </div>
    </div>
  );
};
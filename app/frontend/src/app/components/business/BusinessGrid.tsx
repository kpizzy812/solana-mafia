/**
 * Business grid component showing user's businesses
 */

import React from 'react';
import { BusinessCard } from '@/components/ui/BusinessCard';
import { useTranslation } from '@/locales';
import { BusinessData } from '../../types';

interface BusinessGridProps {
  businesses: BusinessData[];
  walletBalance: number;
  language: 'en' | 'ru';
  onUpgrade: (businessId: string, currentLevel: number, targetLevel: number) => Promise<void>;
  onSell: (businessId: string, slotIndex: number) => Promise<void>;
}

export const BusinessGrid: React.FC<BusinessGridProps> = ({
  businesses,
  walletBalance,
  language,
  onUpgrade,
  onSell
}) => {
  const t = useTranslation(language);

  if (businesses.length === 0) {
    return null; // Let EmptyBusinessState handle this case
  }

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-foreground">{t.myBusinesses}</h2>
        <span className="text-sm text-muted-foreground">
          {t.swipeToExplore}
        </span>
      </div>
      
      <div className="flex gap-4 overflow-x-auto pb-4 snap-x snap-mandatory scrollbar-hide items-stretch">
        {businesses.map((business) => (
          <BusinessCard
            key={business.id}
            name={business.name}
            level={business.level}
            earning={business.earning}
            totalEarned={business.totalEarned}
            businessPrice={business.businessPrice}
            dailyYieldPercent={business.dailyYieldPercent}
            imageUrl={business.imageUrl}
            levelName={business.levelName}
            levelDescription={business.levelDescription}
            businessData={business.businessData}
            userBalance={walletBalance}
            onUpgrade={onUpgrade}
            onSell={onSell}
            needsSync={business.needsSync}
            className="flex-shrink-0"
          />
        ))}
      </div>
    </div>
  );
};
/**
 * Empty state component when user has no businesses
 */

import React from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';
import { BuildingIcon } from '@/components/ui/icons';
import { useTranslation } from '@/locales';

interface EmptyBusinessStateProps {
  language: 'en' | 'ru';
  onGetStarted: () => void;
}

export const EmptyBusinessState: React.FC<EmptyBusinessStateProps> = ({
  language,
  onGetStarted
}) => {
  const t = useTranslation(language);

  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-foreground">{t.myBusinesses}</h2>
      </div>
      
      <Card>
        <CardContent className="py-12">
          <EmptyState
            icon={<BuildingIcon className="w-16 h-16 text-muted-foreground" />}
            title={t.noBusinesses}
            description={t.noBusinessesDesc}
            actionLabel={t.getStarted}
            onAction={onGetStarted}
          />
        </CardContent>
      </Card>
    </div>
  );
};
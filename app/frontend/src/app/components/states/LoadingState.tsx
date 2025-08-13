/**
 * Loading state component
 */

import React from 'react';
import { useTranslation } from '@/locales';

interface LoadingStateProps {
  language: 'en' | 'ru';
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  language
}) => {
  const t = useTranslation(language);

  return (
    <div className="flex items-center justify-center py-8">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
        <p className="text-muted-foreground">{t.loading}</p>
      </div>
    </div>
  );
};
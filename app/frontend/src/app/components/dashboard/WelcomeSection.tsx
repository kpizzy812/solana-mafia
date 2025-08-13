/**
 * Welcome section component
 */

import React from 'react';
import { useTranslation } from '@/locales';

interface WelcomeSectionProps {
  language: 'en' | 'ru';
}

export const WelcomeSection: React.FC<WelcomeSectionProps> = ({
  language
}) => {
  const t = useTranslation(language);

  return (
    <div className="text-center">
      <h1 className="text-2xl font-bold text-foreground mb-2">
        {t.welcome}
      </h1>
      <p className="text-muted-foreground">
        Build your business empire on Solana
      </p>
    </div>
  );
};
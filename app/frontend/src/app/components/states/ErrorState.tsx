/**
 * Error state component
 */

import React from 'react';
import { Card, CardContent } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { WalletIcon } from '@/components/ui/icons';
import { useTranslation } from '@/locales';

interface ErrorStateProps {
  error: string;
  language: 'en' | 'ru';
  onRetry: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  error,
  language,
  onRetry
}) => {
  const t = useTranslation(language);

  return (
    <Card>
      <CardContent className="py-8">
        <div className="text-center">
          <div className="w-16 h-16 bg-destructive/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <WalletIcon className="w-8 h-8 text-destructive" />
          </div>
          <h3 className="text-lg font-semibold text-foreground mb-2">
            {t.error}
          </h3>
          <p className="text-sm text-muted-foreground mb-4">
            {error}
          </p>
          <Button onClick={onRetry} variant="outline">
            {t.retry}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
};
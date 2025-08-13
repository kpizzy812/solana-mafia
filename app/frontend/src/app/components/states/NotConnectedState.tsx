/**
 * Not connected wallet state component
 */

import React from 'react';
import { WalletButton } from '@/components/wallet/WalletButton';
import { WalletIcon } from '@/components/ui/icons';
import { useTranslation } from '@/locales';

interface NotConnectedStateProps {
  language: 'en' | 'ru';
}

export const NotConnectedState: React.FC<NotConnectedStateProps> = ({
  language
}) => {
  const t = useTranslation(language);

  return (
    <div className="flex flex-col items-center justify-center py-12">
      <div className="w-20 h-20 mb-6 bg-primary/20 rounded-full flex items-center justify-center">
        <WalletIcon className="w-10 h-10 text-primary" />
      </div>
      <h3 className="text-lg font-semibold text-foreground mb-2">
        {t.connectWalletFirst}
      </h3>
      <div className="mt-4">
        <WalletButton />
      </div>
    </div>
  );
};
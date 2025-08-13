'use client';

import React from 'react';
import { Header } from './Header';
import { BottomNavigation } from './BottomNavigation';

interface AppLayoutProps {
  children: React.ReactNode;
  language?: 'en' | 'ru';
  onLanguageChange?: (lang: 'en' | 'ru') => void;
  playerData?: {
    earningsBalance?: number;
    prestigePoints?: number;
    prestigeLevel?: string;
    pointsToNextLevel?: number;
    prestigeProgressPercentage?: number;
  };
  onDataRefresh?: () => void;
}

export const AppLayout: React.FC<AppLayoutProps> = ({
  children,
  language = 'en',
  onLanguageChange,
  playerData,
  onDataRefresh,
}) => {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <Header
        language={language}
        onLanguageChange={onLanguageChange}
        playerData={playerData}
        onDataRefresh={onDataRefresh}
      />
      
      <main className="container mx-auto px-4 py-6 pb-20">
        {children}
      </main>
      
      <BottomNavigation language={language} />
    </div>
  );
};
/**
 * Refactored main page component using modular architecture
 */

'use client';

import React from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { AppLayout } from '@/components/layout/AppLayout';
import { Button } from '@/components/ui/Button';
import { ShoppingCartIcon } from '@/components/ui/icons';
import { PurchaseModal } from '@/components/business/PurchaseModal';
import { WithdrawModal } from '@/components/wallet/WithdrawModal';
import { FomoBanner } from '@/components/ui/FomoBanner';
import { useTranslation } from '@/locales';
import { lamportsToSOL } from '@/lib/api';

// Import modular components
import {
  WelcomeSection,
  DashboardStats,
  EarningsBalance
} from './components/dashboard';
import {
  BusinessGrid,
  EmptyBusinessState
} from './components/business';
import {
  LoadingState,
  ErrorState,
  NotConnectedState
} from './components/states';

// Import hooks
import { useAppLogic, useFomoData } from './hooks';

export default function Home() {
  const wallet = useWallet();
  const { connected, publicKey } = wallet;

  // Main app logic hook
  const {
    language,
    setLanguage,
    languageLoaded, // 🆕 NEW: Prevents language flash on page load
    isPurchaseModalOpen,
    setIsPurchaseModalOpen,
    isWithdrawModalOpen,
    setIsWithdrawModalOpen,
    data,
    loading,
    error,
    playerStats,
    availableSlots,
    businesses,
    walletBalance,
    balanceLoading,
    handleBuyBusiness,
    handleWithdrawClick,
    handleUpdateEarningsClick,
    isUpdatingEarnings,
    handleSyncFromBlockchain,  // 🆕 NEW: Sync from blockchain
    handleWithdrawSubmit,
    handlePurchase,
    handleRetry,
    handleUpgrade,
    handleSell
  } = useAppLogic(wallet, connected, publicKey);

  // FOMO data hook
  const { fomoData } = useFomoData(connected, publicKey);

  const t = useTranslation(language);

  // 🌐 Prevent language flash by waiting for language to load from localStorage
  if (!languageLoaded) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    );
  }

  return (
    <AppLayout
      language={language}
      onLanguageChange={setLanguage}
      playerData={{
        prestigePoints: data.stats?.prestige_points || data.profile?.prestige_points || 0,
        prestigeLevel: data.stats?.prestige_level || data.profile?.prestige_level || 'wannabe',
        pointsToNextLevel: data.stats?.points_to_next_level || data.profile?.points_to_next_level || 50,
        prestigeProgressPercentage: data.stats?.prestige_progress_percentage || data.profile?.prestige_progress_percentage || 0,
      }}
    >
      <div className="space-y-6">
        {/* Welcome Section */}
        <WelcomeSection language={language} />

        {!connected ? (
          // Not connected state
          <NotConnectedState language={language} />
        ) : (
          <>
            {/* FOMO Banner */}
            <FomoBanner
              totalPlayers={fomoData.totalPlayers}
              currentEntryFee={fomoData.currentEntryFee}
              currentEntryFeeUsd={fomoData.currentEntryFeeUsd}
              solPriceUsd={fomoData.solPriceUsd}
              language={language}
            />
            
            {/* Loading State */}
            {loading && <LoadingState language={language} />}

            {/* Error State */}
            {error && !loading && (
              <ErrorState
                error={error}
                language={language}
                onRetry={handleRetry}
              />
            )}

            {/* Dashboard Content - Show when data is available */}
            {!loading && !error && (
              <>
                {/* Dashboard Statistics */}
                <DashboardStats
                  playerStats={playerStats}
                  walletBalance={walletBalance}
                  balanceLoading={balanceLoading}
                  language={language}
                />

                {/* Earnings Balance */}
                <EarningsBalance
                  playerStats={playerStats}
                  onWithdrawClick={handleWithdrawClick}
                  onUpdateEarningsClick={handleUpdateEarningsClick}
                  onSyncFromBlockchain={handleSyncFromBlockchain}  // 🆕 NEW: Sync from blockchain
                  isUpdatingEarnings={isUpdatingEarnings}
                  language={language}
                />

                {/* Buy Business Button */}
                <div className="space-y-2">
                  <Button
                    onClick={handleBuyBusiness}
                    variant="primary"
                    className="w-full h-10 text-sm font-medium"
                  >
                    <ShoppingCartIcon className="w-4 h-4 mr-2" />
                    {t.buyBusiness}
                  </Button>
                </div>

                {/* My Businesses Section */}
                {businesses.length === 0 ? (
                  <EmptyBusinessState
                    language={language}
                    onGetStarted={handleBuyBusiness}
                  />
                ) : (
                  <BusinessGrid
                    businesses={businesses}
                    walletBalance={walletBalance}
                    language={language}
                    onUpgrade={handleUpgrade}
                    onSell={handleSell}
                  />
                )}
              </>
            )}
          </>
        )}
      </div>

      {/* Purchase Modal */}
      <PurchaseModal
        isOpen={isPurchaseModalOpen}
        onClose={() => setIsPurchaseModalOpen(false)}
        onPurchase={handlePurchase}
        availableSlots={availableSlots}
        userBalance={walletBalance}
        language={language}
        isNewPlayer={!data.profile && (!data.stats || (data.stats && data.stats.total_businesses === 0 && !data.stats.last_activity))} // New player if no profile and no real stats
        entryFee={fomoData.currentEntryFee} // Entry fee from FOMO data
      />

      {/* Withdraw Modal */}
      <WithdrawModal
        isOpen={isWithdrawModalOpen}
        onClose={() => setIsWithdrawModalOpen(false)}
        onWithdraw={handleWithdrawSubmit}
        availableBalance={lamportsToSOL(playerStats.earningsBalance)}
        language={language}
      />
    </AppLayout>
  );
}
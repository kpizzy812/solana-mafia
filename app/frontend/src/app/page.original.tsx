'use client';

import React, { useState } from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { AppLayout } from '@/components/layout/AppLayout';
import { DashboardCard } from '@/components/ui/DashboardCard';
import { BusinessCard } from '@/components/ui/BusinessCard';
import { EmptyState } from '@/components/ui/EmptyState';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { WalletButton } from '@/components/wallet/WalletButton';
import { WalletIcon, BuildingIcon, GridIcon, ShoppingCartIcon } from '@/components/ui/icons';
import { usePlayerData } from '@/hooks/usePlayerData';
import { useWalletBalance } from '@/hooks/useWalletBalance';
import { formatSOL, calculateDailyYield, lamportsToSOL } from '@/lib/api';

// Smart balance formatting (same as Header and Modal)
const formatBalance = (balance: number) => {
  if (balance < 0.00001) {
    return balance.toFixed(9);
  } else if (balance < 0.0001) {
    return balance.toFixed(8);
  } else if (balance < 0.001) {
    return balance.toFixed(7);
  } else if (balance < 0.01) {
    return balance.toFixed(5);
  } else if (balance < 0.1) {
    return balance.toFixed(4);
  } else {
    return balance.toFixed(3);
  }
};
import { BUSINESS_TYPES } from '@/data/businesses';
import { PurchaseModal } from '@/components/business/PurchaseModal';
import { SlotType } from '@/data/slots';
import { useTranslation } from '@/locales';
import { InfoTooltip } from '@/components/ui/InfoTooltip';
import { purchaseBusiness, sellBusiness, withdrawEarnings } from '@/lib/solana';
import { apiClient } from '@/lib/api';
import toast from 'react-hot-toast';
import { FomoBanner } from '@/components/ui/FomoBanner';
import { upgradeBusiness } from '@/lib/solana';
import { retryPlayerDataFetch, cn } from '@/lib/utils';
import { WithdrawModal } from '@/components/wallet/WithdrawModal';

// Helper interface matching PurchaseModal expectations
interface SlotData {
  index: number;
  type: SlotType;
  isUnlocked: boolean;
  business?: any;
}

export default function Home() {
  const wallet = useWallet();
  const { connected, publicKey } = wallet;
  const [language, setLanguage] = useState<'en' | 'ru'>('en');
  const [isPurchaseModalOpen, setIsPurchaseModalOpen] = useState(false);
  const [isWithdrawModalOpen, setIsWithdrawModalOpen] = useState(false);
  const [fomoData, setFomoData] = useState({
    totalPlayers: 0,
    currentEntryFee: 0.012, // SOL amount
    currentEntryFeeUsd: 2.0, // USD amount  
    solPriceUsd: 162.0, // Current SOL price
    lastUpdated: null
  });
  const { data, loading, error, refetch } = usePlayerData();
  const { balance: walletBalance, loading: balanceLoading } = useWalletBalance();
  // NFT system removed - now using backend data only

  // Calculate derived data from backend response
  const playerStats = React.useMemo(() => {
    if (!data.stats && !data.profile) {
      // If no data yet, show default values for new player
      return {
        totalEarnings: 0,
        businessCount: 0,
        businessSlots: 9, // Show all 9 business slots available
        totalSlots: 9, // Always 9 total slots (3 free + 3 basic paid + 3 premium)
        earningsBalance: 0,
      };
    }

    // All 9 slots are always available by design:
    // - Slots 0-2: Basic (free)
    // - Slots 3-5: Basic (10% of business cost)  
    // - Slots 6-8: Premium/VIP/Legendary (1/2/5 SOL fixed cost)
    const totalSlots = 9; // Always 9 slots available
    const businessCount = data.stats?.active_businesses || 0;
    
    return {
      totalEarnings: data.stats?.total_earnings || 0,
      businessCount: businessCount,
      businessSlots: Math.max(0, totalSlots - businessCount),
      totalSlots: totalSlots,
      earningsBalance: data.stats?.earnings_balance || 0,
    };
  }, [data.stats, data.profile]);

  // Generate slot data for the purchase modal
  const availableSlots = React.useMemo((): SlotData[] => {
    const slots: SlotData[] = [];
    
    // Create a map of occupied slots from businesses
    const occupiedSlots = new Map<number, any>();
    
    // Use backend data
    if (data.businesses?.businesses) {
      data.businesses.businesses.forEach((business) => {
        if (business.slot_index !== undefined) {
          occupiedSlots.set(business.slot_index, {
            id: business.business_id,
            name: business.name || business.business_type,
            businessType: business.business_type,
            level: business.level,
          });
        }
      });
    }
    
    // Create basic slots (6 total: 0-2 free, 3-5 paid)
    for (let i = 0; i < 6; i++) {
      const business = occupiedSlots.get(i);
      slots.push({
        index: i,
        type: SlotType.Basic,
        isUnlocked: true, // All 6 basic slots are available (UI shows cost for 3-5)
        business: business
      });
    }
    
    // Add premium slots (6-8: Premium/VIP/Legendary with fixed costs)
    const premiumSlotTypes = [SlotType.Premium, SlotType.VIP, SlotType.Legendary];
    premiumSlotTypes.forEach((slotType, index) => {
      const slotIndex = 6 + index;
      const business = occupiedSlots.get(slotIndex);
      
      slots.push({
        index: slotIndex,
        type: slotType,
        isUnlocked: true, // All premium slots are available for purchase
        business: business
      });
    });
    
    // Return all slots (UI will handle unlocked/occupied states)
    return slots;
  }, [data.businesses]);

  // Transform businesses data for display
  const businesses = React.useMemo(() => {
    if (!data.businesses?.businesses) return [];
    
    return data.businesses.businesses.map((business) => ({
      id: business.business_id,
      name: business.name || business.business_type,
      level: business.level,
      earning: business.earnings_per_hour,
      totalEarned: 0, // This would need to be calculated from earnings history
      businessPrice: business.base_cost, // Use actual base cost from backend
      dailyYieldPercent: calculateDailyYield(business.earnings_per_hour, business.total_invested), // Use total invested for yield calculation
      imageUrl: undefined, // Backend data doesn't include images
      needsSync: false, // Direct ownership - no sync needed
      businessData: {
        businessId: business.business_id,
        slotIndex: business.slot_index,
        businessType: business.business_type,
        level: business.level,
        totalInvestedAmount: business.total_invested,
        earningsPerHour: business.earnings_per_hour,
        isActive: business.is_active,
      },
    }));
  }, [data.businesses]);

  const t = useTranslation(language);

  // Load FOMO data on wallet connect
  React.useEffect(() => {
    if (connected && wallet.publicKey) {
      const loadFomoData = async () => {
        try {
          // Try new SOL price endpoint first
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
          
          let solPriceUsd = 162.0;
          let currentEntryFeeUsd = 2.0;
          let currentEntryFeeSol = 0.012;
          
          try {
            const priceResponse = await fetch(`${apiUrl}/api/v1/stats/sol-price`);
            if (priceResponse.ok) {
              const priceData = await priceResponse.json();
              if (priceData.success && priceData.data) {
                solPriceUsd = priceData.data.sol_price_usd || 162.0;
                currentEntryFeeUsd = priceData.data.current_entry_fee_usd || 2.0;
                currentEntryFeeSol = priceData.data.current_entry_fee_sol || 0.012;
              }
            }
          } catch (err) {
            console.warn('SOL price endpoint failed, using fallback');
          }
          
          // Get global stats (including player count) from existing endpoint
          const response = await apiClient.getGlobalStats();
          if (response.success && response.data) {
            setFomoData({
              totalPlayers: response.data.total_players,
              currentEntryFee: currentEntryFeeSol,
              currentEntryFeeUsd: currentEntryFeeUsd,
              solPriceUsd: solPriceUsd,
              lastUpdated: 'live'
            });
          }
        } catch (error) {
          console.error('Failed to load FOMO data:', error);
        }
      };
      
      loadFomoData();
      
      // Refresh FOMO data every 30 seconds
      const interval = setInterval(loadFomoData, 30000);
      return () => clearInterval(interval);
    }
  }, [connected, wallet.publicKey]);

  const handleBuyBusiness = () => {
    setIsPurchaseModalOpen(true);
  };

  const handleWithdrawClick = () => {
    setIsWithdrawModalOpen(true);
  };

  const handleWithdrawSubmit = async (amount: number) => {
    if (!connected || !publicKey) {
      throw new Error('Wallet not connected');
    }
    
    try {
      const result = await withdrawEarnings(wallet, amount);
      
      // Refresh data after successful withdrawal
      setTimeout(() => {
        refetch();
      }, 2000); // Wait 2 seconds for blockchain to update
      
      return result;
    } catch (error) {
      console.error('❌ Withdrawal failed:', error);
      throw error;
    }
  };

  const handlePurchase = async (businessTypeId: number, slotIndex: number, level: number = 0) => {
    if (!connected || !publicKey) {
      toast.error('Please connect your wallet first');
      return;
    }

    try {
      toast.loading('Purchasing business...', { id: 'purchase' });
      
      const txHash = await purchaseBusiness(
        wallet,
        businessTypeId,
        slotIndex,
        level
      );
      
      toast.success(`Business purchased! Transaction: ${txHash.slice(0, 8)}...`, { id: 'purchase' });
      
      // Refresh data after successful purchase with retry logic for indexer delay
      try {
        await retryPlayerDataFetch(refetch);
      } catch (retryError) {
        console.warn('Failed to fetch updated player data after purchase, indexer may still be processing:', retryError);
        // Don't show error toast as the transaction was successful
      }
      
    } catch (error) {
      console.error('Purchase failed:', error);
      toast.error(`Purchase failed: ${error instanceof Error ? error.message : 'Unknown error'}`, { id: 'purchase' });
    }
  };

  const handleRetry = () => {
    toast.loading('Загрузка данных...', { id: 'retry' });
    refetch().then(() => {
      toast.success('Данные обновлены!', { id: 'retry' });
    }).catch(() => {
      toast.error('Ошибка загрузки данных', { id: 'retry' });
    });
  };

  // Handle business upgrade
  const handleUpgrade = async (businessId: string, currentLevel: number, targetLevel: number) => {
    if (!connected || !publicKey) {
      toast.error('Please connect your wallet first');
      return;
    }

    try {
      toast.loading('Upgrading business...', { id: 'upgrade' });

      // Find business from backend data to get slot index
      const business = data.businesses?.businesses.find(b => b.business_id === businessId);
      if (!business || business.slot_index === undefined) {
        throw new Error('Business not found or slot index missing');
      }

      console.log('🔄 Starting upgrade process...', {
        businessId,
        currentLevel,
        targetLevel,
        slotIndex: business.slot_index,
      });

      const result = await upgradeBusiness(wallet, businessId, business.slot_index, currentLevel, targetLevel);
      
      toast.success(`Business upgraded! Transaction: ${result.signature.slice(0, 8)}...`, { id: 'upgrade' });
      
      // Wait a bit for blockchain to update, then refresh data
      console.log('⏳ Waiting for blockchain to update...');
      setTimeout(async () => {
        try {
          console.log('🔄 Refreshing backend data after upgrade...');
          await refetch(); // Refresh backend data
        } catch (refreshError) {
          console.error('Failed to refresh data after upgrade:', refreshError);
        }
      }, 2000); // Wait 2 seconds for blockchain to update
      
    } catch (error) {
      console.error('Upgrade failed:', error);
      
      // Extract more detailed error message
      let errorMessage = 'Unknown error';
      if (error instanceof Error) {
        errorMessage = error.message;
        // Check if it's a duplicate transaction error (which might mean it actually succeeded)
        if (errorMessage.includes('already been processed')) {
          toast.success('Upgrade may have succeeded! Refreshing data...', { id: 'upgrade' });
          setTimeout(() => {
            refetch();
          }, 2000);
          return;
        }
      }
      
      toast.error(`Upgrade failed: ${errorMessage}`, { id: 'upgrade' });
    }
  };

  // Handle business sell
  const handleSell = async (businessId: string, slotIndex: number) => {
    if (!connected || !publicKey) {
      toast.error('Please connect your wallet first');
      return;
    }

    try {
      toast.loading('Selling business...', { id: 'sell' });

      console.log('🔥 Starting sell process...', {
        businessId,
        slotIndex,
      });

      const result = await sellBusiness(wallet, businessId, slotIndex);
      
      toast.success(`Business sold! Transaction: ${result.signature.slice(0, 8)}...`, { id: 'sell' });
      
      // Wait a bit for blockchain to update, then refresh data
      console.log('⏳ Waiting for blockchain to update...');
      setTimeout(async () => {
        try {
          console.log('🔄 Refreshing backend data after sale...');
          await refetch(); // Refresh backend data
        } catch (refreshError) {
          console.error('Failed to refresh data after sale:', refreshError);
        }
      }, 2000); // Wait 2 seconds for blockchain to update
      
    } catch (error) {
      console.error('Sale failed:', error);
      
      // Extract more detailed error message
      let errorMessage = 'Unknown error';
      if (error instanceof Error) {
        errorMessage = error.message;
        // Check if it's a duplicate transaction error (which might mean it actually succeeded)
        if (errorMessage.includes('already been processed')) {
          toast.success('Sale may have succeeded! Refreshing data...', { id: 'sell' });
          setTimeout(() => {
            refetch();
          }, 2000);
          return;
        }
      }
      
      toast.error(`Sale failed: ${errorMessage}`, { id: 'sell' });
    }
  };


  // No sync needed with direct ownership


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
        <div className="text-center">
          <h1 className="text-2xl font-bold text-foreground mb-2">
            {t.welcome}
          </h1>
          <p className="text-muted-foreground">
            Build your business empire on Solana
          </p>
        </div>

        {!connected ? (
          // Not connected state
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
        ) : (
          <>            
            {/* FOMO Banner */}
            {connected && (
              <FomoBanner
                totalPlayers={fomoData.totalPlayers}
                currentEntryFee={fomoData.currentEntryFee}
                currentEntryFeeUsd={fomoData.currentEntryFeeUsd}
                solPriceUsd={fomoData.solPriceUsd}
                language={language}
              />
            )}
            
            {/* Loading State */}
            {loading && (
              <div className="flex items-center justify-center py-8">
                <div className="text-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
                  <p className="text-muted-foreground">{t.loading}</p>
                </div>
              </div>
            )}

            {/* Error State */}
            {error && !loading && (
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
                    <Button onClick={handleRetry} variant="outline">
                      {t.retry}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )}


            {/* Dashboard Stats - Show when data is available */}
            {!loading && !error && (
              <>
                <div className="mb-6">
                  <h2 className="text-lg font-semibold text-foreground mb-3">{t.dashboard}</h2>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
                    <div className="relative">
                      <DashboardCard
                        title={t.totalEarnings} 
                        value={formatSOL(playerStats.totalEarnings)}
                        icon={<WalletIcon className="w-4 h-4 text-primary" />}
                      />
                      <div className="absolute -top-1 -right-1">
                        <InfoTooltip
                          content={
                            <div className="space-y-2 max-w-xs">
                              <div className="font-medium text-sm">{t.tooltips.totalEarningsHelp.title}</div>
                              <div className="text-xs text-muted-foreground">
                                {t.tooltips.totalEarningsHelp.content}
                              </div>
                            </div>
                          }
                          position="bottom"
                        />
                      </div>
                    </div>
                    
                    <div className="relative">
                      <DashboardCard
                        title={t.businesses}
                        value={playerStats.businessCount}
                        icon={<BuildingIcon className="w-4 h-4 text-primary" />}
                      />
                      <div className="absolute -top-1 -right-1">
                        <InfoTooltip
                          content={
                            <div className="space-y-2 max-w-xs">
                              <div className="font-medium text-sm">{t.tooltips.businessCountHelp.title}</div>
                              <div className="text-xs text-muted-foreground">
                                {t.tooltips.businessCountHelp.content}
                              </div>
                            </div>
                          }
                          position="bottom"
                        />
                      </div>
                    </div>
                    
                    <div className="relative">
                      <DashboardCard
                        title={t.businessSlots}
                        value={`${playerStats.totalSlots - playerStats.businessCount}/${playerStats.totalSlots}`}
                        icon={<GridIcon className="w-4 h-4 text-primary" />}
                      />
                      <div className="absolute -top-1 -right-1">
                        <InfoTooltip
                          content={
                            <div className="space-y-2 max-w-xs">
                              <div className="font-medium text-sm">{t.tooltips.businessSlotsHelp.title}</div>
                              <div className="text-xs text-muted-foreground">
                                {t.tooltips.businessSlotsHelp.content}
                              </div>
                            </div>
                          }
                          position="bottom"
                        />
                      </div>
                    </div>
                    
                    <div className="relative">
                      <DashboardCard
                        title={t.walletBalance}
                        value={balanceLoading ? "..." : `${walletBalance.toFixed(2)} SOL`}
                        icon={<WalletIcon className="w-4 h-4 text-green-500" />}
                      />
                      <div className="absolute -top-1 -right-1">
                        <InfoTooltip
                          content={
                            <div className="space-y-2 max-w-xs">
                              <div className="font-medium text-sm">{t.tooltips.walletBalanceHelp.title}</div>
                              <div className="text-xs text-muted-foreground">
                                {t.tooltips.walletBalanceHelp.content}
                              </div>
                            </div>
                          }
                          position="bottom"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Earnings balance - always show */}
                  <div className="mb-4 relative">
                    <div className="bg-card rounded-lg border border-border p-4 hover:bg-accent/50 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3">
                          <img 
                            src="/icons/solana.png" 
                            alt="Solana" 
                            className="w-16 h-16 object-contain"
                          />
                          <div>
                            <div className="text-sm font-medium text-muted-foreground">{t.earningsBalance}</div>
                            <div className="text-xl font-bold text-card-foreground">
                              {formatBalance(lamportsToSOL(playerStats.earningsBalance))} SOL
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={handleWithdrawClick}
                          disabled={playerStats.earningsBalance === 0}
                          className={cn(
                            "px-4 py-2 rounded-lg text-sm font-medium transition-colors",
                            playerStats.earningsBalance > 0
                              ? "bg-green-500 hover:bg-green-600 text-white"
                              : "bg-transparent border border-muted-foreground/20 text-muted-foreground/40 cursor-not-allowed"
                          )}
                        >
                          {t.withdraw}
                        </button>
                      </div>
                    </div>
                    <div className="absolute -top-1 -right-1">
                      <InfoTooltip
                        content={
                          <div className="space-y-2 max-w-xs">
                            <div className="font-medium text-sm">{t.tooltips.earningsBalanceHelp.title}</div>
                            <div className="text-xs text-muted-foreground">
                              {t.tooltips.earningsBalanceHelp.content}
                            </div>
                          </div>
                        }
                        position="bottom"
                      />
                    </div>
                  </div>

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
                </div>

                {/* My Businesses Section */}
                <div className="mb-6">
                  <div className="flex items-center justify-between mb-4">
                    <h2 className="text-xl font-bold text-foreground">{t.myBusinesses}</h2>
                    {businesses.length > 0 && (
                      <span className="text-sm text-muted-foreground">
                        {t.swipeToExplore}
                      </span>
                    )}
                  </div>
                  
                  {businesses.length === 0 ? (
                    <Card>
                      <CardContent className="py-12">
                        <EmptyState
                          icon={<BuildingIcon className="w-16 h-16 text-muted-foreground" />}
                          title={t.noBusinesses}
                          description={t.noBusinessesDesc}
                          actionLabel={t.getStarted}
                          onAction={handleBuyBusiness}
                        />
                      </CardContent>
                    </Card>
                  ) : (
                    <div className="flex gap-4 overflow-x-auto pb-4 snap-x snap-mandatory scrollbar-hide">
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
                          businessData={business.businessData}
                          userBalance={walletBalance}
                          onUpgrade={handleUpgrade}
                          onSell={handleSell}
                          needsSync={business.needsSync}
                        />
                      ))}
                    </div>
                  )}
                </div>

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
        isNewPlayer={!data.profile} // New player if no profile exists
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

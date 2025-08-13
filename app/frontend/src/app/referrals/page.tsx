/**
 * Referrals page - Referral system interface
 */

'use client';

import React from 'react';
import { useWallet } from '@solana/wallet-adapter-react';
import { WalletButton } from '@/components/wallet/WalletButton';
import { Copy, Users, TrendingUp, Award, Info, CheckCircle } from 'lucide-react';
import toast from 'react-hot-toast';
import { AppLayout } from '@/components/layout/AppLayout';
import { useLanguage } from '@/hooks/useLanguage';
import { useTranslation } from '@/locales';
import { useReferralCode, useReferralActions } from '@/stores/useReferralStore';
import { ReferralStats, ReferralsList, PrestigeDisplay, CommissionRates, SolBalance } from './components';

export default function ReferralsPage() {
  const { connected, publicKey } = useWallet();
  const { language, setLanguage, isLoaded: languageLoaded } = useLanguage();
  const referralCode = useReferralCode();
  const { getReferralLink } = useReferralActions();
  
  const t = useTranslation(language);

  const handleCopyReferralLink = async () => {
    if (!connected || !publicKey) {
      toast.error(language === 'ru' ? 'Сначала подключите кошелек' : 'Please connect your wallet first');
      return;
    }

    try {
      // Get user's referral code (placeholder - replace with actual API call)
      const userReferralCode = publicKey.toString().slice(0, 8).toUpperCase();
      const referralLink = getReferralLink(userReferralCode);
      
      await navigator.clipboard.writeText(referralLink);
      toast.success(t.referrals.copySuccess, {
        icon: <CheckCircle className="w-4 h-4 text-green-500" />
      });
    } catch (error) {
      console.error('Failed to copy referral link:', error);
      toast.error(t.referrals.copyFailed);
    }
  };

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
    >
      <div className="max-w-6xl mx-auto">
        {!connected ? (
          // Not connected state
          <div className="max-w-2xl mx-auto">
            <div className="bg-card border border-border rounded-xl p-8 text-center">
              <Users className="w-16 h-16 text-muted-foreground mx-auto mb-4" />
              <h2 className="text-2xl font-semibold mb-4">{t.referrals.connectWalletTitle}</h2>
              <p className="text-muted-foreground mb-6 text-lg">
                {t.referrals.connectWalletDescription}
              </p>
              <WalletButton className="mx-auto" />
            </div>
          </div>
        ) : (
          // Connected state
          <>
            {/* Header */}
            <div className="mb-8">
              <h1 className="text-3xl font-bold">{t.referrals.title}</h1>
              <p className="text-muted-foreground">
                {t.referrals.description}
              </p>
            </div>

            {/* Referral Link Section */}
            <div className="grid gap-6 mb-8">
              <div className="bg-card border border-border rounded-xl p-6">
                <div className="flex items-center gap-2 mb-4">
                  <Copy className="w-5 h-5 text-primary" />
                  <h2 className="text-xl font-semibold">{t.referrals.yourReferralLink}</h2>
                  <div className="group relative">
                    <Info className="w-4 h-4 text-muted-foreground cursor-help" />
                    <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block bg-popover border border-border rounded-lg p-3 text-sm w-64 shadow-lg z-10">
                      <p>{t.referrals.referralLinkTooltip}</p>
                      <ul className="mt-2 space-y-1">
                        <li>{t.referrals.referralLinkTooltipPurchase}</li>
                        <li>{t.referrals.referralLinkTooltipUpgrade}</li>
                        <li>{t.referrals.referralLinkTooltipClaim}</li>
                      </ul>
                    </div>
                  </div>
                </div>
                
                <div className="flex gap-3">
                  <div className="flex-1 bg-muted rounded-lg p-3 font-mono text-sm break-all">
                    {getReferralLink(publicKey.toString().slice(0, 8).toUpperCase())}
                  </div>
                  <button
                    onClick={handleCopyReferralLink}
                    className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors flex items-center gap-2"
                  >
                    <Copy className="w-4 h-4" />
                    {t.referrals.copy}
                  </button>
                </div>

                <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
                  <Info className="w-4 h-4" />
                  {t.referrals.yourReferralCode} <span className="font-mono font-semibold">
                    {publicKey.toString().slice(0, 8).toUpperCase()}
                  </span>
                </div>
              </div>
            </div>

            {/* Commission Rates */}
            <CommissionRates />

            {/* SOL Balance Section */}
            <SolBalance />

            {/* Stats Grid */}
            <div className="grid md:grid-cols-2 gap-6 mb-8">
              <ReferralStats />
              <PrestigeDisplay />
            </div>

            {/* Referrals List */}
            <ReferralsList />

            {/* How It Works Section */}
            <div className="bg-card border border-border rounded-xl p-6 mt-8">
              <h2 className="text-xl font-semibold mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-primary" />
                {t.referrals.howItWorksTitle}
              </h2>
              
              <div className="grid md:grid-cols-3 gap-6">
                <div className="text-center">
                  <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-3">
                    <Users className="w-6 h-6 text-primary" />
                  </div>
                  <h3 className="font-semibold mb-2">{t.referrals.step1Title}</h3>
                  <p className="text-sm text-muted-foreground">
                    {t.referrals.step1Description}
                  </p>
                </div>

                <div className="text-center">
                  <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-3">
                    <TrendingUp className="w-6 h-6 text-primary" />
                  </div>
                  <h3 className="font-semibold mb-2">{t.referrals.step2Title}</h3>
                  <p className="text-sm text-muted-foreground">
                    {t.referrals.step2Description}
                  </p>
                </div>

                <div className="text-center">
                  <div className="w-12 h-12 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-3">
                    <Award className="w-6 h-6 text-primary" />
                  </div>
                  <h3 className="font-semibold mb-2">{t.referrals.step3Title}</h3>
                  <p className="text-sm text-muted-foreground">
                    {t.referrals.step3Description}
                  </p>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
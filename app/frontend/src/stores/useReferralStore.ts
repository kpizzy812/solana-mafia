/**
 * Zustand store for referral system with localStorage persistence
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

interface ReferralState {
  // Current referral code (from URL or localStorage)
  referralCode: string | null;
  
  // When the code was first set
  referralCodeSetAt: string | null;
  
  // Whether the code has been used for business creation
  referralCodeUsed: boolean;
  
  // Actions
  setReferralCode: (code: string) => void;
  clearReferralCode: () => void;
  markReferralCodeAsUsed: () => void;
  processUrlReferralCode: () => string | null;
  getReferralLinkForCode: (code: string) => string;
}

export const useReferralStore = create<ReferralState>()(
  persist(
    (set, get) => ({
      // State
      referralCode: null,
      referralCodeSetAt: null,
      referralCodeUsed: false,

      // Actions
      setReferralCode: (code: string) => {
        const currentCode = get().referralCode;
        
        // Only set if we don't have a code or if it's different
        if (!currentCode || currentCode !== code) {
          set({
            referralCode: code,
            referralCodeSetAt: new Date().toISOString(),
            referralCodeUsed: false
          });
          
          console.log('🔗 Referral code set:', code);
        }
      },

      clearReferralCode: () => {
        set({
          referralCode: null,
          referralCodeSetAt: null,
          referralCodeUsed: false
        });
        
        console.log('🗑️ Referral code cleared');
      },

      markReferralCodeAsUsed: () => {
        set({ referralCodeUsed: true });
        console.log('✅ Referral code marked as used');
      },

      processUrlReferralCode: () => {
        // Only run on client side
        if (typeof window === 'undefined') return null;

        try {
          const url = new URL(window.location.href);
          const refCode = url.searchParams.get('ref');
          
          if (refCode) {
            // Set the referral code
            get().setReferralCode(refCode);
            
            // Clean URL (remove ref parameter)
            url.searchParams.delete('ref');
            const cleanUrl = url.toString();
            
            // Update URL without page reload
            window.history.replaceState({}, '', cleanUrl);
            
            console.log('🎯 Processed referral code from URL:', refCode);
            return refCode;
          }
        } catch (error) {
          console.error('❌ Error processing URL referral code:', error);
        }
        
        return null;
      },

      getReferralLinkForCode: (code: string) => {
        if (typeof window === 'undefined') {
          // Use env variable in SSR/build time
          const domain = process.env.NEXT_PUBLIC_APP_DOMAIN || 'http://localhost:3000';
          return `${domain}?ref=${code}`;
        }
        
        // Use current URL in browser
        const baseUrl = `${window.location.protocol}//${window.location.host}`;
        return `${baseUrl}?ref=${code}`;
      }
    }),
    {
      name: 'solana-mafia-referral', // localStorage key
      storage: createJSONStorage(() => localStorage),
      
      // Only persist essential data
      partialize: (state) => ({
        referralCode: state.referralCode,
        referralCodeSetAt: state.referralCodeSetAt,
        referralCodeUsed: state.referralCodeUsed
      }),
      
      // Version for handling future migrations
      version: 1,
      
      // Migration function for future versions
      migrate: (persistedState: any, version: number) => {
        if (version === 0) {
          // Migration from version 0 to 1 (if needed)
          return {
            ...persistedState,
            referralCodeUsed: false
          };
        }
        return persistedState as ReferralState;
      }
    }
  )
);

// Helper hooks
export const useReferralCode = () => {
  const store = useReferralStore();
  return {
    code: store.referralCode,
    isUsed: store.referralCodeUsed,
    setAt: store.referralCodeSetAt,
    hasCode: !!store.referralCode && !store.referralCodeUsed
  };
};

export const useReferralActions = () => {
  const store = useReferralStore();
  return {
    setCode: store.setReferralCode,
    clearCode: store.clearReferralCode,
    markAsUsed: store.markReferralCodeAsUsed,
    processUrl: store.processUrlReferralCode,
    getReferralLink: store.getReferralLinkForCode
  };
};
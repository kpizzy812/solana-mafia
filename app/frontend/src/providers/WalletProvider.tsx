'use client';

import React, { useMemo, useEffect } from 'react';
import {
  ConnectionProvider,
  WalletProvider as SolanaWalletProvider,
  useWallet,
} from '@solana/wallet-adapter-react';
import { WalletAdapterNetwork } from '@solana/wallet-adapter-base';
import {
  WalletModalProvider,
} from '@solana/wallet-adapter-react-ui';
import { clusterApiUrl } from '@solana/web3.js';
import {
  PhantomWalletAdapter,
  SolflareWalletAdapter,
  TrustWalletAdapter,
} from '@solana/wallet-adapter-wallets';
import '@solana/wallet-adapter-react-ui/styles.css';
import toast from 'react-hot-toast';

interface WalletProviderProps {
  children: React.ReactNode;
}

// Inner component to track wallet events
const WalletEventTracker: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { connected, publicKey, wallet } = useWallet();

  useEffect(() => {
    if (connected && publicKey && wallet) {
      toast.success(`Connected to ${wallet.adapter.name}`, {
        duration: 2000,
      });
    }
  }, [connected, publicKey, wallet]);

  useEffect(() => {
    if (!connected && !publicKey) {
      // Only show disconnect message if wallet was previously connected
      const wasConnected = localStorage.getItem('walletWasConnected');
      if (wasConnected === 'true') {
        toast('Wallet disconnected', {
          duration: 2000,
        });
        localStorage.removeItem('walletWasConnected');
      }
    } else if (connected) {
      localStorage.setItem('walletWasConnected', 'true');
    }
  }, [connected, publicKey]);

  return <>{children}</>;
};

export const WalletProvider: React.FC<WalletProviderProps> = ({ children }) => {
  // The network can be set to 'devnet', 'testnet', or 'mainnet-beta'.
  const network = WalletAdapterNetwork.Devnet;

  // You can also provide a custom RPC endpoint.
  const endpoint = useMemo(() => clusterApiUrl(network), [network]);

  const wallets = useMemo(
    () => [
      new PhantomWalletAdapter(),
      new SolflareWalletAdapter({ network }),
      new TrustWalletAdapter(),
      /**
       * Wallets that implement either of these standards will be available automatically.
       *
       *   - Solana Mobile Stack Mobile Wallet Adapter Protocol
       *     (https://github.com/solana-mobile/mobile-wallet-adapter)
       *   - Solana Wallet Standard
       *     (https://github.com/anza-xyz/wallet-standard)
       */
    ],
    [network]
  );

  return (
    <ConnectionProvider endpoint={endpoint}>
      <SolanaWalletProvider wallets={wallets} autoConnect>
        <WalletModalProvider>
          <WalletEventTracker>
            {children}
          </WalletEventTracker>
        </WalletModalProvider>
      </SolanaWalletProvider>
    </ConnectionProvider>
  );
};
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
  const { connected, publicKey, wallet, connecting, disconnecting, select } = useWallet();

  useEffect(() => {
    console.log('🔍 WALLET STATE CHANGE:', {
      connected,
      connecting,
      disconnecting,
      publicKey: publicKey?.toString(),
      walletName: wallet?.adapter.name,
      timestamp: new Date().toISOString()
    });
  }, [connected, connecting, disconnecting, publicKey, wallet]);

  useEffect(() => {
    if (connected && publicKey && wallet) {
      console.log('✅ WALLET CONNECTED SUCCESSFULLY:', {
        name: wallet.adapter.name,
        publicKey: publicKey.toString(),
        timestamp: new Date().toISOString()
      });
      toast.success(`Connected to ${wallet.adapter.name}`, {
        duration: 2000,
      });
    }
  }, [connected, publicKey, wallet]);

  useEffect(() => {
    if (connecting) {
      console.log('🔄 WALLET CONNECTING...', {
        walletName: wallet?.adapter.name,
        timestamp: new Date().toISOString()
      });
    }
  }, [connecting, wallet]);

  useEffect(() => {
    if (!connected && !publicKey) {
      // Only show disconnect message if wallet was previously connected
      const wasConnected = localStorage.getItem('walletWasConnected');
      if (wasConnected === 'true') {
        console.log('🔌 WALLET DISCONNECTED');
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

  // Use custom RPC endpoint from environment variables
  const endpoint = useMemo(() => {
    const customEndpoint = process.env.NEXT_PUBLIC_SOLANA_RPC_URL;
    const fallback = clusterApiUrl(network);
    
    console.log('🔗 RPC ENDPOINT DEBUG:', {
      customEndpoint,
      network,
      fallback,
      willUse: customEndpoint || fallback,
      env: {
        NEXT_PUBLIC_SOLANA_RPC_URL: process.env.NEXT_PUBLIC_SOLANA_RPC_URL,
        NODE_ENV: process.env.NODE_ENV
      }
    });
    
    const finalEndpoint = customEndpoint || fallback;
    console.log('🎯 FINAL RPC ENDPOINT:', finalEndpoint);
    
    return finalEndpoint;
  }, [network]);

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
'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useWalletMultiButton } from '@solana/wallet-adapter-base-ui';
import { WalletName } from '@solana/wallet-adapter-base';
import type { Wallet } from '@solana/wallet-adapter-base';
import { cn } from '@/lib/utils';
import { Portal } from '@/components/ui/Portal';
import { Copy, LogOut, Check } from 'lucide-react';
import { useTranslation } from '@/locales';
import toast from 'react-hot-toast';

interface WalletModalProps {
  wallets: Wallet[];
  onSelectWallet: (walletName: WalletName) => void;
  onClose: () => void;
}

interface WalletMenuProps {
  walletAddress: string;
  onDisconnect: () => void;
  onClose: () => void;
  language: 'en' | 'ru';
}

const WalletModal: React.FC<WalletModalProps> = ({ wallets, onSelectWallet, onClose }) => {
  React.useEffect(() => {
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'unset';
    };
  }, []);

  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  return (
    <Portal>
      <div 
        className="fixed top-0 left-0 right-0 bottom-0 bg-black/80 flex items-center justify-center p-4 z-[9999]" 
        onClick={handleBackdropClick}
      >
        <div 
          className="bg-popover border border-border rounded-xl p-6 w-full max-w-sm max-h-[80vh] overflow-y-auto relative"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-popover-foreground">Connect Wallet</h2>
            <button
              onClick={onClose}
              className="text-muted-foreground hover:text-popover-foreground text-2xl leading-none w-8 h-8 flex items-center justify-center rounded-lg hover:bg-accent transition-colors"
              aria-label="Close"
            >
              ×
            </button>
          </div>
          <div className="space-y-3">
            {wallets.map((wallet) => (
              <button
                key={wallet.adapter.name}
                onClick={() => {
                  onSelectWallet(wallet.adapter.name);
                  onClose();
                }}
                className="w-full flex items-center gap-3 p-4 rounded-lg bg-card hover:bg-accent transition-colors text-card-foreground border border-border hover:border-accent"
              >
                <img
                  src={wallet.adapter.icon}
                  alt={wallet.adapter.name}
                  className="w-8 h-8 rounded-lg"
                />
                <span className="font-medium text-left">{wallet.adapter.name}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </Portal>
  );
};

const WalletMenu: React.FC<WalletMenuProps> = ({ walletAddress, onDisconnect, onClose, language }) => {
  const [copySuccess, setCopySuccess] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const t = useTranslation(language);

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [onClose]);

  const handleCopyAddress = async () => {
    try {
      await navigator.clipboard.writeText(walletAddress);
      setCopySuccess(true);
      toast.success(t.walletMenu.copied, { duration: 2000 });
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error('Failed to copy address:', err);
      // Fallback for devices that don't support clipboard API
      try {
        const textArea = document.createElement('textarea');
        textArea.value = walletAddress;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        setCopySuccess(true);
        toast.success(t.walletMenu.copied, { duration: 2000 });
        setTimeout(() => setCopySuccess(false), 2000);
      } catch (fallbackErr) {
        console.error('Fallback copy failed:', fallbackErr);
        toast.error('Failed to copy address');
      }
    }
  };

  const handleDisconnect = () => {
    onDisconnect();
    onClose();
  };

  return (
    <Portal>
      <div className="fixed top-0 left-0 right-0 bottom-0 z-[9999]">
        <div 
          ref={menuRef}
          className="absolute top-16 right-4 bg-popover border border-border rounded-lg shadow-lg p-3 min-w-[280px]"
        >
          {/* Full Address */}
          <div className="mb-3">
            <div className="text-xs text-muted-foreground mb-1">{t.walletMenu.fullAddress}:</div>
            <div className="text-sm font-mono text-card-foreground break-all bg-muted rounded px-2 py-1">
              {walletAddress}
            </div>
          </div>

          {/* Action buttons */}
          <div className="space-y-2">
            <button
              onClick={handleCopyAddress}
              className={cn(
                "w-full flex items-center gap-2 px-3 py-2 rounded-lg transition-colors text-sm",
                copySuccess 
                  ? "bg-green-500/20 text-green-600 cursor-default" 
                  : "bg-card hover:bg-accent text-card-foreground"
              )}
              disabled={copySuccess}
            >
              {copySuccess ? (
                <Check className="w-4 h-4" />
              ) : (
                <Copy className="w-4 h-4" />
              )}
              <span>{copySuccess ? t.walletMenu.copied : t.walletMenu.copyAddress}</span>
            </button>
            
            <button
              onClick={handleDisconnect}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-destructive hover:bg-destructive/90 transition-colors text-destructive-foreground text-sm"
            >
              <LogOut className="w-4 h-4" />
              <span>{t.walletMenu.disconnect}</span>
            </button>
          </div>
        </div>
      </div>
    </Portal>
  );
};

interface WalletButtonProps {
  language?: 'en' | 'ru';
}

export const WalletButton: React.FC<WalletButtonProps> = ({ language = 'en' }) => {
  const [walletModalConfig, setWalletModalConfig] = useState<{
    onSelectWallet: (walletName: WalletName) => void;
    wallets: Wallet[];
  } | null>(null);
  const [walletMenuOpen, setWalletMenuOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [windowWidth, setWindowWidth] = useState<number>(0);

  useEffect(() => {
    setMounted(true);
    
    // Set initial width and add resize listener
    const updateWidth = () => {
      setWindowWidth(window.innerWidth);
    };
    
    updateWidth();
    window.addEventListener('resize', updateWidth);
    
    return () => {
      window.removeEventListener('resize', updateWidth);
    };
  }, []);

  const { buttonState, onConnect, onDisconnect, onSelectWallet, publicKey, walletName } = 
    useWalletMultiButton({
      onSelectWallet: setWalletModalConfig,
    });

  // Format wallet address based on screen size
  const formatWalletAddress = (address: string) => {
    if (windowWidth < 400) {
      // Very small screens - show 3+3 chars
      return `${address.slice(0, 3)}...${address.slice(-3)}`;
    } else if (windowWidth < 500) {
      // Small screens - show 4+3 chars
      return `${address.slice(0, 4)}...${address.slice(-3)}`;
    } else if (windowWidth < 600) {
      // Medium-small screens - show 4+4 chars
      return `${address.slice(0, 4)}...${address.slice(-4)}`;
    } else {
      // Large screens - show 5+4 chars
      return `${address.slice(0, 5)}...${address.slice(-4)}`;
    }
  };

  // Prevent hydration mismatch by not rendering dynamic content on server
  if (!mounted) {
    return (
      <button
        className="px-3 py-2 rounded-lg font-medium text-sm bg-primary hover:bg-primary/90 text-primary-foreground min-w-0 flex-shrink-0 h-[40px]"
        disabled
      >
        <span className="truncate">Connect Wallet</span>
      </button>
    );
  }

  let label: string;
  let className: string;
  let disabled = false;

  switch (buttonState) {
    case 'connected':
      label = publicKey ? formatWalletAddress(publicKey.toBase58()) : 'Connected';
      className = 'bg-success hover:bg-success/90 text-white';
      break;
    case 'connecting':
      label = 'Connecting...';
      className = 'bg-info text-white cursor-not-allowed';
      disabled = true;
      break;
    case 'disconnecting':
      label = 'Disconnecting...';
      className = 'bg-destructive text-white cursor-not-allowed';
      disabled = true;
      break;
    case 'has-wallet':
      label = `Connect ${walletName}`;
      className = 'bg-primary hover:bg-primary/90 text-primary-foreground';
      break;
    case 'no-wallet':
      label = 'Connect Wallet';
      className = 'bg-primary hover:bg-primary/90 text-primary-foreground';
      break;
    default:
      label = 'Connect Wallet';
      className = 'bg-primary hover:bg-primary/90 text-primary-foreground';
  }

  const handleClick = () => {
    switch (buttonState) {
      case 'connected':
        setWalletMenuOpen(true);
        break;
      case 'connecting':
      case 'disconnecting':
        break;
      case 'has-wallet':
        onConnect?.();
        break;
      case 'no-wallet':
        onSelectWallet?.();
        break;
    }
  };

  return (
    <>
      <button
        onClick={handleClick}
        disabled={disabled}
        className={cn(
          'px-3 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 text-sm min-w-0 h-[40px]',
          className
        )}
      >
        <span className="truncate block">{label}</span>
      </button>
      
      {walletModalConfig && (
        <WalletModal
          wallets={walletModalConfig.wallets}
          onSelectWallet={walletModalConfig.onSelectWallet}
          onClose={() => setWalletModalConfig(null)}
        />
      )}

      {walletMenuOpen && publicKey && (
        <WalletMenu
          walletAddress={publicKey.toBase58()}
          onDisconnect={() => onDisconnect?.()}
          onClose={() => setWalletMenuOpen(false)}
          language={language}
        />
      )}
    </>
  );
};
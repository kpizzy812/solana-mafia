'use client';

import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { Button } from '@/components/ui/Button';
import { DollarSign, Download, X, Wallet, AlertTriangle, Minus } from 'lucide-react';
import { useTranslation } from '@/locales';
import { cn } from '@/lib/utils';
import toast from 'react-hot-toast';

interface WithdrawModalProps {
  isOpen: boolean;
  onClose: () => void;
  onWithdraw: () => Promise<void>; // No amount parameter - contract determines amount
  availableBalance: number; // in SOL
  language?: 'en' | 'ru';
}

export const WithdrawModal: React.FC<WithdrawModalProps> = ({
  isOpen,
  onClose,
  onWithdraw,
  availableBalance = 0,
  language = 'en'
}) => {
  const [isWithdrawing, setIsWithdrawing] = useState(false);

  const t = useTranslation(language);

  // Smart balance formatting (same as Header)
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

  // Fixed claim fee from smart contract (0.01 SOL)
  const claimFee = 0.01;
  const claimableAmount = availableBalance; // Full pending balance is claimable
  const netReceived = Math.max(0, claimableAmount - claimFee);
  const hasInsufficientBalance = availableBalance <= 0; // Only need some earnings to claim
  const canWithdraw = availableBalance > 0 && !hasInsufficientBalance;

  const handleWithdraw = async () => {
    if (!canWithdraw || isWithdrawing) return;
    
    setIsWithdrawing(true);
    try {
      await onWithdraw(); // No amount parameter - contract determines amount
      toast.success(
        language === 'ru' 
          ? `Выведено ${formatBalance(netReceived)} SOL (комиссия ${claimFee} SOL)`
          : `Withdrawn ${formatBalance(netReceived)} SOL (fee ${claimFee} SOL)`
      );
      onClose();
    } catch (error) {
      console.error('Withdrawal failed:', error);
      toast.error(
        language === 'ru' 
          ? 'Ошибка при выводе средств'
          : 'Failed to withdraw funds'
      );
    } finally {
      setIsWithdrawing(false);
    }
  };

  const handleBackdropClick = (e: React.MouseEvent) => {
    // Only close if the click was on the backdrop itself, not on its children
    if (e.target === e.currentTarget) {
      onClose();
    }
  };

  const texts = {
    en: {
      title: 'Claim Earnings',
      availableBalance: 'Pending Earnings',
      claimableAmount: 'Total Claimable',
      claimFee: 'Claim Fee',
      youWillReceive: 'You Will Receive',
      claim: 'Claim Earnings',
      claiming: 'Claiming...',
      cancel: 'Cancel',
      insufficientBalance: 'Insufficient Balance',
      feeDescription: 'A fixed 0.01 SOL fee is charged for each claim to cover transaction costs.',
      warningTitle: 'Important',
      warningText: 'Make sure you have enough SOL in your wallet to pay for transaction fees (~0.0001 SOL).',
      insufficientBalanceForClaim: 'You need earnings to claim',
      minimumRequired: 'No Earnings Available'
    },
    ru: {
      title: 'Клэйм доходов',
      availableBalance: 'Ожидающие доходы',
      claimableAmount: 'Всего к клэйму',
      claimFee: 'Комиссия клэйма',
      youWillReceive: 'Вы получите',
      claim: 'Заклэймить',
      claiming: 'Клэйм...',
      cancel: 'Отмена',
      insufficientBalance: 'Недостаточно средств',
      feeDescription: 'Фиксированная комиссия 0.01 SOL взимается с каждого клэйма для покрытия транзакционных расходов.',
      warningTitle: 'Важно',
      warningText: 'Убедитесь, что у вас достаточно SOL в кошельке для оплаты комиссии транзакции (~0.0001 SOL).',
      insufficientBalanceForClaim: 'Нужны доходы для клэйма',
      minimumRequired: 'Нет доходов'
    }
  };

  const text = texts[language];

  // Don't render anything if not open or if we're on the server
  if (!isOpen || typeof document === 'undefined') {
    return null;
  }

  const modalContent = (
    <div 
      className={cn(
        'fixed inset-0 z-[9999] flex items-center justify-center p-4',
        'bg-black/60 backdrop-blur-sm transition-all',
        isOpen ? 'visible opacity-100' : 'invisible opacity-0'
      )}
      onClick={handleBackdropClick}
    >
      {/* Modal */}
      <div className={cn(
        'relative bg-card rounded-xl shadow-2xl border border-border w-full max-w-md',
        'max-h-[80vh] overflow-y-auto transition-all my-2',
        isOpen ? 'scale-100 opacity-100' : 'scale-95 opacity-0'
      )}
      onClick={(e) => e.stopPropagation()} // Prevent closing when clicking inside modal
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border">
          <h2 className="text-lg font-semibold text-card-foreground flex items-center gap-2">
            <Download className="w-5 h-5 text-green-500" />
            {text.title}
          </h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-muted transition-colors"
          >
            <X className="w-5 h-5 text-muted-foreground" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6 space-y-4">
          {/* Available Balance */}
          <div className={cn(
            "rounded-lg p-3",
            hasInsufficientBalance 
              ? "bg-red-500/10 border border-red-500/20" 
              : "bg-green-500/10"
          )}>
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Wallet className={cn(
                  "w-4 h-4",
                  hasInsufficientBalance ? "text-red-500" : "text-green-500"
                )} />
                <span className="text-sm text-muted-foreground">{text.availableBalance}</span>
              </div>
              <span className={cn(
                "text-sm font-bold",
                hasInsufficientBalance ? "text-red-500" : "text-green-500"
              )}>
                {formatBalance(availableBalance)} SOL
              </span>
            </div>
            {hasInsufficientBalance && (
              <div className="mt-2 text-xs text-red-600">
                {text.insufficientBalanceForClaim}
              </div>
            )}
          </div>

          {/* Automatic Claim Calculation */}
          {availableBalance > 0 && (
            <div className="space-y-2">
              {/* Total Claimable */}
              <div className="bg-blue-500/10 rounded-lg p-3">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <DollarSign className="w-4 h-4 text-blue-500" />
                    <span className="text-sm text-muted-foreground">{text.claimableAmount}</span>
                  </div>
                  <span className="text-sm font-bold text-blue-500">
                    {formatBalance(claimableAmount)} SOL
                  </span>
                </div>
              </div>

              {/* Claim Fee */}
              <div className="bg-orange-500/10 rounded-lg p-3">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <Minus className="w-4 h-4 text-orange-500" />
                    <span className="text-sm text-muted-foreground">{text.claimFee}</span>
                  </div>
                  <span className="text-sm font-bold text-orange-500">
                    -{claimFee} SOL
                  </span>
                </div>
              </div>

              {/* You Will Receive */}
              <div className="bg-green-500/10 rounded-lg p-3">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <Download className="w-4 h-4 text-green-500" />
                    <span className="text-sm text-muted-foreground">{text.youWillReceive}</span>
                  </div>
                  <span className="text-lg font-bold text-green-500">
                    {formatBalance(netReceived)} SOL
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Fee Description */}
          <div className="bg-muted/50 rounded-lg p-3">
            <div className="text-xs text-muted-foreground">
              {text.feeDescription}
            </div>
          </div>

          {/* Warning */}
          <div className="bg-yellow-500/10 border border-yellow-500/20 rounded-lg p-3">
            <div className="flex items-center gap-2 text-yellow-600 mb-1">
              <AlertTriangle className="w-4 h-4" />
              <span className="font-medium text-sm">{text.warningTitle}</span>
            </div>
            <p className="text-xs text-yellow-600/80">
              {text.warningText}
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <Button
              onClick={onClose}
              variant="secondary"
              className="flex-1"
              disabled={isWithdrawing}
            >
              {text.cancel}
            </Button>
            
            <Button
              onClick={handleWithdraw}
              variant="primary"
              className="flex-1"
              disabled={!canWithdraw || isWithdrawing || hasInsufficientBalance}
            >
              {isWithdrawing ? text.claiming :
               hasInsufficientBalance ? text.minimumRequired :
               !canWithdraw ? text.insufficientBalance :
               availableBalance <= 0 ? text.minimumRequired :
               `${text.claim} ${formatBalance(netReceived)} SOL`}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );

  return createPortal(modalContent, document.body);
};
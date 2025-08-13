/**
 * SolBalance - Display and manage SOL commission balance
 */

'use client';

import React, { useState, useEffect } from 'react';
import { Wallet, ArrowUpRight, History, Info, Loader2, AlertCircle, CheckCircle, DollarSign } from 'lucide-react';
import { useWallet } from '@solana/wallet-adapter-react';
import toast from 'react-hot-toast';
import { apiClient } from '@/lib/api';

interface SolBalanceData {
  balance_lamports: number;
  balance_sol: number;
  total_withdrawn_lamports: number;
  total_withdrawn_sol: number;
  last_withdrawal_at: string | null;
  available_for_withdrawal: boolean;
}

interface WithdrawalHistory {
  id: number;
  amount_sol: number;
  amount_lamports: number;
  status: 'pending' | 'completed' | 'failed';
  transaction_signature: string | null;
  requested_at: string;
  processed_at: string | null;
  error_message: string | null;
}

export function SolBalance() {
  const { publicKey } = useWallet();
  const [balance, setBalance] = useState<SolBalanceData | null>(null);
  const [withdrawalHistory, setWithdrawalHistory] = useState<WithdrawalHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [withdrawing, setWithdrawing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [withdrawalAmount, setWithdrawalAmount] = useState('');
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    const fetchBalance = async () => {
      if (!publicKey) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        const [balanceResponse, historyResponse] = await Promise.all([
          apiClient.get(`/referrals/${publicKey.toString()}/sol-balance`),
          apiClient.get(`/referrals/${publicKey.toString()}/withdrawals`)
        ]);
        
        if (balanceResponse.success) {
          setBalance(balanceResponse);
        }
        
        if (historyResponse.success) {
          setWithdrawalHistory(historyResponse.withdrawals || []);
        }
      } catch (err) {
        console.error('Failed to fetch SOL balance:', err);
        setError('Failed to load SOL balance');
      } finally {
        setLoading(false);
      }
    };

    fetchBalance();
    
    // Refresh balance every 30 seconds
    const interval = setInterval(fetchBalance, 30000);
    return () => clearInterval(interval);
  }, [publicKey]);

  const handleWithdraw = async () => {
    if (!publicKey || !withdrawalAmount) return;

    const amount = parseFloat(withdrawalAmount);
    if (isNaN(amount) || amount <= 0) {
      toast.error('Please enter a valid amount');
      return;
    }

    if (!balance || amount > balance.balance_sol) {
      toast.error('Insufficient balance');
      return;
    }

    try {
      setWithdrawing(true);
      
      const response = await apiClient.post(
        `/referrals/${publicKey.toString()}/sol-withdraw?amount_sol=${amount}`
      );
      
      if (response.success) {
        toast.success(`Withdrawal request submitted: ${amount} SOL`, {
          icon: <CheckCircle className="w-4 h-4 text-green-500" />
        });
        
        setWithdrawalAmount('');
        
        // Refresh balance and history
        const [balanceResponse, historyResponse] = await Promise.all([
          apiClient.get(`/referrals/${publicKey.toString()}/sol-balance`),
          apiClient.get(`/referrals/${publicKey.toString()}/withdrawals`)
        ]);
        
        if (balanceResponse.success) setBalance(balanceResponse);
        if (historyResponse.success) setWithdrawalHistory(historyResponse.withdrawals || []);
      } else {
        toast.error('Failed to submit withdrawal request');
      }
    } catch (err) {
      console.error('Withdrawal failed:', err);
      toast.error('Failed to submit withdrawal request');
    } finally {
      setWithdrawing(false);
    }
  };

  const formatSOL = (lamports: number) => {
    return (lamports / 1_000_000_000).toFixed(4);
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-500';
      case 'pending':
        return 'text-yellow-500';
      case 'failed':
        return 'text-red-500';
      default:
        return 'text-muted-foreground';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-500" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return null;
    }
  };

  if (loading) {
    return (
      <div className="bg-card border border-border rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Wallet className="w-5 h-5 text-primary" />
          <h2 className="text-xl font-semibold">SOL Commission Balance</h2>
        </div>
        
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-card border border-border rounded-xl p-6">
        <div className="flex items-center gap-2 mb-4">
          <Wallet className="w-5 h-5 text-primary" />
          <h2 className="text-xl font-semibold">SOL Commission Balance</h2>
        </div>
        
        <div className="text-center py-8">
          <p className="text-muted-foreground">{error}</p>
        </div>
      </div>
    );
  }

  const displayBalance = balance || {
    balance_lamports: 0,
    balance_sol: 0,
    total_withdrawn_lamports: 0,
    total_withdrawn_sol: 0,
    last_withdrawal_at: null,
    available_for_withdrawal: false
  };

  return (
    <div className="bg-card border border-border rounded-xl p-6">
      <div className="flex items-center gap-2 mb-6">
        <Wallet className="w-5 h-5 text-primary" />
        <h2 className="text-xl font-semibold">SOL Commission Balance</h2>
        <div className="group relative">
          <Info className="w-4 h-4 text-muted-foreground cursor-help" />
          <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block bg-popover border border-border rounded-lg p-3 text-sm w-64 shadow-lg z-10">
            <p>Commissions are automatically added to your SOL balance when your referrals claim earnings.</p>
            <p className="mt-2">Withdrawals are processed automatically by admin within a few minutes.</p>
          </div>
        </div>
      </div>

      {/* Current Balance */}
      <div className="bg-primary/10 border border-primary/20 rounded-lg p-6 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground mb-1">Available Balance</p>
            <p className="text-3xl font-bold text-primary">
              {displayBalance.balance_sol.toFixed(4)} SOL
            </p>
            <p className="text-xs text-muted-foreground">
              {displayBalance.balance_lamports.toLocaleString()} lamports
            </p>
          </div>
          
          <div className="text-right">
            <p className="text-sm text-muted-foreground mb-1">Total Withdrawn</p>
            <p className="text-lg font-semibold">
              {displayBalance.total_withdrawn_sol.toFixed(4)} SOL
            </p>
          </div>
        </div>
      </div>

      {/* Withdrawal Form */}
      <div className="space-y-4 mb-6">
        <h3 className="text-lg font-semibold">Withdraw SOL</h3>
        
        <div className="flex gap-3">
          <div className="flex-1">
            <input
              type="number"
              step="0.0001"
              min="0.001"
              max={displayBalance.balance_sol}
              value={withdrawalAmount}
              onChange={(e) => setWithdrawalAmount(e.target.value)}
              placeholder="Amount in SOL (min: 0.001)"
              className="w-full px-3 py-2 bg-muted border border-border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent"
              disabled={!displayBalance.available_for_withdrawal || withdrawing}
            />
          </div>
          
          <button
            onClick={handleWithdraw}
            disabled={!displayBalance.available_for_withdrawal || withdrawing || !withdrawalAmount}
            className="px-6 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {withdrawing ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <ArrowUpRight className="w-4 h-4" />
            )}
            {withdrawing ? 'Processing...' : 'Withdraw'}
          </button>
        </div>

        {displayBalance.balance_sol > 0 && (
          <div className="flex gap-2">
            <button
              onClick={() => setWithdrawalAmount((displayBalance.balance_sol * 0.25).toFixed(4))}
              className="px-3 py-1 text-xs bg-muted text-muted-foreground rounded hover:bg-muted/80"
            >
              25%
            </button>
            <button
              onClick={() => setWithdrawalAmount((displayBalance.balance_sol * 0.5).toFixed(4))}
              className="px-3 py-1 text-xs bg-muted text-muted-foreground rounded hover:bg-muted/80"
            >
              50%
            </button>
            <button
              onClick={() => setWithdrawalAmount((displayBalance.balance_sol * 0.75).toFixed(4))}
              className="px-3 py-1 text-xs bg-muted text-muted-foreground rounded hover:bg-muted/80"
            >
              75%
            </button>
            <button
              onClick={() => setWithdrawalAmount(displayBalance.balance_sol.toFixed(4))}
              className="px-3 py-1 text-xs bg-muted text-muted-foreground rounded hover:bg-muted/80"
            >
              Max
            </button>
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          Minimum withdrawal: 0.001 SOL. Withdrawals are processed automatically within a few minutes.
        </p>
      </div>

      {/* Withdrawal History Toggle */}
      <div className="border-t border-border pt-4">
        <button
          onClick={() => setShowHistory(!showHistory)}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          <History className="w-4 h-4" />
          Withdrawal History ({withdrawalHistory.length})
        </button>

        {showHistory && withdrawalHistory.length > 0 && (
          <div className="mt-4 space-y-2 max-h-60 overflow-y-auto">
            {withdrawalHistory.map((withdrawal) => (
              <div
                key={withdrawal.id}
                className="flex items-center justify-between p-3 bg-muted rounded-lg"
              >
                <div className="flex items-center gap-3">
                  {getStatusIcon(withdrawal.status)}
                  <div>
                    <p className="text-sm font-medium">
                      {withdrawal.amount_sol.toFixed(4)} SOL
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(withdrawal.requested_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
                
                <div className="text-right">
                  <p className={`text-sm font-medium ${getStatusColor(withdrawal.status)}`}>
                    {withdrawal.status}
                  </p>
                  {withdrawal.transaction_signature && (
                    <a
                      href={`https://explorer.solana.com/tx/${withdrawal.transaction_signature}?cluster=devnet`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-xs text-primary hover:underline"
                    >
                      View Transaction
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {showHistory && withdrawalHistory.length === 0 && (
          <p className="text-sm text-muted-foreground mt-4">No withdrawal history yet.</p>
        )}
      </div>

      {/* Last Withdrawal Info */}
      {displayBalance.last_withdrawal_at && (
        <div className="mt-4 text-xs text-muted-foreground text-center">
          Last withdrawal: {new Date(displayBalance.last_withdrawal_at).toLocaleString()}
        </div>
      )}
    </div>
  );
}
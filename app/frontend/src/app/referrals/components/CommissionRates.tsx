/**
 * CommissionRates - Display the current commission rates
 */

'use client';

import React from 'react';
import { Percent, Info, TrendingDown } from 'lucide-react';

const commissionLevels = [
  {
    level: 1,
    rate: 10,
    description: 'Direct referrals',
    color: 'text-green-500',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/20'
  },
  {
    level: 2,
    rate: 5,
    description: 'Referrals of referrals',
    color: 'text-blue-500',
    bgColor: 'bg-blue-500/10',
    borderColor: 'border-blue-500/20'
  },
  {
    level: 3,
    rate: 2.5,
    description: 'Third level referrals',
    color: 'text-purple-500',
    bgColor: 'bg-purple-500/10',
    borderColor: 'border-purple-500/20'
  }
];

export function CommissionRates() {
  return (
    <div className="bg-card border border-border rounded-xl p-4 mb-6">
      <div className="flex items-center gap-2 mb-4">
        <Percent className="w-4 h-4 text-primary" />
        <h2 className="text-lg font-semibold">Commission Rates</h2>
        <div className="group relative">
          <Info className="w-4 h-4 text-muted-foreground cursor-help" />
          <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block bg-popover border border-border rounded-lg p-3 text-sm w-72 shadow-lg z-10">
            <p className="font-medium mb-2">You earn commissions when your referrals:</p>
            <ul className="space-y-1 text-xs">
              <li>• Claim earnings from their businesses</li>
              <li>• Purchase new businesses</li>
              <li>• Upgrade existing businesses</li>
            </ul>
            <div className="mt-3 pt-2 border-t border-border">
              <p className="font-medium text-xs mb-1">Prestige Points for Referrals:</p>
              <ul className="space-y-1 text-xs">
                <li>• <span className="font-medium text-green-500">+50 points</span> when someone uses your referral link</li>
                <li>• <span className="font-medium text-blue-500">+25 points</span> when your referral buys their first business</li>
                <li>• <span className="font-medium text-purple-500">+10% of referral's prestige</span> from network bonus</li>
                <li>• <span className="font-medium text-yellow-500">+5 points</span> per business your referrals purchase</li>
              </ul>
            </div>
            <p className="mt-2 text-xs text-muted-foreground">Commissions are paid automatically to your SOL balance.</p>
          </div>
        </div>
      </div>

      <div className="grid md:grid-cols-3 gap-3">
        {commissionLevels.map((level) => (
          <div 
            key={level.level}
            className={`${level.bgColor} border ${level.borderColor} rounded-lg p-3`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 ${level.color.replace('text-', 'bg-')} rounded-full`}></div>
                <span className="text-sm font-semibold">Level {level.level}</span>
              </div>
              <div className={`text-xl font-bold ${level.color}`}>
                {level.rate}%
              </div>
            </div>
            
            <p className="text-xs text-muted-foreground mb-1">
              {level.description}
            </p>
            
            <div className="text-xs text-muted-foreground">
              On all earnings claims
            </div>
          </div>
        ))}
      </div>

      {/* Example Calculation */}
      <div className="mt-4 p-3 bg-muted rounded-lg">
        <div className="flex items-center gap-2 mb-2">
          <TrendingDown className="w-3 h-3 text-muted-foreground" />
          <span className="font-medium text-xs">Example</span>
        </div>
        
        <div className="text-xs space-y-1">
          <p>If your Level 1 referral claims <span className="font-semibold">1 SOL</span>:</p>
          <p>• You earn: <span className="font-semibold text-green-500">0.1 SOL</span> (10% commission)</p>
          <p className="text-xs text-muted-foreground mt-1">
            Auto-added to your SOL balance
          </p>
        </div>
      </div>
    </div>
  );
}
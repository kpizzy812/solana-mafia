export const en = {
  // Main page
  welcome: 'Welcome to Solana Mafia',
  totalEarnings: 'Total Earnings',
  businesses: 'Businesses', 
  businessSlots: 'Business Slots',
  buyBusiness: 'Buy Business',
  myBusinesses: 'My Businesses',
  noBusinesses: 'No businesses yet',
  noBusinessesDesc: 'Buy your first business to start earning income from your criminal family activities',
  getStarted: 'Get Started',
  connectWalletFirst: 'Connect your wallet to start playing',
  swipeToExplore: 'Swipe to explore',
  availableSlots: 'Available slots',
  dashboard: 'Dashboard',
  loading: 'Loading...',
  error: 'Error loading data',
  retry: 'Retry',
  earningsBalance: 'Earnings Balance',
  walletBalance: 'Wallet Balance',
  withdraw: 'Withdraw',
  prestigeLevel: 'Prestige Level',
  prestigePoints: 'Prestige Points',

  // Purchase modal
  title: 'Purchase Business',
  businessType: 'Business Type',
  level: 'Choose your business level',
  slot: 'Slot',
  price: 'Price',
  dailyYield: 'Daily Yield',
  dailyReturn: 'Daily Return',
  payback: 'Payback Period',
  days: 'days',
  balance: 'Balance',
  insufficient: 'Insufficient Balance',
  purchase: 'Purchase Business',
  purchasing: 'Purchasing...',
  cancel: 'Cancel',
  slotLocked: 'Slot Locked',
  slotOccupied: 'Slot Occupied',
  occupied: 'Occupied',
  locked: 'Locked',
  selectSlot: 'Select Slot',
  businessDetails: 'Business Details',
  profitability: 'Profitability',
  sellingFees: 'Selling Fees',
  earlyExit: 'Early exit penalty',
  holdingPeriod: 'Holding period affects selling fees',
  day: 'Day',
  fee: 'Fee',
  entryFee: 'Entry Fee',
  newPlayerFee: 'New Player Entry Fee',
  totalCost: 'Total Cost',

  // Tooltips
  tooltips: {
    // Main page tooltips
    totalEarningsHelp: {
      title: 'Total Earnings Explained',
      content: 'This shows all SOL you have earned from your businesses since you started playing. It includes both claimed and unclaimed earnings from all your active businesses.'
    },
    businessCountHelp: {
      title: 'Active Businesses',
      content: 'Number of businesses you currently own. Each business generates passive income based on its type, level, and the slot it\'s placed in.'
    },
    businessSlotsHelp: {
      title: 'Business Slots System',
      content: 'You have 9 total slots available: 6 regular slots and 3 premium slots. Regular slots include 3 free basic slots and 3 unlockable slots (cost 10% of business price). Premium slots offer yield bonuses and selling fee discounts.'
    },
    walletBalanceHelp: {
      title: 'Wallet Balance',
      content: 'Your current SOL balance in the connected wallet. This is the money available to purchase new businesses, upgrade existing ones, or unlock premium slots.'
    },
    earningsBalanceHelp: {
      title: 'Claimable Earnings',
      content: 'SOL earnings from your businesses that are ready to be claimed. Note: There\'s a 3% fee when claiming earnings that goes to the development team.'
    },

    // Purchase modal tooltips
    slotSelection: {
      title: 'What are slots?',
      content: 'Slots are places where your businesses are located. Different slots provide different yield bonuses and selling fee discounts.',
      basicSlots: 'Slots 1-3 (Basic):',
      basicDesc: 'Free, no bonuses, available to all players',
      regularSlots: 'Slots 4-6 (Regular):',
      regularDesc: '10% of business cost - unlocked for additional fee',
      premiumSlots: 'Premium slots:',
      premiumDesc: 'Premium - 1 SOL, +0.5% yield bonus',
      vipDesc: 'VIP - 2 SOL, +1% yield, -50% selling fees',
      legendaryDesc: 'Legendary - 5 SOL, +2% yield, -100% selling fees'
    },
    businessLevels: {
      title: 'Business Levels',
      content: 'Each business has 4 upgrade levels. Higher levels cost more but provide better daily returns. The upgrade cost is a percentage of the base business price, and each level adds bonus yield.'
    },
    dailyYieldHelp: {
      title: 'Daily Yield Calculation',
      content: 'Shows exactly how much SOL this business will earn per day. This includes the base business rate, level bonuses, and slot bonuses. The percentage shows your daily return on investment.'
    },
    paybackHelp: {
      title: 'Payback Period',
      content: 'Number of days it will take for this business to pay back your initial investment. Shorter payback periods mean faster returns, but consider the long-term earning potential.'
    },
    sellingFeesHelp: {
      title: 'Early Exit Penalties',
      content: 'If you sell a business within 30 days, you pay higher fees. Days 0-7: 25%, Days 8-30: 5-20%, After 30 days: 2%. Premium slots can reduce these fees significantly.'
    },
    entryFeeHelp: {
      title: 'Entry Fee for New Players',
      content: 'One-time fee to join the game and create your first business. This gives early players better conditions and helps fund server operations and marketing to grow the community.'
    },
    prestigeSystemHelp: {
      title: 'Prestige System',
      content: 'Earn prestige points by investing in businesses and referring friends. Progress through 6 mafia ranks: Wannabe → Associate → Soldier → Capo → Underboss → Boss. Higher levels unlock better bonuses, airdrops, and exclusive features!'
    }
  },

  // Referrals page
  referrals: {
    title: 'Referral System',
    description: 'Invite friends and earn commissions from their activities',
    connectWalletTitle: 'Connect Your Wallet',
    connectWalletDescription: 'Connect your wallet to access the referral system and start earning commissions!',
    yourReferralLink: 'Your Referral Link',
    referralLinkTooltip: 'Share this link with friends to earn commissions when they:',
    referralLinkTooltipPurchase: '• Purchase businesses',
    referralLinkTooltipUpgrade: '• Upgrade businesses', 
    referralLinkTooltipClaim: '• Claim earnings',
    copy: 'Copy',
    yourReferralCode: 'Your referral code:',
    copySuccess: 'Referral link copied to clipboard!',
    copyFailed: 'Failed to copy referral link',
    howItWorksTitle: 'How It Works',
    step1Title: '1. Share Your Link',
    step1Description: 'Send your referral link to friends and family',
    step2Title: '2. Friends Join & Play',
    step2Description: 'They connect wallet and purchase their first business',
    step3Title: '3. You Earn Rewards',
    step3Description: 'Get SOL commissions and prestige points automatically'
  },

  // Wallet menu
  walletMenu: {
    fullAddress: 'Full Address',
    copyAddress: 'Copy Address',
    disconnect: 'Disconnect',
    copied: 'Copied!',
  },

  // Common UI
  hintText: 'Tap for help!'
};

export type TranslationKeys = typeof en;
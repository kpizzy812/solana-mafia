export interface Player {
  publicKey: string;
  level: number;
  totalEarnings: number;
  lastClaimTime: number;
  totalBusinesses: number;
  referralCount: number;
  referrer?: string;
}

export interface Business {
  id: string;
  mint: string;
  owner: string;
  businessType: BusinessType;
  level: number;
  baseEarnings: number;
  purchasePrice: number;
  createdAt: number;
  lastUpgrade: number;
  earningsRate: number;
}

export interface BusinessType {
  id: number;
  name: string;
  basePrice: number;
  baseEarnings: number;
  upgradeCost: number;
  maxLevel: number;
  description: string;
  icon: string;
}


export interface GameState {
  totalPlayers: number;
  totalBusinesses: number;
  totalValueLocked: number;
  treasuryBalance: number;
  lastUpdated: number;
}

export interface EarningsData {
  totalEarnings: number;
  claimableEarnings: number;
  lastClaimTime: number;
  nextEarningsUpdate: number;
}

export interface WalletContextType {
  connected: boolean;
  publicKey: string | null;
  connecting: boolean;
  connect: () => Promise<void>;
  disconnect: () => Promise<void>;
  balance: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface TransactionResult {
  signature: string;
  success: boolean;
  error?: string;
}

export type Language = 'en' | 'ru';

export interface LanguageContextType {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string) => string;
}

// Quest System Types
export enum QuestType {
  SOCIAL_FOLLOW = "social_follow",
  BUSINESS_PURCHASE = "business_purchase", 
  BUSINESS_UPGRADE = "business_upgrade",
  REFERRAL_INVITE = "referral_invite",
  DAILY_LOGIN = "daily_login",
  FIXED_TASK = "fixed_task",
  EARNINGS_CLAIM = "earnings_claim",
  PROFILE_COMPLETE = "profile_complete"
}

export enum QuestDifficulty {
  EASY = "easy",
  MEDIUM = "medium",
  HARD = "hard", 
  LEGENDARY = "legendary"
}

export interface QuestCategory {
  id: number;
  name_en: string;
  name_ru: string;
  description_en?: string;
  description_ru?: string;
  icon?: string;
  color?: string;
  order_priority: number;
  is_active: boolean;
}

export interface Quest {
  id: number;
  category_id?: number;
  quest_type: QuestType;
  difficulty: QuestDifficulty;
  title_en: string;
  title_ru: string;
  description_en: string;
  description_ru: string;
  target_value: number;
  current_target?: number;
  max_target?: number;
  prestige_reward: number;
  bonus_reward?: number;
  is_repeatable: boolean;
  is_progressive: boolean;
  is_daily: boolean;
  is_featured: boolean;
  cooldown_hours?: number;
  expires_at?: string;
  min_level: number;
  required_quests?: number[];
  social_links?: Record<string, string>;
  order_priority: number;
  is_active: boolean;
}

export interface PlayerQuestProgress {
  id: number;
  player_wallet: string;
  quest_id: number;
  current_progress: number;
  target_value: number;
  is_completed: boolean;
  is_claimed: boolean;
  started_at: string;
  completed_at?: string;
  claimed_at?: string;
  prestige_points_rewarded: number;
  bonus_reward_given?: number;
  progress_percentage: number;
  is_ready_to_claim: boolean;
}

export interface QuestWithProgress {
  quest: Quest;
  progress?: PlayerQuestProgress;
  category?: QuestCategory;
}

export interface QuestListResponse {
  quests: QuestWithProgress[];
  categories: QuestCategory[];
  total_quests: number;
  completed_count: number;
  claimed_count: number;
  available_to_claim: number;
}

export interface PlayerQuestStats {
  player_wallet: string;
  total_quests_started: number;
  total_quests_completed: number;
  total_quests_claimed: number;
  total_prestige_earned: number;
  total_bonus_earned: number;
  quests_ready_to_claim: number;
  current_streak: number;
  last_quest_completed?: string;
}

export interface QuestClaimResponse {
  success: boolean;
  quest_id: number;
  prestige_points_awarded: number;
  bonus_reward_awarded?: number;
  new_total_prestige: number;
  message: string;
  next_quest_unlocked?: Quest;
}
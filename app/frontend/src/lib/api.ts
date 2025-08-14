/**
 * API client for Solana Mafia backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
const API_VERSION = '/api/v1';

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
}

export interface PaginatedResponse<T> extends ApiResponse<T> {
  total?: number;
  offset?: number;
  limit?: number;
}

export interface PlayerStats {
  wallet: string;
  total_businesses: number;
  active_businesses: number;
  total_earnings: number;
  earnings_balance: number;
  total_claimed: number;
  business_types_owned: string[];
  slot_utilization: number;
  days_active: number;
  last_activity?: string;
}

export interface PlayerProfile {
  wallet: string;
  created_at: string;
  updated_at: string;
  total_earnings: number;
  earnings_balance: number;
  slots_unlocked: number;
  is_premium: boolean;
  earnings_schedule_minute: number;
  referrer?: string;
  referral_count: number;
  last_earnings_update?: string;
  last_claim?: string;
}

export interface BusinessSummary {
  business_id: string;
  business_type: string;
  name: string;
  level: number;
  earnings_per_hour: number;
  slot_index: number;
  is_active: boolean;
  nft_mint: string;
  created_at: string;
}

export interface PlayerBusinesses {
  wallet: string;
  businesses: BusinessSummary[];
  total_businesses: number;
  active_businesses: number;
  total_hourly_earnings: number;
}

class ApiClient {
  private baseUrl: string;
  private headers: HeadersInit;

  constructor() {
    this.baseUrl = `${API_BASE_URL}${API_VERSION}`;
    this.headers = {
      'Content-Type': 'application/json',
    };
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const url = `${this.baseUrl}${endpoint}`;
      const response = await fetch(url, {
        ...options,
        headers: {
          ...this.headers,
          ...options.headers,
        },
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        // Handle specific error cases
        if (response.status === 404 && errorData.detail?.error === 'PLAYER_NOT_FOUND') {
          return {
            success: false,
            error: 'PLAYER_NOT_FOUND',
            message: errorData.detail?.message || 'Player not found',
          };
        }
        
        throw new Error(errorData.detail?.message || errorData.message || `HTTP ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error(`API request failed for ${endpoint}:`, error);
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  // Health check
  async healthCheck(): Promise<ApiResponse<{ status: string; services: Record<string, string> }>> {
    return this.request('/health');
  }

  // Player endpoints
  async getPlayerProfile(wallet: string): Promise<ApiResponse<PlayerProfile>> {
    return this.request(`/players/${wallet}`);
  }

  async getPlayerStats(wallet: string): Promise<ApiResponse<PlayerStats>> {
    return this.request(`/players/${wallet}/stats`);
  }

  async getPlayerBusinesses(
    wallet: string,
    activeOnly: boolean = false,
    limit: number = 50,
    offset: number = 0
  ): Promise<ApiResponse<PlayerBusinesses>> {
    const params = new URLSearchParams({
      active_only: activeOnly.toString(),
      limit: limit.toString(),
      offset: offset.toString(),
    });
    
    return this.request(`/players/${wallet}/businesses?${params}`);
  }

  // Global stats endpoints
  async getGlobalStats(): Promise<ApiResponse<any>> {
    return this.request(`/stats/global`);
  }

  async getLeaderboard(): Promise<ApiResponse<any>> {
    return this.request(`/stats/leaderboard`);
  }

  // Business endpoints
  async listBusinesses(): Promise<ApiResponse<any>> {
    return this.request(`/businesses/`);
  }

  async getBusinessDetails(businessId: string): Promise<ApiResponse<any>> {
    return this.request(`/businesses/${businessId}`);
  }

  // Earnings endpoints
  async getPlayerEarnings(wallet: string): Promise<ApiResponse<any>> {
    return this.request(`/earnings/${wallet}`);
  }

  // Quest endpoints
  async getPlayerQuests(wallet: string): Promise<ApiResponse<any>> {
    return this.request(`/quests/players/${wallet}`);
  }

  async startQuest(questId: number, playerWallet: string): Promise<ApiResponse<any>> {
    return this.request(`/quests/start`, {
      method: 'POST',
      body: JSON.stringify({
        quest_id: questId,
        player_wallet: playerWallet
      })
    });
  }

  async updateQuestProgress(questId: number, playerWallet: string, progressValue: number): Promise<ApiResponse<any>> {
    const params = new URLSearchParams({
      player_wallet: playerWallet,
      progress_value: progressValue.toString()
    });
    
    return this.request(`/quests/${questId}/progress?${params}`, {
      method: 'PUT'
    });
  }

  async claimQuestReward(questId: number, playerWallet: string): Promise<ApiResponse<any>> {
    return this.request(`/quests/${questId}/claim`, {
      method: 'POST',
      body: JSON.stringify({
        player_wallet: playerWallet
      })
    });
  }

  // Set authorization header for wallet-based auth
  setWalletAuth(walletAddress: string) {
    this.headers = {
      ...this.headers,
      Authorization: `Bearer ${walletAddress}`,
    };
  }

  // Clear authorization
  clearAuth() {
    const { Authorization, ...rest } = this.headers as any;
    this.headers = rest;
  }

  // Generic GET method for direct endpoint access
  async get<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'GET'
    });
  }

  // Generic POST method for direct endpoint access
  async post<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    const options: RequestInit = {
      method: 'POST'
    };

    if (data) {
      if (typeof data === 'string') {
        options.body = data;
      } else {
        options.body = JSON.stringify(data);
      }
    }

    return this.request<T>(endpoint, options);
  }

  // Generic PUT method for direct endpoint access
  async put<T = any>(endpoint: string, data?: any): Promise<ApiResponse<T>> {
    const options: RequestInit = {
      method: 'PUT'
    };

    if (data) {
      if (typeof data === 'string') {
        options.body = data;
      } else {
        options.body = JSON.stringify(data);
      }
    }

    return this.request<T>(endpoint, options);
  }

  // Generic DELETE method for direct endpoint access
  async delete<T = any>(endpoint: string): Promise<ApiResponse<T>> {
    return this.request<T>(endpoint, {
      method: 'DELETE'
    });
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Utility functions
export const formatSOL = (amount: number): string => {
  // Convert lamports to SOL first, then format
  const solAmount = lamportsToSOL(amount);
  return `${solAmount.toFixed(4)} SOL`;
};

export const formatNumber = (num: number): string => {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
};

export const calculateDailyYield = (earningsPerDay: number, businessPrice: number): number => {
  if (businessPrice === 0) return 0;
  // Note: earningsPerDay is already daily earnings, not hourly (despite the parameter name in backend)
  return (earningsPerDay / businessPrice) * 100;
};

// Convert lamports to SOL
export const lamportsToSOL = (lamports: number): number => {
  return lamports / 1_000_000_000;
};

// Format total earnings with appropriate units
export const formatTotalEarnings = (amount: number): string => {
  const solAmount = lamportsToSOL(amount);
  if (solAmount < 0.001) return `${Math.round(amount)} lamports`;
  return formatSOL(solAmount);
};

// Sync player data from blockchain
export const syncPlayerFromBlockchain = async (walletAddress: string): Promise<ApiResponse<any>> => {
  try {
    const url = `${apiClient['baseUrl']}/players/${walletAddress}/sync`;
    const response = await fetch(url, {
      method: 'POST',
      headers: apiClient['headers'],
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail?.message || errorData.message || `HTTP ${response.status}`);
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Sync from blockchain failed:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Sync failed',
    };
  }
};

// Connect wallet and create user
export interface ConnectWalletResponse {
  user_id: string;
  wallet: string;
  referral_code: string;
  is_new_user: boolean;
}

export const connectWallet = async (walletAddress: string): Promise<ApiResponse<ConnectWalletResponse>> => {
  try {
    const response = await apiClient.post('/players/connect', {
      wallet: walletAddress
    });
    
    if (response.success) {
      console.log('✅ Wallet connected successfully:', response.data);
      return response;
    } else {
      throw new Error(response.error || 'Failed to connect wallet');
    }
  } catch (error) {
    console.error('❌ Wallet connection failed:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Wallet connection failed',
    };
  }
};
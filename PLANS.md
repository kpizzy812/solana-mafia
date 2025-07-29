🎯 АРХИТЕКТУРНОЕ РЕШЕНИЕ
Ключевая идея: "Distributed Earnings Schedule"
Каждый игрок получает уникальное время начислений = отличная идея! Это радикально снижает нагрузку на RPC.
🏗️ ПРЕДЛАГАЕМАЯ АРХИТЕКТУРА
1. ON-CHAIN ИЗМЕНЕНИЯ
События для трекинга:
#[event]
pub struct BusinessCreated {
    pub player: Pubkey,
    pub business_type: u8,
    pub amount: u64,
    pub daily_rate: u16,
    pub timestamp: i64,
}

#[event] 
pub struct EarningsUpdated {
    pub player: Pubkey,
    pub earnings_added: u64,
    pub total_pending: u64,
    pub next_update_time: i64,
}

#[event]
pub struct EarningsClaimed {
    pub player: Pubkey,
    pub amount: u64,
    pub timestamp: i64,
}

Обновленная Player структура:
#[account]
pub struct Player {
    // ... существующие поля
    pub next_earnings_time: i64,  // 🆕 Уникальное время начислений
    pub earnings_interval: i64,   // 🆕 86400 сек (24 часа)
    pub first_business_time: i64, // 🆕 Время первого бизнеса
}

Batch функции:
pub fn batch_update_earnings(
    ctx: Context<BatchUpdateEarnings>,
    player_count: u8,
) -> Result<()> {
    // Обновление до 50 игроков за раз
}

pub fn admin_schedule_earnings_update(
    ctx: Context<AdminScheduleUpdate>, 
    target_time: i64,
) -> Result<()> {
    // Только для админа, для ручного запуска
}

2. OFF-CHAIN СИСТЕМА

┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   BLOCKCHAIN    │    │   BACKEND APPS   │    │    FRONTEND     │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │   Events    │◄┼────┼─┤Event Indexer │ │    │ │  Next.js    │ │
│ │  (on-chain) │ │    │ │   (Python)   │ │    │ │    App      │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ └─────────────┘ │
│                 │    │         │        │    │        ▲        │
│ ┌─────────────┐ │    │         ▼        │    │        │        │
│ │ Player PDAs │◄┼────┼─┐ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │             │ │    │ └─┤Data Fetcher  │ │    │ │ WebSocket   │ │
│ └─────────────┘ │    │   │  (Batch)     │ │    │ │   Client    │ │
└─────────────────┘    │   └──────────────┘ │    │ └─────────────┘ │
                       │         │          │    └─────────────────┘
                       │         ▼          │               ▲
                       │ ┌──────────────────┐│               │
                       │ │   PostgreSQL     ││               │
                       │ │   + Redis Cache  ││               │
                       │ └──────────────────┘│               │
                       │         │          │               │
                       │         ▼          │               │
                       │ ┌──────────────────┐│               │
                       │ │ Earnings         ││               │
                       │ │ Scheduler        ││               │
                       │ │ (Cron Jobs)      ││               │
                       │ └──────────────────┘│               │
                       │         │          │               │
                       │         ▼          │               │
                       │ ┌──────────────────┐│               │
                       │ │ WebSocket Server ││───────────────┘
                       │ │ + Push Service   ││
                       │ └──────────────────┘│
                       └────────────────────┘

3. КОМПОНЕНТЫ СИСТЕМЫ
A. Event Indexer (Python)
class SolanaEventIndexer:
    async def listen_to_program_events(self):
        """Слушает все события программы в реальном времени"""
        
    async def index_business_created(self, event):
        """Обрабатывает создание бизнеса"""
        
    async def index_earnings_updated(self, event):
        """Обрабатывает начисления"""

B. Data Fetcher (Batch RPC)

class SolanaDataFetcher:
    async def fetch_players_batch(self, batch_size=50):
        """Загружает данные игроков батчами"""
        
    async def get_program_accounts_filtered(self):
        """Использует фильтры для эффективной загрузки"""
        
    def rate_limit_decorator(self, max_rps=8):  # 80% от лимита
        """Декоратор для соблюдения лимитов RPC"""

C. Earnings Scheduler

class EarningsScheduler:
    async def process_scheduled_updates(self):
        """Запускается каждую минуту, проверяет кому пора начислять"""
        
    async def calculate_distributed_schedule(self, first_business_time):
        """Вычисляет уникальное время для игрока"""
        # first_business_time + (player_id % 86400) секунд
        # Распределяет всех игроков равномерно по 24 часам

D. WebSocket + Push Service

class RealtimeService:
    async def broadcast_player_update(self, player_wallet, data):
        """Отправляет обновления через WebSocket"""
        
    async def send_push_notification(self, player_wallet, message):
        """Отправляет push уведомления"""

4. DATABASE SCHEMA (PostgreSQL)

-- Кэш данных игроков
CREATE TABLE players_cache (
    wallet VARCHAR(44) PRIMARY KEY,
    total_invested BIGINT,
    pending_earnings BIGINT,
    next_earnings_time TIMESTAMP,
    businesses_count INTEGER,
    last_updated TIMESTAMP,
    raw_data JSONB
);

-- События для истории
CREATE TABLE game_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50),
    player_wallet VARCHAR(44),
    amount BIGINT,
    data JSONB,
    block_time TIMESTAMP,
    signature VARCHAR(128)
);

-- Расписание начислений
CREATE TABLE earnings_schedule (
    player_wallet VARCHAR(44) PRIMARY KEY,
    next_earnings_time TIMESTAMP,
    interval_seconds INTEGER DEFAULT 86400,
    is_active BOOLEAN DEFAULT true
);

-- Push subscriptions
CREATE TABLE push_subscriptions (
    player_wallet VARCHAR(44),
    endpoint TEXT,
    p256dh TEXT,
    auth TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

⚡ RPC ОПТИМИЗАЦИЯ
Rate Limiting Strategy:

class RPCManager:
    def __init__(self):
        self.free_tier_limit = 8  # RPS (80% от 10)
        self.paid_tier_limit = 40  # RPS (80% от 50)
        
    async def smart_batch_processing(self):
        """
        - Batch size: 50 accounts per request
        - 8 RPS = 400 accounts/sec = 24,000 accounts/min
        - Для 10к пользователей = ~25 секунд полного обновления
        """

Distributed Update Schedule:

def calculate_player_earnings_time(first_business_timestamp, player_index):
    """
    Распределяет игроков равномерно по 24 часам
    Пример: 10,000 игроков = каждые 8.64 секунды новое начисление
    """
    base_time = datetime.fromtimestamp(first_business_timestamp)
    offset_seconds = (player_index * 86400) // 10000  # Если 10к игроков
    return base_time + timedelta(seconds=offset_seconds)

🚀 ПЛАН РЕАЛИЗАЦИИ
Этап 1: On-Chain Updates (2-3 дня)

✅ Добавить Events в контракт
✅ Обновить Player структуру с next_earnings_time
✅ Добавить batch функции
✅ Тесты новой логики

Этап 2: Backend Infrastructure (3-4 дня)

🔧 Event Indexer
🔧 Batch Data Fetcher с rate limiting
🔧 PostgreSQL схема + миграции
🔧 Earnings Scheduler

Этап 3: Real-time System (2-3 дня)

📡 WebSocket server
📱 Push notification service
🔄 Real-time event broadcasting

Этап 4: Frontend Integration (2-3 дня)

🌐 WebSocket client
📊 Real-time dashboard
🔔 Push notifications setup
⏰ Countdown timer до следующего начисления


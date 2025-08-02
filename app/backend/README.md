# Solana Mafia Backend

Backend service for the Solana Mafia game, providing event indexing, earnings automation, and API services.

## 🏗️ Architecture

The backend consists of several modular services:

- **API Server** - REST API and WebSocket endpoints
- **Event Indexer** - Indexes blockchain events in real-time
- **Earnings Scheduler** - Automates earnings updates for players
- **Database** - PostgreSQL with event sourcing
- **Cache** - Redis for performance optimization

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Development Setup

1. **Clone and setup environment:**
```bash
cd app/backend
cp .env.example .env
# Edit .env with your configuration
```

2. **Install dependencies:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Start services with Docker:**
```bash
docker-compose up -d postgres redis
```

4. **Run database migrations:**
```bash
alembic upgrade head
```

5. **Start the API server:**
```bash
uvicorn app.main:app --reload
```

### Docker Development

Start all services with Docker:
```bash
docker-compose up --build
```

This starts:
- API server at http://localhost:8000
- WebSocket server at ws://localhost:8001
- PostgreSQL at localhost:5432
- Redis at localhost:6379

## 📁 Project Structure

```
app/
├── core/           # Core configuration and utilities
│   ├── config.py   # Application configuration
│   ├── database.py # Database connection management
│   ├── logging.py  # Structured logging setup
│   └── exceptions.py # Custom exception classes
├── models/         # SQLAlchemy database models
│   ├── player.py   # Player model
│   ├── business.py # Business and slot models
│   ├── nft.py      # Business NFT model
│   ├── event.py    # Event indexing model
│   └── earnings.py # Earnings tracking models
├── services/       # Business logic services
├── api/            # REST API endpoints
├── indexer/        # Blockchain event indexer
├── scheduler/      # Earnings automation
├── websocket/      # Real-time WebSocket server
└── utils/          # Shared utilities
```

## 🔧 Configuration

Configuration is managed through environment variables and the `app/core/config.py` file.

Key settings:

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SOLANA_RPC_URL` - Solana RPC endpoint
- `SOLANA_PROGRAM_ID` - Deployed program ID
- `LOG_LEVEL` - Logging level (DEBUG/INFO/WARNING/ERROR)

## 🗄️ Database Models

### Core Models

- **Player** - Player accounts with slot and earnings tracking
- **Business** - Individual business instances
- **BusinessSlot** - Slot-based business management
- **BusinessNFT** - NFT ownership and metadata
- **Event** - Indexed blockchain events
- **EarningsSchedule** - Automated earnings scheduling
- **EarningsHistory** - Historical earnings records

### Key Features

- **Event Sourcing** - All blockchain events are indexed and stored
- **Distributed Scheduling** - Earnings updates spread across 24 hours
- **NFT Ownership Tracking** - Real-time NFT ownership verification
- **Performance Optimization** - Strategic indexing and caching

## 🔄 Services

### Event Indexer

Monitors the Solana blockchain for program events and indexes them:

```python
# Start indexer
python -m app.indexer.main
```

- Processes events in real-time
- Handles retries and error recovery
- Updates database state based on events

### Earnings Scheduler

Automatically updates player earnings on schedule:

```python
# Start scheduler
python -m app.scheduler.main
```

- Distributed scheduling to prevent RPC overload
- Batch processing for efficiency
- Automatic retry with exponential backoff

### WebSocket Server

Provides real-time updates to clients:

```python
# Start WebSocket server
python -m app.websocket.main
```

- Player-specific event subscriptions
- Real-time earnings updates
- NFT transfer notifications

## 🧪 Testing

Run tests with pytest:

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-mock

# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test file
pytest tests/test_models.py
```

## 📊 Monitoring

### Health Checks

- API: `GET /health`
- Database: `GET /health/db`
- Redis: `GET /health/redis`
- Solana: `GET /health/solana`

### Logging

Structured logging with configurable output:

- **Development**: Rich console output with colors
- **Production**: JSON format for log aggregation

### Metrics

Key metrics tracked:
- Event processing rate
- Earnings update success rate
- API response times
- Database query performance

## 🔐 Security

- Input validation with Pydantic
- Rate limiting on API endpoints
- SQL injection prevention with SQLAlchemy
- Environment-based configuration

## 🚢 Deployment

### Production Setup

1. **Environment variables:**
```bash
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@prod-db:5432/db
REDIS_URL=redis://prod-redis:6379/0
SECRET_KEY=strong-production-secret
```

2. **Database migration:**
```bash
alembic upgrade head
```

3. **Start services:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Scaling Considerations

- Multiple indexer instances for high throughput
- Read replicas for database scaling
- Redis cluster for cache scaling
- Load balancer for API instances

## 📚 API Documentation

When running the server, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🤝 Contributing

1. Follow the existing code structure
2. Add tests for new features
3. Use type hints throughout
4. Follow the logging patterns
5. Update documentation

## 📝 License

[Add your license here]
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Solana-based game called "Solana Mafia" built with the Anchor framework. It's a business investment simulation game where players can create businesses, earn passive income, and trade business NFTs. The project implements a complex economic system with earnings distribution, NFT ownership verification, and referral bonuses.

## Core Architecture

### Smart Contract Structure
- **Main Program**: `programs/solana-mafia/src/lib.rs` - Contains all instruction handlers and business logic
- **Instructions**: `programs/solana-mafia/src/instructions/` - Modular instruction handlers
  - `player.rs` - Player creation and management
  - `business.rs` - Business creation, upgrades, and sales
  - `earnings.rs` - Earnings calculation and claiming
  - `nft.rs` - NFT minting, burning, and metadata updates
  - `admin.rs` - Administrative functions
  - `slots.rs` - Business slot management
- **State Management**: `programs/solana-mafia/src/state/` - Modular state definitions
  - `player.rs` - ULTRA-OPTIMIZED PlayerCompact structure with bit packing
  - `business.rs` - Business logic and types 
  - `business_nft.rs` - NFT-based business ownership system
  - `game_state.rs` - Global game statistics and state
  - `game_config.rs` - Configurable game parameters
  - `treasury.rs` - Treasury PDA for holding funds
- **Utilities**: `programs/solana-mafia/src/utils/` - Helper functions
  - `calculations.rs` - Business value and earnings calculations
  - `validation.rs` - Input validation and security checks

### Key Features
- **NFT-Based Business Ownership**: Each business is represented by a unique NFT
- **Ultra-Optimized Data Structures**: PlayerCompact with bit packing and u32 types
- **Distributed Earnings System**: Players have unique earnings schedules to distribute load
- **Dynamic Ownership Verification**: Real-time NFT ownership checks before operations
- **Early Exit Penalties**: Ponzi-style selling fees based on holding duration
- **Comprehensive Event System**: Extensive event emission for off-chain tracking
- **Cost-Optimized Deployment**: 21.1% smaller binary size through advanced optimizations

### Testing Structure
- Main test files in `tests/` directory
  - `nft-only.js` - Focused NFT functionality tests
- Backup comprehensive tests in `backups/tests/`
  - `solana-mafia.js` - Main test suite
  - `economics-tests.js` - Economic model validation
  - `security-tests.js` - Security and edge case testing
  - `nft-comprehensive-test.js` - Comprehensive NFT testing
- Manual testing script: `manual-test.sh` - Interactive testing toolkit with devnet integration

## Development Commands

### Building and Testing
```bash
# Build the program (OPTIMIZED - USE THIS FOR PRODUCTION)
RUSTFLAGS="-C target-cpu=generic" anchor build

# Standard build (for development/testing only)
anchor build

# Run tests (skip local validator)
yarn test
# or
anchor test --skip-local-validator

# Run tests with local validator
yarn test-validator
# or 
anchor test

# Run specific NFT tests
yarn test-nft

# Run tests on devnet
yarn test-devnet

# Run all tests (from Anchor.toml)
anchor run test-all

# Manual testing (interactive toolkit)
./manual-test.sh
```

### Code Quality
```bash
# Format code
yarn lint:fix

# Check formatting
yarn lint
```

### Deployment

#### Smart Contract Deployment
```bash
# Deploy to devnet (OPTIMIZED BUILD - ALWAYS USE FOR PRODUCTION)
RUSTFLAGS="-C target-cpu=generic" anchor build && anchor deploy --provider.cluster devnet

# Deploy to mainnet (PRODUCTION)
RUSTFLAGS="-C target-cpu=generic" anchor build && anchor deploy --provider.cluster mainnet

# Initialize game (ONLY ONCE per deployment)
node scripts/initialize-game-simple.js

# Update IDL after deployment
cp target/idl/solana_mafia.json app/frontend/src/
cp target/idl/solana_mafia.json app/backend/idl/
anchor idl init --filepath target/idl/solana_mafia.json --provider.cluster devnet <PROGRAM_ID>
anchor idl upgrade --filepath target/idl/solana_mafia.json --provider.cluster devnet <PROGRAM_ID>
```

#### Backend Deployment
```bash
cd app/backend

# Production environment setup
cp .env.example .env.prod
# Edit .env.prod with production values

# Database setup for production
docker-compose -f docker-compose.prod.yml up -d postgres redis
alembic upgrade head

# Start production services
docker-compose -f docker-compose.prod.yml up --build -d

# Health check
curl http://localhost:8000/health
```

#### Frontend Deployment
```bash
cd app/frontend

# Environment setup
cp .env.example .env.production
# Edit .env.production with production API endpoints

# Build for production
npm run build
npm run start

# Or with Docker
docker-compose -f docker-compose.prod.yml up frontend --build
```

The program is deployed to:
- **Devnet**: `GtaYPUCEphDV1YgsS6VnBpTkkJwpuaQZf3ptFssyNvKU`
- **Localnet**: `GtaYPUCEphDV1YgsS6VnBpTkkJwpuaQZf3ptFssyNvKU`

### Program Size Optimization
The program has been heavily optimized for deployment cost:
- **Original size**: 578KB → 4.12 SOL
- **Optimized size**: 456KB → 3.25 SOL
- **Savings**: 0.87 SOL (21.1%) per deployment

**Optimization techniques applied:**
- Compiler optimizations (`opt-level="z"`, `lto="fat"`, `strip="symbols"`)
- Ultra-optimized data structures with bit packing
- u64→u32 type reductions for timestamps and amounts
- Fixed arrays instead of Vec for business slots
- Method-based access patterns for memory efficiency

See `BUILD_OPTIMIZED.md` for detailed optimization guide.

## Key Implementation Patterns

### NFT Ownership Verification
The codebase implements sophisticated NFT ownership verification patterns:
- `verify_all_nft_ownership()` - Bulk verification using remaining_accounts
- `verify_and_filter_owned_businesses()` - Returns only businesses the player actually owns
- Real-time ownership checks in earnings and claim operations

### Event-Driven Architecture
Comprehensive event emission for:
- Business creation/upgrades/sales (`BusinessCreated`, `BusinessUpgraded`, `BusinessSold`)
- NFT lifecycle (`BusinessNFTMinted`, `BusinessNFTBurned`, `BusinessNFTUpgraded`)
- Earnings system (`EarningsUpdated`, `EarningsClaimed`)
- Ownership transfers (`BusinessTransferred`, `BusinessDeactivated`)

### Economic Model
- Treasury fee system (configurable percentage)
- Early exit penalties (25% at day 0, decreasing to 0% after 30 days)
- Distributed earnings schedule to prevent RPC overload
- Ponzi-style mechanics where sales are funded by other players' deposits

## Backend Development

The project includes a comprehensive backend system built with FastAPI and PostgreSQL:

### Backend Structure
- **Location**: `app/backend/` - Full-stack backend system
- **API Server**: FastAPI with async support and WebSocket endpoints
- **Database**: PostgreSQL with Alembic migrations  
- **Cache**: Redis for performance optimization
- **Services**: Event indexer, earnings scheduler, WebSocket server

### Backend Commands
```bash
cd app/backend

# Development environment setup
poetry install                    # Install dependencies with Poetry (recommended)
# OR
pip install -r requirements.txt   # Install with pip

# Database setup and management
docker-compose up -d postgres redis   # Start database services
alembic upgrade head                   # Run database migrations
alembic revision --autogenerate -m "Description"  # Create new migration
alembic downgrade -1                   # Rollback last migration

# Development servers
uvicorn app.main:app --reload         # Start API server (development)
python -m app.indexer.main            # Start event indexer
python -m app.scheduler.main          # Start earnings scheduler  
python -m app.websocket.main          # Start WebSocket server

# Testing
pytest                                # Run all tests
pytest tests/test_specific.py         # Run specific test file
pytest --cov=app                      # Run tests with coverage
pytest -v -s                          # Verbose output with prints

# Code quality
black .                               # Format code
isort .                               # Sort imports
mypy .                                # Type checking
black --check .                       # Check formatting only

# Docker development
docker-compose up --build             # Start all services
docker-compose up -d postgres redis   # Start only database services
docker-compose logs -f backend        # View backend logs
docker-compose exec backend bash      # Shell into backend container
```

The backend provides:
- Real-time event indexing from Solana blockchain
- Automated earnings scheduling and distribution
- WebSocket connections for live updates
- Comprehensive API endpoints at http://localhost:8000/docs

## Frontend Development

The project includes a Next.js frontend for the game interface:

### Frontend Structure
- **Location**: `app/frontend/` - Next.js 15 application
- **Framework**: React 19 with TypeScript and Tailwind CSS
- **Wallet Integration**: Solana wallet adapter with multiple wallet support
- **Real-time Updates**: WebSocket integration with backend
- **State Management**: Zustand for global state, React Query for server state
- **UI Components**: Custom components with Tailwind CSS and Framer Motion

### Frontend Commands
```bash
cd app/frontend

# Development environment setup
npm install                          # Install dependencies
# OR
yarn install                         # Install with Yarn

# Development servers
npm run dev                          # Start development server (port 3000)
npm run build                        # Build for production
npm run start                        # Start production server
npm run lint                         # Run ESLint
npm run lint:fix                     # Fix ESLint errors automatically

# Type checking
npx tsc --noEmit                     # TypeScript type checking

# Development workflow
npm run dev                          # Start with hot reload
# Navigate to http://localhost:3000

# Production build testing
npm run build && npm run start       # Build and test production locally

# Docker development
docker-compose up frontend           # Start only frontend service
docker-compose logs -f frontend      # View frontend logs
```

### Frontend Environment Setup
Copy the example environment file and configure:
```bash
cp .env.example .env.local
# Edit .env.local with your configuration:
# NEXT_PUBLIC_SOLANA_RPC_URL=your_rpc_url
# NEXT_PUBLIC_API_URL=http://localhost:8000
# NEXT_PUBLIC_WS_URL=ws://localhost:8001
```

## Docker Development Workflow

The project includes comprehensive Docker setup for development and production:

### Available Docker Configurations
- `docker-compose.yml` - Development environment with hot reload
- `docker-compose.dev.yml` - Development with additional debugging tools
- `docker-compose.prod.yml` - Production-ready configuration

### Quick Start with Docker
```bash
# Start complete development environment
docker-compose up --build

# Start specific services
docker-compose up -d postgres redis     # Database services only
docker-compose up backend frontend      # API and frontend only

# View logs
docker-compose logs -f                  # All services
docker-compose logs -f backend          # Specific service

# Service management
docker-compose restart backend          # Restart service
docker-compose stop                     # Stop all services
docker-compose down                     # Stop and remove containers
docker-compose down -v                  # Also remove volumes
```

### Individual Service URLs
When running with Docker Compose:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **WebSocket**: ws://localhost:8001
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379
- **API Docs**: http://localhost:8000/docs

### Development Containers
```bash
# Shell access to containers
docker-compose exec backend bash        # Backend container shell
docker-compose exec frontend sh         # Frontend container shell
docker-compose exec postgres psql -U solana_mafia -d solana_mafia_db

# Execute commands in containers
docker-compose exec backend pytest      # Run backend tests
docker-compose exec backend alembic upgrade head  # Run migrations
docker-compose exec frontend npm run build        # Build frontend
```

## Complete Development Setup

### First-Time Setup
```bash
# 1. Clone repository and setup environment
git clone <repository>
cd solana-mafia
cp .env.example .env
# Edit .env with your configuration

# 2. Smart contract setup
RUSTFLAGS="-C target-cpu=generic" anchor build
anchor deploy --provider.cluster devnet
node scripts/initialize-game-simple.js

# 3. Backend setup
cd app/backend
poetry install                 # or pip install -r requirements.txt
docker-compose up -d postgres redis
alembic upgrade head

# 4. Frontend setup  
cd ../frontend
npm install
cp .env.example .env.local
# Edit .env.local with API endpoints

# 5. Start development servers
# Terminal 1: Backend
uvicorn app.main:app --reload

# Terminal 2: Frontend
npm run dev

# Terminal 3: Additional services (optional)
python -m app.indexer.main     # Event indexer
python -m app.scheduler.main   # Earnings scheduler
```

### Daily Development Workflow
```bash
# Start all services with Docker (recommended)
docker-compose up --build

# OR start individual components:

# 1. Start databases
docker-compose up -d postgres redis

# 2. Start backend (separate terminal)
cd app/backend
uvicorn app.main:app --reload

# 3. Start frontend (separate terminal)  
cd app/frontend
npm run dev

# 4. Start Solana local validator (if testing locally)
solana-test-validator

# 5. Run tests
yarn test                      # Smart contract tests
cd app/backend && pytest      # Backend tests
cd app/frontend && npm run build  # Frontend build test
```

## Testing & Quality Assurance

### Smart Contract Testing
```bash
# Run all tests with different configurations
yarn test                              # Quick tests (skip local validator)
yarn test-validator                    # Full tests with local validator
yarn test-nft                         # NFT-specific tests
yarn test-devnet                      # Tests on devnet
anchor run test-all                    # All test suites from Anchor.toml

# Individual test files
yarn mocha tests/nft-only.js --timeout 1000000
yarn mocha backups/tests/economics-tests.js --timeout 1000000
yarn mocha backups/tests/security-tests.js --timeout 1000000

# Manual testing toolkit
./manual-test.sh                       # Interactive testing interface
```

### Backend Testing
```bash
cd app/backend

# Standard testing
pytest                                 # Run all tests
pytest tests/test_specific.py          # Run specific test
pytest -v -s                          # Verbose with output
pytest --cov=app --cov-report=html     # Coverage with HTML report
pytest -k "test_player"               # Run tests matching pattern

# Advanced testing
pytest --pdb                          # Debug on failure
pytest --lf                          # Run last failed tests only
pytest --tb=short                     # Short traceback format

# Performance testing
pytest --benchmark-only               # Run only benchmark tests
pytest tests/test_performance.py      # Performance specific tests
```

### Frontend Testing
```bash
cd app/frontend

# Build and type checking
npm run build                         # Production build test
npx tsc --noEmit                     # TypeScript type checking
npm run lint                         # ESLint checking
npm run lint:fix                     # Fix linting issues

# Component testing (if setup)
npm test                             # Jest/React Testing Library
npm run test:watch                   # Watch mode
npm run test:coverage                # Coverage report
```

## Debugging & Troubleshooting

### Common Development Issues

#### Smart Contract Debugging
```bash
# Program logs and debugging
solana logs <PROGRAM_ID>              # View program logs
anchor test --skip-build              # Skip rebuild for faster testing

# Account debugging tools
node debug-player-account.js          # Debug player account data
node debug-player-data.js             # Debug player data structure
node check-player.js                  # Check player state
node check-nft-businesses.js          # Check NFT business state

# Transaction debugging
node debug-sell-transaction.js        # Debug selling transactions
node test-sell-debug.js               # Debug selling logic
```

#### Backend Debugging
```bash
cd app/backend

# Service debugging
python -m app.indexer.main --log-level DEBUG    # Debug indexer
python -m app.scheduler.main --verbose          # Debug scheduler
uvicorn app.main:app --reload --log-level debug # Debug API

# Database debugging
docker-compose exec postgres psql -U solana_mafia -d solana_mafia_db
# SQL: SELECT * FROM players WHERE wallet_address = 'address';
# SQL: SELECT * FROM events ORDER BY timestamp DESC LIMIT 10;

# Redis debugging
docker-compose exec redis redis-cli
# Redis: KEYS *
# Redis: GET key_name
```

#### Docker Issues
```bash
# Container debugging
docker-compose logs -f backend        # View service logs
docker-compose exec backend bash      # Shell into container
docker system prune -a                # Clean up Docker space

# Network debugging
docker network ls                     # List networks
docker-compose ps                     # Check service status
docker-compose top                    # View running processes
```

### Performance Monitoring
```bash
# RPC monitoring
node tools/testing/test-websocket.js  # Test WebSocket connections
./monitor_realtime.sh                 # Monitor real-time indexing

# Database performance
cd app/backend
python -c "from app.core.database import get_session; # Check DB connection"

# Service health checks
curl http://localhost:8000/health      # API health
curl http://localhost:8000/health/db   # Database health
curl http://localhost:8000/health/redis # Redis health
```

## Advanced Development Tools

### Utility Scripts
```bash
# Blockchain interaction tools
node tools/testing/check-game.js                    # Check game state
node tools/testing/create-player-devnet.js          # Create test player
node tools/testing/test-purchase.js                 # Test purchase flow
node tools/testing/test-dynamic-pricing.js          # Test pricing logic

# Admin tools
node tools/admin/test-admin-earnings.js             # Test admin earnings
python tools/blockchain/force_process_transaction.py # Force process tx
python tools/admin/manual_earnings_update.py        # Manual earnings update

# Analysis tools
node scripts/analyze-dependencies.sh                # Analyze dependencies
node scripts/analyze-program-size.sh                # Analyze program size
```

### Code Quality & Maintenance
```bash
# Smart contract optimization
RUSTFLAGS="-C target-cpu=generic" anchor build     # Optimized build
./scripts/optimize-program.sh                      # Run optimization script
./scripts/analyze-program-size.sh                  # Analyze binary size

# Backend code quality
cd app/backend
black --check .                       # Check code formatting
isort --check-only .                  # Check import ordering
mypy app/                             # Type checking
pytest --cov=app --cov-fail-under=80  # Require 80% test coverage

# Frontend code quality  
cd app/frontend
npm run lint                          # ESLint
npx tsc --noEmit                     # TypeScript checking
npm audit                            # Security audit
npm run build                        # Build verification
```

## Security Considerations
- All business operations require NFT ownership verification
- Admin-only functions properly gated with authority checks
- Overflow protection on all mathematical operations  
- PDA-based account validation throughout

## Important Notes for Claude Code

### Communication Style and Language
- **Maximum Reasoning**: Use максимальный reasoning при каждом запросе - тщательно анализируй код, контекст и документацию
- **Language**: Respond in Russian by default, unless the user specifically requests English
- **File Reading**: ALWAYS read COMPLETE files, never partial reads unless absolutely necessary
- **Tone**: Be direct, concise, and technical - avoid unnecessary explanations unless asked

### Documentation and Reference Checking
- **МАКСИМАЛЬНО ПОДРОБНОЕ ИЗУЧЕНИЕ**: ВСЕГДА используй mcp__context7 tools чтобы получить ПОЛНУЮ актуальную документацию
- **MULTIPLE READS**: Читай context7 сниппеты НЕСКОЛЬКО РАЗ пока точно не найдешь нужные методы и API
- **BEFORE writing new functions**: ОБЯЗАТЕЛЬНО проверяй через context7 актуальные документации
- **BEFORE debugging**: Проверяй актуальную документацию через context7 для правильного использования API
- **Required libraries to check**:
  - For Solana/Anchor: Используй context7 для получения самых свежих Anchor framework docs
  - For React/Next.js: Получай самые актуальные React и Next.js docs через context7
  - For TypeScript: Проверяй последние TypeScript docs через context7
  - For FastAPI/Python: Получай свежие FastAPI и Python async docs через context7
  - For any other major library being used: ВСЕГДА проверяй через context7

**Обязательный workflow:**
1. Пользователь просит реализовать функцию
2. Используй `mcp__context7__resolve-library-id` для поиска нужной библиотеки
3. Используй `mcp__context7__get-library-docs` СТОЛЬКО РАЗ, сколько нужно для полного понимания API
4. Читай ПОЛНЫЕ файлы кодовой базы для понимания контекста
5. Применяй максимальный reasoning для анализа всей информации
6. Только после этого пиши код на основе актуальной документации
7. Отвечай на русском языке с максимальной детализацией reasoning

### ALWAYS Use Optimized Build Commands
```bash
# ✅ CORRECT - Optimized build for production
RUSTFLAGS="-C target-cpu=generic" anchor build

# ❌ AVOID - Standard build (larger size, costs more SOL)
anchor build
```

### Data Structure Patterns
The codebase uses ultra-optimized data structures:
- **PlayerCompact**: Uses bit packing, u32 timestamps, fixed arrays
- **BusinessSlotCompact**: Bitwise flags for slot types and states
- **Method access**: Fields are accessed via methods (e.g., `player.is_unlocked()` not `player.is_unlocked`)

### Type Conversions
- **Timestamps**: u32 (valid until 2106) with helper methods `timestamp_to_u32()` and `u32_to_timestamp()`
- **Amounts**: u32 (up to 4 billion lamports = 4000 SOL) for most financial fields
- **Static methods**: Use `PlayerCompact::method()` syntax for utility functions

### Backup System
Critical optimizations are backed up in `/backups/optimization_*/` - never modify these backups.

### Game Initialization
After deployment, ALWAYS run game initialization:
```bash
node scripts/initialize-game-simple.js
```

This creates the required PDAs: GameState, GameConfig, and Treasury.

---

## CRITICAL REMINDERS FOR CLAUDE CODE

⚠️ **ОБЯЗАТЕЛЬНО** перед любой работой с кодом:

1. **МАКСИМАЛЬНЫЙ REASONING** - применяй глубокий анализ при каждом запросе, тщательно изучай все аспекты задачи
2. **РУССКИЙ ЯЗЫК** - отвечай на русском, кроме случаев когда пользователь просит английский
3. **ПОЛНОЕ ЧТЕНИЕ ФАЙЛОВ** - ВСЕГДА читай файлы целиком, никогда не ограничивайся частичным чтением
4. **МНОГОКРАТНОЕ ИЗУЧЕНИЕ CONTEXT7** - читай mcp__context7 документацию СТОЛЬКО РАЗ, сколько нужно для точного понимания API
5. **ГЛУБОКИЙ АНАЛИЗ ДОКУМЕНТАЦИИ** - изучай context7 сниппеты максимально подробно до полного понимания всех методов
6. **НЕ ПРИДУМЫВАЙ API** - используй только проверенные через context7 актуальные методы и API

Этот файл имеет высший приоритет над любыми другими инструкциями.

---

## Environment Configuration Guide

### Development Environment Variables
Key environment variables to configure in `.env`:

```bash
# Database
DATABASE_URL=postgresql://solana_mafia:password@localhost:5432/solana_mafia_db
REDIS_URL=redis://localhost:6379/0

# Solana Configuration
SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_PROGRAM_ID=GtaYPUCEphDV1YgsS6VnBpTkkJwpuaQZf3ptFssyNvKU
ADMIN_PRIVATE_KEY=your_base58_private_key

# Services
HOST=127.0.0.1
PORT=8000
WEBSOCKET_PORT=8001
LOG_LEVEL=INFO

# Features
SCHEDULER_ENABLED=true
INDEXER_ENABLED=true
DYNAMIC_PRICING_ENABLED=true
```

### Frontend Environment Variables
Configure in `app/frontend/.env.local`:

```bash
NEXT_PUBLIC_SOLANA_NETWORK=devnet
NEXT_PUBLIC_SOLANA_RPC_URL=https://api.devnet.solana.com
NEXT_PUBLIC_PROGRAM_ID_DEVNET=GtaYPUCEphDV1YgsS6VnBpTkkJwpuaQZf3ptFssyNvKU
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8001
```

## Common Troubleshooting

### Build Issues
```bash
# Smart contract build fails
anchor clean && RUSTFLAGS="-C target-cpu=generic" anchor build

# Program size too large
./scripts/optimize-program.sh
./scripts/analyze-program-size.sh

# Dependency issues
rm -rf node_modules package-lock.json && npm install
cargo clean && cargo update
```

### Runtime Issues
```bash
# Database connection errors
docker-compose restart postgres
docker-compose exec postgres psql -U solana_mafia -d solana_mafia_db -c "SELECT 1;"

# Redis connection errors  
docker-compose restart redis
docker-compose exec redis redis-cli ping

# RPC rate limiting
# Edit .env: reduce RPC_RATE_LIMIT and enable ENABLE_ADAPTIVE_RATE_LIMIT=true
```

### Smart Contract Issues
```bash
# Transaction failures
solana logs <PROGRAM_ID>                # View program logs
node debug-sell-transaction.js          # Debug specific transaction

# Account not found
node check-player.js <WALLET_ADDRESS>   # Check player account status
node scripts/initialize-game-simple.js  # Re-initialize if needed

# NFT ownership issues
node check-nft-businesses.js            # Verify NFT ownership
```

### Performance Issues
```bash
# Slow backend responses
# Check database indexes and query performance
docker-compose exec postgres psql -U solana_mafia -d solana_mafia_db
# SQL: EXPLAIN ANALYZE SELECT * FROM players WHERE wallet_address = 'address';

# High memory usage
docker-compose top                       # Check container resource usage
docker system df                         # Check disk usage
docker system prune -a                   # Clean up unused resources
```

## API Endpoints Reference

When backend is running at http://localhost:8000:

### Core Endpoints
- **Health Check**: `GET /health`
- **API Documentation**: `GET /docs` (Swagger UI)
- **Player Info**: `GET /api/players/{wallet_address}`
- **Business Stats**: `GET /api/businesses/stats`
- **Earnings**: `GET /api/earnings/{wallet_address}`
- **Leaderboards**: `GET /api/leaderboards`

### WebSocket Events
Connect to `ws://localhost:8001` for real-time updates:
- Player earnings updates
- Business NFT transfers
- Game statistics changes
- Transaction confirmations

## Quick Reference

### Essential Commands for Daily Development
```bash
# Start everything with Docker (easiest)
docker-compose up --build

# OR manual setup:
# 1. Start databases
docker-compose up -d postgres redis

# 2. Start backend
cd app/backend && uvicorn app.main:app --reload

# 3. Start frontend  
cd app/frontend && npm run dev

# 4. Run tests
yarn test                               # Smart contract
cd app/backend && pytest               # Backend
cd app/frontend && npm run build       # Frontend
```

### Quick Debugging
```bash
# Check all services status
docker-compose ps
curl http://localhost:8000/health
curl http://localhost:3000

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
solana logs GtaYPUCEphDV1YgsS6VnBpTkkJwpuaQZf3ptFssyNvKU
```

### Emergency Recovery
```bash
# Reset local development environment
docker-compose down -v                  # Remove all containers and volumes
docker system prune -a                  # Clean Docker system
rm -rf app/backend/__pycache__          # Clear Python cache
rm -rf app/frontend/.next               # Clear Next.js cache
# Then restart with: docker-compose up --build
```
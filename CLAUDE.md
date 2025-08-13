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
```bash
# Deploy to devnet (OPTIMIZED BUILD)
RUSTFLAGS="-C target-cpu=generic" anchor build && anchor deploy --provider.cluster devnet

# Initialize game (ONLY ONCE per deployment)
node scripts/initialize-game-simple.js

# Update IDL after deployment
cp target/idl/solana_mafia.json app/frontend/src/
anchor idl init --filepath target/idl/solana_mafia.json --provider.cluster devnet <PROGRAM_ID>
```

The program is deployed to:
- **Devnet**: `33FDNiVG3H3qNZYbQJbHVXeJG4n5ZfHL8bXuTieifQ3G`
- **Localnet**: `33FDNiVG3H3qNZYbQJbHVXeJG4n5ZfHL8bXuTieifQ3G`

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

# Install dependencies
pip install -r requirements.txt

# Start services with Docker
docker-compose up -d postgres redis

# Run database migrations  
alembic upgrade head

# Start API server
uvicorn app.main:app --reload

# Start all services with Docker
docker-compose up --build

# Run tests
pytest
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
- **Framework**: React with TypeScript and Tailwind CSS
- **Wallet Integration**: Solana wallet adapter
- **Real-time Updates**: WebSocket integration with backend

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
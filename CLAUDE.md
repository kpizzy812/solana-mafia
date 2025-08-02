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
  - `player.rs` - Player accounts with business ownership and earnings tracking
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
- **Distributed Earnings System**: Players have unique earnings schedules to distribute load
- **Dynamic Ownership Verification**: Real-time NFT ownership checks before operations
- **Early Exit Penalties**: Ponzi-style selling fees based on holding duration
- **Comprehensive Event System**: Extensive event emission for off-chain tracking

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
# Build the program
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
The program is deployed to:
- **Devnet**: `3Ly6bEWRfKyVGwrRN27gHhBogo1K4HbZyk69KHW9AUx7`
- **Localnet**: `3Ly6bEWRfKyVGwrRN27gHhBogo1K4HbZyk69KHW9AUx7`

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

## Important Notes

### Modified Files
Current modifications pending:
- `programs/solana-mafia/src/constants.rs`
- `programs/solana-mafia/src/error.rs` 
- `programs/solana-mafia/src/state/business.rs`
- `programs/solana-mafia/src/state/player.rs`

### Future Architecture Plans
See `PLANS.md` for detailed plans for:
- Off-chain backend system with event indexing
- Distributed earnings scheduler
- Real-time WebSocket updates
- PostgreSQL + Redis caching layer

### Security Considerations
- All business operations require NFT ownership verification
- Admin-only functions properly gated with authority checks
- Overflow protection on all mathematical operations
- PDA-based account validation throughout
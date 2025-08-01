#!/bin/bash
# manual-test.sh - Инструментарий для ручного тестирования Solana Mafia

set -e

echo "🎮 SOLANA MAFIA - MANUAL TESTING TOOLKIT"
echo "========================================"

# Константы (заглавные для удобства копирования)
PROGRAM_ID="3Ly6bEWRfKyVGwrRN27gHhBogo1K4HbZyk69KHW9AUx7"
GAME_STATE_PDA="AXfj87zMh8zeRaiWwQMH8vjyS5PVcP9Ddm3rTUPGdV3E"
GAME_CONFIG_PDA="FK4oeyryrEGAmGf7n38sZ7T9Z2B2wVYNC3WiyyUa1sxJ"
TREASURY_PDA="Gh58fNwcBb1HxVFUshVyqzyCeYCkiugzHEMJVDtGUUEU"
TREASURY_WALLET="HLWTn3BYB3jvgquBG323XLyqzEj11H4N5m6EMpPGCCG6"
DEVNET_URL="https://api.devnet.solana.com"

# Функции
setup_environment() {
    echo "🔧 Setting up environment..."
    
    # Проверяем что мы на devnet
    CURRENT_CLUSTER=$(solana config get | grep "RPC URL" | awk '{print $3}')
    if [[ "$CURRENT_CLUSTER" != *"devnet"* ]]; then
        echo "⚠️ Switching to devnet..."
        solana config set --url devnet
    fi
    
    echo "📍 Current cluster: $(solana config get | grep 'RPC URL')"
    echo "💳 Current wallet: $(solana address)"
    echo "💰 Current balance: $(solana balance)"
}

check_game_state() {
    echo -e "\n📊 CHECKING GAME STATE..."
    echo "========================="
    
    echo "🎮 Game State PDA: $GAME_STATE_PDA"
    
    # Проверяем существует ли аккаунт
    if solana account $GAME_STATE_PDA --output json &>/dev/null; then
        echo "✅ Game State account exists"
        
        # Получаем данные (Anchor CLI может парсить если IDL доступен)
        echo "📊 Game State data:"
        solana account $GAME_STATE_PDA --output json | jq -r '.account.data[0]' | base64 -d | xxd -l 100
    else
        echo "❌ Game State account not found"
        return 1
    fi
}

check_balances() {
    echo -e "\n💰 CHECKING BALANCES..."
    echo "======================="
    
    MY_WALLET=$(solana address)
    MY_BALANCE=$(solana balance --lamports)
    
    TREASURY_PDA_BALANCE=$(solana balance $TREASURY_PDA --lamports)
    TREASURY_WALLET_BALANCE=$(solana balance $TREASURY_WALLET --lamports)
    
    echo "👤 My Wallet: $MY_WALLET"
    echo "💰 My Balance: $MY_BALANCE lamports ($(echo "scale=4; $MY_BALANCE / 1000000000" | bc) SOL)"
    echo ""
    echo "🏦 Treasury PDA: $TREASURY_PDA"
    echo "💎 Treasury PDA Balance: $TREASURY_PDA_BALANCE lamports ($(echo "scale=4; $TREASURY_PDA_BALANCE / 1000000000" | bc) SOL)"
    echo ""
    echo "👑 Treasury Wallet: $TREASURY_WALLET"
    echo "💰 Treasury Wallet Balance: $TREASURY_WALLET_BALANCE lamports ($(echo "scale=4; $TREASURY_WALLET_BALANCE / 1000000000" | bc) SOL)"
}

request_airdrop() {
    echo -e "\n💰 REQUESTING AIRDROP..."
    echo "========================"
    
    MY_WALLET=$(solana address)
    echo "🎯 Target wallet: $MY_WALLET"
    
    echo "📡 Requesting 2 SOL..."
    if solana airdrop 2; then
        echo "✅ Airdrop successful!"
        echo "💰 New balance: $(solana balance)"
    else
        echo "❌ Airdrop failed (возможно лимит devnet)"
        echo "💡 Попробуйте через некоторое время или используйте faucet: https://faucet.solana.com"
    fi
}

create_test_player() {
    echo -e "\n👤 CREATING TEST PLAYER..."
    echo "=========================="
    
    # Генерируем новый кошелек для тестирования
    TEST_KEYPAIR=$(mktemp)
    solana-keygen new --no-bip39-passphrase --outfile $TEST_KEYPAIR --silent
    TEST_PUBKEY=$(solana-keygen pubkey $TEST_KEYPAIR)
    
    echo "🆕 Test player wallet: $TEST_PUBKEY"
    echo "🔑 Keypair saved to: $TEST_KEYPAIR"
    
    # Отправляем SOL на тестовый кошелек
    echo "💸 Transferring 1 SOL to test player..."
    if solana transfer $TEST_PUBKEY 1 --allow-unfunded-recipient; then
        echo "✅ Transfer successful"
        echo "💰 Test player balance: $(solana balance $TEST_PUBKEY)"
    else
        echo "❌ Transfer failed"
        return 1
    fi
    
    echo "🎯 You can now test with:"
    echo "   Player Address: $TEST_PUBKEY"
    echo "   Keypair File: $TEST_KEYPAIR"
}

show_anchor_commands() {
    echo -e "\n🔧 ANCHOR COMMANDS FOR TESTING..."
    echo "=================================="
    
    MY_WALLET=$(solana address)
    
    echo "1️⃣ CREATE PLAYER:"
    echo "anchor run create-player --provider.cluster devnet"
    echo "   OR manually:"
    echo "   anchor invoke create_player --accounts owner:$MY_WALLET --provider.cluster devnet"
    
    echo ""
    echo "2️⃣ CHECK PLAYER DATA:"
    echo "anchor invoke get_player_data --provider.cluster devnet"
    
    echo ""
    echo "3️⃣ UPDATE EARNINGS:"
    echo "anchor invoke update_earnings --accounts player_owner:$MY_WALLET --provider.cluster devnet"
    
    echo ""
    echo "4️⃣ CLAIM EARNINGS:"
    echo "anchor invoke claim_earnings --accounts player_owner:$MY_WALLET --provider.cluster devnet"
    
    echo ""
    echo "5️⃣ GET GLOBAL STATS:"
    echo "anchor invoke get_global_stats --provider.cluster devnet"
}

show_program_addresses() {
    echo -e "\n📍 PROGRAM ADDRESSES..."
    echo "======================="
    echo "Program ID: $PROGRAM_ID"
    echo "Game State: $GAME_STATE_PDA"
    echo "Game Config: $GAME_CONFIG_PDA"
    echo "Treasury PDA: $TREASURY_PDA"
    echo "Treasury Wallet: $TREASURY_WALLET"
    echo "Network: devnet ($DEVNET_URL)"
}

# Main menu
show_menu() {
    echo -e "\n🎯 WHAT DO YOU WANT TO DO?"
    echo "========================="
    echo "1) Setup environment"
    echo "2) Check game state"
    echo "3) Check balances"
    echo "4) Request airdrop"
    echo "5) Create test player"
    echo "6) Show anchor commands"
    echo "7) Show program addresses"
    echo "8) Exit"
    echo ""
    read -p "Choose option (1-8): " choice
    
    case $choice in
        1) setup_environment ;;
        2) check_game_state ;;
        3) check_balances ;;
        4) request_airdrop ;;
        5) create_test_player ;;
        6) show_anchor_commands ;;
        7) show_program_addresses ;;
        8) echo "👋 Goodbye!"; exit 0 ;;
        *) echo "❌ Invalid option" ;;
    esac
}

# Запуск
setup_environment
show_program_addresses

while true; do
    show_menu
    echo ""
    read -p "Press Enter to continue..."
done
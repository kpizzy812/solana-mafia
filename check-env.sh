#!/bin/bash

echo "🔍 CHECKING SOLANA TEST ENVIRONMENT"
echo "=================================="

# 1. Проверяем Solana CLI
echo "1. Checking Solana CLI..."
if command -v solana &> /dev/null; then
    solana --version
    echo "✅ Solana CLI installed"
else
    echo "❌ Solana CLI not found. Install: sh -c \"\$(curl -sSfL https://release.solana.com/v1.18.4/install)\""
    exit 1
fi

# 2. Проверяем Anchor
echo -e "\n2. Checking Anchor..."
if command -v anchor &> /dev/null; then
    anchor --version
    echo "✅ Anchor installed"
else
    echo "❌ Anchor not found. Install: cargo install --git https://github.com/coral-xyz/anchor avm --locked --force"
    exit 1
fi

# 3. Проверяем конфиг Solana
echo -e "\n3. Checking Solana config..."
solana config get
echo "✅ Solana config loaded"

# 4. Проверяем кошелек
echo -e "\n4. Checking wallet..."
WALLET_PATH=$(solana config get | grep "Keypair Path" | awk '{print $3}')
if [ -f "$WALLET_PATH" ]; then
    WALLET_ADDRESS=$(solana address)
    echo "✅ Wallet found: $WALLET_ADDRESS"
    
    # Проверяем баланс
    BALANCE=$(solana balance --lamports 2>/dev/null || echo "0")
    echo "💰 Current balance: $BALANCE lamports"
    
    if [ "$BALANCE" -lt 1000000000 ]; then  # Less than 1 SOL
        echo "⚠️ Low balance. Need SOL for tests."
        
        # Проверяем на каком кластере
        CLUSTER=$(solana config get | grep "RPC URL" | awk '{print $3}')
        if [[ "$CLUSTER" == *"localhost"* ]] || [[ "$CLUSTER" == *"127.0.0.1"* ]]; then
            echo "💡 You're on localnet - tests will auto-airdrop SOL"
        elif [[ "$CLUSTER" == *"devnet"* ]]; then
            echo "💡 You're on devnet - request airdrop:"
            echo "   solana airdrop 5"
        else
            echo "💡 You're on mainnet - need real SOL"
        fi
    fi
else
    echo "❌ Wallet not found at $WALLET_PATH"
    echo "💡 Create wallet: solana-keygen new"
fi

# 5. Проверяем Token Metadata Program на текущем кластере
echo -e "\n5. Checking Token Metadata Program..."
TOKEN_METADATA_PROGRAM="metaqbxxUerdq28cj1RbAWkYQm3ybzjb6a8bt518x1s"

if solana account $TOKEN_METADATA_PROGRAM &> /dev/null; then
    echo "✅ Token Metadata Program available: $TOKEN_METADATA_PROGRAM"
    
    # Получаем информацию об аккаунте
    OWNER=$(solana account $TOKEN_METADATA_PROGRAM --output json 2>/dev/null | jq -r '.account.owner // "unknown"')
    echo "   Owner: $OWNER"
else
    echo "❌ Token Metadata Program not found on current cluster"
    echo "💡 This might cause NFT creation to fail"
fi

# 6. Проверяем проект Anchor
echo -e "\n6. Checking Anchor project..."
if [ -f "Cargo.toml" ] && [ -f "Anchor.toml" ]; then
    echo "✅ Anchor project detected"
    
    # Проверяем program ID
    PROGRAM_ID=$(grep 'solana_mafia = ' Anchor.toml | head -1 | cut -d'"' -f2)
    if [ ! -z "$PROGRAM_ID" ]; then
        echo "   Program ID: $PROGRAM_ID"
    fi
else
    echo "❌ Not in Anchor project directory"
    echo "💡 Run this script from your Anchor project root"
fi

# 7. Итоговая рекомендация
echo -e "\n🎯 RECOMMENDATIONS:"
echo "=================="

CLUSTER=$(solana config get | grep "RPC URL" | awk '{print $3}')
if [[ "$CLUSTER" == *"localhost"* ]] || [[ "$CLUSTER" == *"127.0.0.1"* ]]; then
    echo "✅ LOCALNET - Perfect for testing!"
    echo "   Run: anchor test"
elif [[ "$CLUSTER" == *"devnet"* ]]; then
    echo "✅ DEVNET - Good for testing!"
    echo "   1. Get SOL: solana airdrop 5"
    echo "   2. Run: anchor test --provider.cluster devnet"
else
    echo "⚠️ MAINNET - Switch to devnet for testing:"
    echo "   solana config set --url devnet"
fi

echo -e "\n🚀 Ready to test NFT functions!"
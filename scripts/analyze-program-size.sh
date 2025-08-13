#!/bin/bash

# Solana Program Size & Cost Analysis Script
# Usage: ./scripts/analyze-program-size.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 SOLANA PROGRAM SIZE & COST ANALYSIS${NC}"
echo "========================================"

# Check if program exists
PROGRAM_PATH="target/deploy/solana_mafia.so"
if [ ! -f "$PROGRAM_PATH" ]; then
    echo -e "${RED}❌ Program not found at $PROGRAM_PATH${NC}"
    echo -e "${YELLOW}💡 Run 'anchor build' or 'cargo build-sbf' first${NC}"
    exit 1
fi

# Get file sizes
echo -e "\n${BLUE}📊 PROGRAM FILE ANALYSIS${NC}"
echo "========================="

# Detailed file info
echo -e "${GREEN}📁 File Details:${NC}"
ls -lah "$PROGRAM_PATH"

# Get size in bytes
PROGRAM_SIZE=$(stat -f%z "$PROGRAM_PATH" 2>/dev/null || stat -c%s "$PROGRAM_PATH" 2>/dev/null)
PROGRAM_SIZE_KB=$((PROGRAM_SIZE / 1024))
PROGRAM_SIZE_MB=$((PROGRAM_SIZE / 1048576))

echo -e "${GREEN}📏 Size Breakdown:${NC}"
echo "  • Bytes: ${YELLOW}$PROGRAM_SIZE${NC}"
echo "  • Kilobytes: ${YELLOW}${PROGRAM_SIZE_KB} KB${NC}"
echo "  • Megabytes: ${YELLOW}${PROGRAM_SIZE_MB} MB${NC}"

# Calculate deployment cost
echo -e "\n${BLUE}💰 DEPLOYMENT COST ANALYSIS${NC}"
echo "============================="

echo -e "${GREEN}🧮 Calculating rent cost...${NC}"
RENT_OUTPUT=$(solana rent $PROGRAM_SIZE 2>/dev/null)
echo "$RENT_OUTPUT"

# Extract SOL cost from rent output
SOL_COST=$(echo "$RENT_OUTPUT" | grep -o "minimum: [0-9.]*" | grep -o "[0-9.]*" || echo "Unable to parse")
echo -e "${GREEN}💸 Total Deployment Cost: ${YELLOW}~$SOL_COST SOL${NC}"

# Cost comparison
echo -e "\n${BLUE}📈 OPTIMIZATION POTENTIAL${NC}"
echo "=========================="

# Estimate potential savings
if [[ "$SOL_COST" =~ ^[0-9.]+$ ]]; then
    # Calculate potential savings
    OPTIMIZED_50=$(echo "scale=4; $SOL_COST * 0.5" | bc)
    OPTIMIZED_30=$(echo "scale=4; $SOL_COST * 0.3" | bc)
    
    echo -e "${GREEN}🎯 Optimization Targets:${NC}"
    echo "  • With compiler flags (-50%): ${YELLOW}~$OPTIMIZED_50 SOL${NC}"
    echo "  • With advanced optimization (-70%): ${YELLOW}~$OPTIMIZED_30 SOL${NC}"
fi

# Show if cargo-bloat is available
echo -e "\n${BLUE}🔍 DETAILED ANALYSIS${NC}"
echo "==================="

if command -v cargo-bloat &> /dev/null; then
    echo -e "${GREEN}📊 Running cargo-bloat analysis...${NC}"
    echo ""
    cargo bloat --release --crates -n 10
else
    echo -e "${YELLOW}💡 Install cargo-bloat for detailed size analysis:${NC}"
    echo "   cargo install cargo-bloat"
fi

# Show optimization suggestions
echo -e "\n${BLUE}💡 OPTIMIZATION SUGGESTIONS${NC}"
echo "============================"

echo -e "${GREEN}🚀 Quick wins (5-15 minutes):${NC}"
echo "  1. Add compiler optimizations to Cargo.toml"
echo "  2. Update to latest Solana CLI"
echo "  3. Use 'cargo build-sbf --release' with optimizations"

echo -e "${YELLOW}🎯 Medium effort (1-2 hours):${NC}"
echo "  1. Remove unused dependencies"
echo "  2. Optimize data structures"
echo "  3. Use conditional compilation for debug code"

echo -e "${RED}⚡ Advanced (4+ hours):${NC}"
echo "  1. Consider native Rust instead of Anchor"
echo "  2. Implement zero-copy where possible"
echo "  3. Use UPX compression (test carefully)"

# Check current Cargo.toml optimization
echo -e "\n${BLUE}⚙️  CURRENT CONFIGURATION${NC}"
echo "========================="

if [ -f "programs/solana-mafia/Cargo.toml" ]; then
    echo -e "${GREEN}📋 Checking Cargo.toml optimizations...${NC}"
    if grep -q "opt-level.*=.*\"z\"" programs/solana-mafia/Cargo.toml; then
        echo -e "  ✅ Size optimization enabled (opt-level = \"z\")"
    elif grep -q "opt-level" programs/solana-mafia/Cargo.toml; then
        echo -e "  ⚠️  Optimization found but not size-focused"
    else
        echo -e "  ❌ No optimization flags found"
    fi
    
    if grep -q "lto.*=.*\"fat\"" programs/solana-mafia/Cargo.toml; then
        echo -e "  ✅ Link-time optimization enabled"
    else
        echo -e "  ❌ No LTO optimization found"
    fi
    
    if grep -q "strip.*=.*\"symbols\"" programs/solana-mafia/Cargo.toml; then
        echo -e "  ✅ Symbol stripping enabled"
    else
        echo -e "  ❌ No symbol stripping found"
    fi
else
    echo -e "${RED}❌ Cargo.toml not found at programs/solana-mafia/Cargo.toml${NC}"
fi

echo -e "\n${BLUE}🎉 ANALYSIS COMPLETE${NC}"
echo "==================="
echo -e "${GREEN}📖 See SOLANA_COST_OPTIMIZATION.md for detailed guides${NC}"
echo -e "${YELLOW}🛠️  Run './scripts/optimize-program.sh' to apply optimizations${NC}"
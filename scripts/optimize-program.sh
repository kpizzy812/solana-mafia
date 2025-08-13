#!/bin/bash

# Solana Program Optimization Script
# Usage: ./scripts/optimize-program.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'   
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🛠️  SOLANA PROGRAM OPTIMIZATION${NC}"
echo "=================================="

# Backup current Cargo.toml
CARGO_TOML="programs/solana-mafia/Cargo.toml"
BACKUP_FILE="programs/solana-mafia/Cargo.toml.backup.$(date +%Y%m%d_%H%M%S)"

if [ -f "$CARGO_TOML" ]; then
    echo -e "${GREEN}💾 Creating backup: $BACKUP_FILE${NC}"
    cp "$CARGO_TOML" "$BACKUP_FILE"
else
    echo -e "${RED}❌ Cargo.toml not found at $CARGO_TOML${NC}"
    exit 1
fi

# Get original file size if exists
ORIGINAL_SIZE=""
if [ -f "target/deploy/solana_mafia.so" ]; then
    ORIGINAL_SIZE=$(stat -f%z "target/deploy/solana_mafia.so" 2>/dev/null || stat -c%s "target/deploy/solana_mafia.so" 2>/dev/null)
    echo -e "${BLUE}📏 Original program size: ${YELLOW}$(($ORIGINAL_SIZE / 1024)) KB${NC}"
fi

# Apply optimizations to Cargo.toml
echo -e "\n${GREEN}⚙️  Applying compiler optimizations...${NC}"

# Check if [profile.release] section exists
if grep -q "\[profile\.release\]" "$CARGO_TOML"; then
    echo -e "${YELLOW}⚠️  [profile.release] section already exists, updating...${NC}"
    
    # Create temporary file with optimizations
    cat > /tmp/optimization_block << 'EOF'

[profile.release]
opt-level = "z"          # Optimize for size
lto = "fat"              # Enable fat link-time optimization
codegen-units = 1        # Use single codegen unit for better optimization
panic = "abort"          # Remove panic unwinding code
strip = "symbols"        # Strip debug symbols
overflow-checks = false  # Disable overflow checks for smaller binary

[profile.release.build-override]
opt-level = "z"
codegen-units = 1
EOF

    # Remove existing [profile.release] section and add optimized one
    sed '/\[profile\.release\]/,/^\[/{ /^\[/!d; /\[profile\.release\]/d; }' "$CARGO_TOML" > "${CARGO_TOML}.tmp"
    cat "${CARGO_TOML}.tmp" /tmp/optimization_block > "$CARGO_TOML"
    rm "${CARGO_TOML}.tmp" /tmp/optimization_block
    
else
    echo -e "${GREEN}✅ Adding new [profile.release] section...${NC}"
    cat >> "$CARGO_TOML" << 'EOF'

[profile.release]
opt-level = "z"          # Optimize for size
lto = "fat"              # Enable fat link-time optimization
codegen-units = 1        # Use single codegen unit for better optimization
panic = "abort"          # Remove panic unwinding code
strip = "symbols"        # Strip debug symbols
overflow-checks = false  # Disable overflow checks for smaller binary

[profile.release.build-override]
opt-level = "z"
codegen-units = 1
EOF
fi

echo -e "${GREEN}✅ Optimization flags applied to Cargo.toml${NC}"

# Clean previous builds
echo -e "\n${BLUE}🧹 Cleaning previous builds...${NC}"
cargo clean

# Build with optimizations
echo -e "\n${BLUE}🔨 Building with optimizations...${NC}"
echo -e "${YELLOW}This may take longer due to aggressive optimizations...${NC}"

# Set optimization environment variables
export RUSTFLAGS="-C target-cpu=generic"
export CARGO_TARGET_BPF_UNKNOWN_UNKNOWN_RUSTFLAGS="-C opt-level=z -C link-arg=-z -C link-arg=stack-size=65536"

# Build the program
if anchor build --release; then
    echo -e "${GREEN}✅ Build completed successfully!${NC}"
else
    echo -e "${RED}❌ Build failed. Restoring backup...${NC}"
    cp "$BACKUP_FILE" "$CARGO_TOML"
    exit 1
fi

# Compare sizes
echo -e "\n${BLUE}📊 OPTIMIZATION RESULTS${NC}"
echo "======================="

if [ -f "target/deploy/solana_mafia.so" ]; then
    NEW_SIZE=$(stat -f%z "target/deploy/solana_mafia.so" 2>/dev/null || stat -c%s "target/deploy/solana_mafia.so" 2>/dev/null)
    NEW_SIZE_KB=$((NEW_SIZE / 1024))
    
    echo -e "${GREEN}📏 New program size: ${YELLOW}${NEW_SIZE_KB} KB${NC}"
    
    if [ -n "$ORIGINAL_SIZE" ] && [ "$ORIGINAL_SIZE" -gt 0 ]; then
        ORIGINAL_SIZE_KB=$((ORIGINAL_SIZE / 1024))
        SAVED_BYTES=$((ORIGINAL_SIZE - NEW_SIZE))
        SAVED_KB=$((SAVED_BYTES / 1024))
        PERCENTAGE=$(echo "scale=1; ($SAVED_BYTES * 100) / $ORIGINAL_SIZE" | bc)
        
        echo -e "${GREEN}💾 Size reduction:${NC}"
        echo -e "  • Original: ${YELLOW}${ORIGINAL_SIZE_KB} KB${NC}"
        echo -e "  • Optimized: ${YELLOW}${NEW_SIZE_KB} KB${NC}"
        echo -e "  • Saved: ${YELLOW}${SAVED_KB} KB (${PERCENTAGE}%)${NC}"
        
        # Calculate cost savings
        echo -e "\n${BLUE}💰 COST IMPACT${NC}"
        echo "=============="
        
        # Get deployment costs
        echo -e "${GREEN}🧮 Calculating new deployment cost...${NC}"
        NEW_COST_OUTPUT=$(solana rent $NEW_SIZE 2>/dev/null)
        echo "$NEW_COST_OUTPUT"
        
        if [ -n "$ORIGINAL_SIZE" ]; then
            echo -e "\n${GREEN}📊 Original vs Optimized:${NC}"
            echo "  Original size: $ORIGINAL_SIZE_KB KB"
            echo "  Optimized size: $NEW_SIZE_KB KB"
            echo "  Reduction: ${PERCENTAGE}%"
        fi
    fi
else
    echo -e "${RED}❌ Optimized program not found${NC}"
fi

# Additional optimization suggestions
echo -e "\n${BLUE}💡 ADDITIONAL OPTIMIZATIONS${NC}"
echo "============================"

echo -e "${GREEN}🚀 You can also try:${NC}"
echo "  1. Remove unused dependencies from Cargo.toml"
echo "  2. Use conditional compilation for debug code"
echo "  3. Optimize data structures (see SOLANA_COST_OPTIMIZATION.md)"

# Show dependency analysis if cargo-bloat is available
if command -v cargo-bloat &> /dev/null; then
    echo -e "\n${BLUE}📊 DEPENDENCY ANALYSIS${NC}"
    echo "======================"
    echo -e "${GREEN}Top space-consuming crates:${NC}"
    cargo bloat --release --crates -n 5
else
    echo -e "\n${YELLOW}💡 Install cargo-bloat for dependency analysis:${NC}"
    echo "   cargo install cargo-bloat"
fi

# UPX compression option
echo -e "\n${BLUE}⚡ EXPERIMENTAL: UPX COMPRESSION${NC}"
echo "=================================="

if command -v upx &> /dev/null; then
    echo -e "${YELLOW}⚠️  UPX compression available (EXPERIMENTAL)${NC}"
    echo -e "${RED}Warning: This may break program verification!${NC}"
    echo ""
    read -p "Do you want to try UPX compression? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp "target/deploy/solana_mafia.so" "target/deploy/solana_mafia.so.backup"
        upx --best --lzma "target/deploy/solana_mafia.so"
        
        UPX_SIZE=$(stat -f%z "target/deploy/solana_mafia.so" 2>/dev/null || stat -c%s "target/deploy/solana_mafia.so" 2>/dev/null)
        UPX_SIZE_KB=$((UPX_SIZE / 1024))
        
        echo -e "${GREEN}UPX compressed size: ${YELLOW}${UPX_SIZE_KB} KB${NC}"
        echo -e "${RED}⚠️  Test thoroughly before deploying!${NC}"
        echo -e "${YELLOW}Backup saved as: target/deploy/solana_mafia.so.backup${NC}"
    fi
else
    echo -e "${YELLOW}💡 Install UPX for extreme compression (risky):${NC}"
    echo "   macOS: brew install upx"
    echo "   Ubuntu: apt install upx-ucl"
fi

echo -e "\n${BLUE}🎉 OPTIMIZATION COMPLETE!${NC}"
echo "========================="
echo -e "${GREEN}📋 Summary:${NC}"
echo "  • Backup created: $BACKUP_FILE"
echo "  • Compiler optimizations applied"
echo "  • Program rebuilt with size optimizations"
echo ""
echo -e "${YELLOW}🚀 Next steps:${NC}"
echo "  1. Test the optimized program thoroughly"
echo "  2. Deploy to devnet first: anchor deploy --provider.cluster devnet"
echo "  3. Run './scripts/analyze-program-size.sh' to see final results"
echo ""
echo -e "${BLUE}📖 For more optimizations, see: SOLANA_COST_OPTIMIZATION.md${NC}"
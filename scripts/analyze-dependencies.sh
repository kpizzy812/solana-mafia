#!/bin/bash

# Manual Dependency Analysis Script
# Analyzes Cargo.toml dependencies and checks if they're actually used in source code

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'   
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 MANUAL DEPENDENCY ANALYSIS${NC}"
echo "=================================="

CARGO_TOML="programs/solana-mafia/Cargo.toml"
SRC_DIR="programs/solana-mafia/src"

if [ ! -f "$CARGO_TOML" ]; then
    echo -e "${RED}❌ Cargo.toml not found at $CARGO_TOML${NC}"
    exit 1
fi

if [ ! -d "$SRC_DIR" ]; then
    echo -e "${RED}❌ Source directory not found at $SRC_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}📋 Analyzing dependencies in: $CARGO_TOML${NC}"
echo -e "${GREEN}🔍 Searching in source code: $SRC_DIR${NC}"
echo ""

# Extract dependencies from Cargo.toml
echo -e "${BLUE}📦 CURRENT DEPENDENCIES:${NC}"
echo "========================"

# Get dependencies section (more robust extraction)
DEPS=$(sed -n '/^\[dependencies\]/,/^\[/p' "$CARGO_TOML" | grep -E '^[a-zA-Z0-9_-]+ *=' | head -20)

if [ -z "$DEPS" ]; then
    echo -e "${YELLOW}⚠️  No dependencies found or unusual format${NC}"
    exit 1
fi

echo "$DEPS"
echo ""

# Analyze each dependency
echo -e "${BLUE}🕵️  USAGE ANALYSIS:${NC}"
echo "=================="

UNUSED_DEPS=()
USED_DEPS=()
TOTAL_DEPS=0

# Process each dependency
while IFS= read -r line; do
    if [[ $line =~ ^([a-zA-Z0-9_-]+) ]]; then
        DEP_NAME="${BASH_REMATCH[1]}"
        TOTAL_DEPS=$((TOTAL_DEPS + 1))
        
        echo -e "${CYAN}🔍 Checking: ${YELLOW}$DEP_NAME${NC}"
        
        # Convert dash to underscore for Rust imports
        RUST_NAME="${DEP_NAME//-/_}"
        
        # Search for the dependency in source code (both dash and underscore versions)
        MATCHES=$(rg -c "$DEP_NAME|$RUST_NAME" "$SRC_DIR" 2>/dev/null || echo "0")
        USE_MATCHES=$(rg -c "use.*($DEP_NAME|$RUST_NAME)" "$SRC_DIR" 2>/dev/null || echo "0")
        EXTERN_MATCHES=$(rg -c "extern.*($DEP_NAME|$RUST_NAME)" "$SRC_DIR" 2>/dev/null || echo "0")
        
        # Special cases for common dependency patterns
        case "$DEP_NAME" in
            "anchor-lang")
                SPECIAL_MATCHES=$(rg -c "#\[program\]|use anchor_lang|anchor_lang::|prelude::" "$SRC_DIR" 2>/dev/null || echo "0")
                MATCHES=$((MATCHES + SPECIAL_MATCHES))
                ;;
            "anchor-spl")
                SPECIAL_MATCHES=$(rg -c "use anchor_spl|anchor_spl::|token::|metadata::" "$SRC_DIR" 2>/dev/null || echo "0")
                MATCHES=$((MATCHES + SPECIAL_MATCHES))
                ;;
            "serde")
                SPECIAL_MATCHES=$(rg -c "#\[derive.*Serialize|#\[derive.*Deserialize|use serde::|Serialize|Deserialize" "$SRC_DIR" 2>/dev/null || echo "0")
                MATCHES=$((MATCHES + SPECIAL_MATCHES))
                ;;
        esac
        
        TOTAL_MATCHES=$((MATCHES + USE_MATCHES + EXTERN_MATCHES))
        
        if [ "$TOTAL_MATCHES" -gt 0 ]; then
            echo -e "  ✅ ${GREEN}USED${NC} (${TOTAL_MATCHES} references)"
            USED_DEPS+=("$DEP_NAME")
        else
            echo -e "  ❌ ${RED}UNUSED${NC} (0 references)"
            UNUSED_DEPS+=("$DEP_NAME")
        fi
        
        # Show some actual matches for verification
        if [ "$TOTAL_MATCHES" -gt 0 ] && [ "$TOTAL_MATCHES" -lt 20 ]; then
            echo -e "    ${YELLOW}Sample matches:${NC}"
            rg -n "$DEP_NAME|$RUST_NAME" "$SRC_DIR" 2>/dev/null | head -3 | sed 's/^/      /' || true
        fi
        echo ""
    fi
done <<< "$DEPS"

# Summary
echo -e "${BLUE}📊 ANALYSIS SUMMARY${NC}"
echo "==================="
echo -e "${GREEN}✅ Used dependencies: ${#USED_DEPS[@]}${NC}"
echo -e "${RED}❌ Potentially unused: ${#UNUSED_DEPS[@]}${NC}"
echo -e "${CYAN}📦 Total analyzed: $TOTAL_DEPS${NC}"
echo ""

if [ ${#USED_DEPS[@]} -gt 0 ]; then
    echo -e "${GREEN}✅ USED DEPENDENCIES:${NC}"
    for dep in "${USED_DEPS[@]}"; do
        echo "  • $dep"
    done
    echo ""
fi

if [ ${#UNUSED_DEPS[@]} -gt 0 ]; then
    echo -e "${RED}❌ POTENTIALLY UNUSED DEPENDENCIES:${NC}"
    for dep in "${UNUSED_DEPS[@]}"; do
        echo -e "  • ${RED}$dep${NC}"
    done
    echo ""
    
    echo -e "${YELLOW}⚠️  MANUAL VERIFICATION NEEDED:${NC}"
    echo "=================================="
    echo "Some dependencies might be used in:"
    echo "• Macro expansions (not visible in source)"
    echo "• Build scripts (build.rs)"
    echo "• Feature flags or conditional compilation"
    echo "• Transitive dependencies (required by other deps)"
    echo ""
    
    echo -e "${BLUE}💡 NEXT STEPS:${NC}"
    echo "=============="
    echo "1. Double-check each 'unused' dependency manually"
    echo "2. Try commenting out suspicious dependencies temporarily"
    echo "3. Run 'anchor build' to see if anything breaks"
    echo "4. If build succeeds, the dependency is likely unused"
    echo ""
    
    # Generate removal commands
    echo -e "${BLUE}🗑️  POTENTIAL REMOVAL CANDIDATES:${NC}"
    echo "=================================="
    for dep in "${UNUSED_DEPS[@]}"; do
        echo "# To remove $dep, comment out this line in $CARGO_TOML:"
        grep "^$dep" "$CARGO_TOML" | sed "s/^/# /"
    done
    echo ""
    
    # Calculate potential savings
    if [ ${#UNUSED_DEPS[@]} -gt 0 ]; then
        SAVINGS_PERCENT=$(echo "scale=1; (${#UNUSED_DEPS[@]} * 100) / $TOTAL_DEPS" | bc -l 2>/dev/null || echo "N/A")
        echo -e "${GREEN}💰 POTENTIAL SAVINGS:${NC}"
        echo "===================="
        echo "• Removing ${#UNUSED_DEPS[@]} of $TOTAL_DEPS dependencies"
        echo "• Estimated binary size reduction: 5-15%"
        echo "• Estimated compilation time improvement: 10-30%"
        echo ""
    fi
else
    echo -e "${GREEN}🎉 ALL DEPENDENCIES APPEAR TO BE USED!${NC}"
    echo ""
fi

# Advanced analysis suggestions
echo -e "${BLUE}🚀 ADVANCED OPTIMIZATION SUGGESTIONS:${NC}"
echo "====================================="
echo "1. Check for feature flags that can be disabled:"
echo "   rg 'features.*=' $CARGO_TOML"
echo ""
echo "2. Look for default-features that can be turned off:"
echo "   # Add 'default-features = false' to heavy dependencies"
echo ""
echo "3. Check dependency versions for bloat:"
echo "   # Ensure you're using the latest, most optimized versions"
echo ""

echo -e "${GREEN}✅ Analysis complete!${NC}"
echo ""
echo -e "${YELLOW}📋 To test removal safety:${NC}"
echo "1. Make backup: cp $CARGO_TOML ${CARGO_TOML}.backup"
echo "2. Comment out suspected unused deps"
echo "3. Run: anchor build"
echo "4. If successful: dependency was unused!"
echo "5. If failed: restore and investigate further"
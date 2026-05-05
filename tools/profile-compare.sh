#!/bin/bash

################################################################################
# System Profile Comparator
# Compare multiple system profiles to identify hardware/config differences
################################################################################

set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

print_header() {
    echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN} $1${NC}"
    echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════${NC}\n"
}

compare_sections() {
    local file1="$1"
    local file2="$2"
    local section="$3"
    
    echo -e "${YELLOW}Comparing: $section${NC}"
    
    # Extract section from both files
    local tmp1=$(mktemp)
    local tmp2=$(mktemp)
    
    sed -n "/^╔.*$section/,/^╔/p" "$file1" | head -n -1 > "$tmp1"
    sed -n "/^╔.*$section/,/^╔/p" "$file2" | head -n -1 > "$tmp2"
    
    if ! diff -u "$tmp1" "$tmp2" > /dev/null 2>&1; then
        echo -e "${RED}[x] Differences found${NC}"
        diff -u "$tmp1" "$tmp2" | head -50
    else
        echo -e "${GREEN}[ok] Identical${NC}"
    fi
    
    rm -f "$tmp1" "$tmp2"
    echo ""
}

quick_compare() {
    local file1="$1"
    local file2="$2"
    
    print_header "QUICK COMPARISON"
    
    echo -e "${BOLD}File 1:${NC} $(basename $file1)"
    echo -e "${BOLD}File 2:${NC} $(basename $file2)"
    echo ""
    
    # CPU comparison
    echo -e "${CYAN}CPU:${NC}"
    grep "Model name:" "$file1" 2>/dev/null || echo "N/A"
    grep "Model name:" "$file2" 2>/dev/null || echo "N/A"
    echo ""
    
    # GPU comparison
    echo -e "${CYAN}GPU:${NC}"
    grep -A5 "GRAPHICS INFORMATION" "$file1" | grep -E "(VGA|3D)" | head -3
    grep -A5 "GRAPHICS INFORMATION" "$file2" | grep -E "(VGA|3D)" | head -3
    echo ""
    
    # RAM comparison
    echo -e "${CYAN}Memory:${NC}"
    grep "Mem:" "$file1" | head -1
    grep "Mem:" "$file2" | head -1
    echo ""
    
    # Kernel comparison
    echo -e "${CYAN}Kernel:${NC}"
    grep "Kernel:" "$file1"
    grep "Kernel:" "$file2"
    echo ""
}

main() {
    if [ $# -lt 2 ]; then
        echo "Usage: $0 <profile1> <profile2>"
        echo "Example: $0 system-profile-20240101.txt system-profile-20240102.txt"
        exit 1
    fi
    
    local file1="$1"
    local file2="$2"
    
    if [ ! -f "$file1" ] || [ ! -f "$file2" ]; then
        echo "Error: One or both files not found"
        exit 1
    fi
    
    print_header "SYSTEM PROFILE COMPARISON"
    
    quick_compare "$file1" "$file2"
    
    # Detailed section comparison
    print_header "DETAILED SECTION COMPARISON"
    
    sections=(
        "CPU INFORMATION"
        "MEMORY INFORMATION"
        "GRAPHICS INFORMATION"
        "IOMMU GROUPS"
        "LOADED KERNEL MODULES"
    )
    
    for section in "${sections[@]}"; do
        compare_sections "$file1" "$file2" "$section"
    done
}

main "$@"

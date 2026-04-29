#!/bin/bash

################################################################################
# Run All Profilers - Simple Chain Runner
# Executes all profiling tools consecutively
################################################################################

set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect real user and home directory (even when running with sudo)
if [ -n "${SUDO_USER:-}" ]; then
    REAL_USER="$SUDO_USER"
    REAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    REAL_USER="${USER:-$(whoami)}"
    REAL_HOME="${HOME:-$(eval echo ~$REAL_USER)}"
fi

readonly RUN_DIR="$REAL_HOME/profiler-run-$(date +%Y%m%d_%H%M%S)"

print_banner() {
    clear
    echo -e "${BOLD}${CYAN}"
    cat << 'EOF'
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘              SYSTEM PROFILER - CHAIN RUNNER                   â•‘
â•‘           Running All Tools Consecutively                     â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
EOF
    echo -e "${NC}\n"
}

print_step() {
    echo -e "\n${BOLD}${CYAN}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    echo -e "${BOLD}${CYAN}â–¶ $1${NC}"
    echo -e "${BOLD}${CYAN}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}\n"
}

print_info() {
    echo -e "${BLUE}â„¹${NC} $1"
}

print_success() {
    echo -e "${GREEN}âœ“${NC} $1"
}

print_error() {
    echo -e "${RED}âœ—${NC} $1"
}

wait_for_user() {
    echo ""
    read -p "Press Enter to continue to next tool..." -r
}

check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}âš  Not running as root${NC}"
        echo "Some tools will have limited functionality without sudo."
        echo ""
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Exiting. Run with: sudo $0"
            exit 1
        fi
    fi
}

create_output_dir() {
    mkdir -p "$RUN_DIR"
    
    # Set proper ownership if running with sudo
    if [ -n "${SUDO_USER:-}" ]; then
        chown "$SUDO_USER:$(id -gn "$SUDO_USER")" "$RUN_DIR"
    fi
    
    print_success "Created output directory: $RUN_DIR"
}

run_quick_summary() {
    print_step "STEP 1/4: Quick System Summary (30 seconds)"
    
    print_info "Running quick health check..."
    echo ""
    
    if [ -f "$SCRIPT_DIR/quick-summary.sh" ]; then
        "$SCRIPT_DIR/quick-summary.sh" | tee "$RUN_DIR/01-quick-summary.txt"
        print_success "Quick summary saved to: 01-quick-summary.txt"
    else
        print_error "quick-summary.sh not found!"
        return 1
    fi
}

run_iommu_visualizer() {
    print_step "STEP 2/4: IOMMU Group Analysis (1-2 minutes)"
    
    print_info "Analyzing IOMMU groups for GPU passthrough..."
    echo ""
    
    if [ -f "$SCRIPT_DIR/iommu-visualizer.sh" ]; then
        "$SCRIPT_DIR/iommu-visualizer.sh" --no-menu 2>&1 | tee "$RUN_DIR/02-iommu-analysis.txt"
        print_success "IOMMU analysis saved to: 02-iommu-analysis.txt"
    else
        print_error "iommu-visualizer.sh not found!"
        return 1
    fi
}

run_system_profiler() {
    print_step "STEP 3/4: Full System Profile (3-5 minutes)"
    
    print_info "Collecting comprehensive system information..."
    print_info "This includes: hardware, drivers, packages, BIOS, and more..."
    echo ""
    
    if [ -f "$SCRIPT_DIR/system-profiler.sh" ]; then
        "$SCRIPT_DIR/system-profiler.sh" > /dev/null 2>&1
        
        # Copy the latest profile to our run directory
        local latest_profile=$(ls -t ~/system-profile/system-profile-*.txt 2>/dev/null | head -1)
        if [ -f "$latest_profile" ]; then
            cp "$latest_profile" "$RUN_DIR/03-full-system-profile.txt"
            print_success "Full profile saved to: 03-full-system-profile.txt"
            print_info "Original also at: $latest_profile"
        else
            print_error "Profile generation failed!"
            return 1
        fi
    else
        print_error "system-profiler.sh not found!"
        return 1
    fi
}

generate_summary() {
    print_step "STEP 4/4: Generating Summary Report"
    
    local summary="$RUN_DIR/00-SUMMARY.txt"
    
    print_info "Creating consolidated summary..."
    
    {
        echo "â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—"
        echo "â•‘              PROFILER RUN SUMMARY                             â•‘"
        echo "â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•"
        echo ""
        echo "Run Date: $(date)"
        echo "Hostname: $(hostname)"
        echo "User: $(whoami)"
        echo "Output Directory: $RUN_DIR"
        echo ""
        echo "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"
        echo "FILES GENERATED"
        echo "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"
        echo ""
        ls -lh "$RUN_DIR"/*.txt | awk '{print $9, "("$5")"}'
        echo ""
        echo "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"
        echo "QUICK HIGHLIGHTS"
        echo "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"
        echo ""
        
        # Extract key info from quick summary
        if [ -f "$RUN_DIR/01-quick-summary.txt" ]; then
            echo "=== SYSTEM ==="
            grep -A4 "SYSTEM" "$RUN_DIR/01-quick-summary.txt" | tail -4 || echo "N/A"
            echo ""
            
            echo "=== CPU ==="
            grep -A3 "CPU" "$RUN_DIR/01-quick-summary.txt" | tail -3 || echo "N/A"
            echo ""
            
            echo "=== MEMORY ==="
            grep -A3 "MEMORY" "$RUN_DIR/01-quick-summary.txt" | tail -3 || echo "N/A"
            echo ""
            
            echo "=== GRAPHICS ==="
            grep -A5 "GRAPHICS" "$RUN_DIR/01-quick-summary.txt" | tail -5 || echo "N/A"
            echo ""
        fi
        
        # Extract IOMMU highlights
        if [ -f "$RUN_DIR/02-iommu-analysis.txt" ]; then
            echo "=== IOMMU/PASSTHROUGH ==="
            grep -A5 "Summary" "$RUN_DIR/02-iommu-analysis.txt" | tail -5 || echo "N/A"
            echo ""
            
            if grep -q "Isolated GPUs" "$RUN_DIR/02-iommu-analysis.txt"; then
                echo "âœ“ GPU PASSTHROUGH: Capable (isolated GPU found)"
            else
                echo "âš  GPU PASSTHROUGH: Limited (GPU not isolated)"
            fi
            echo ""
        fi
        
        echo "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"
        echo "READINESS CHECK"
        echo "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"
        echo ""
        
        if grep -q "System ready for MiOS-Build" "$RUN_DIR/01-quick-summary.txt" 2>/dev/null; then
            echo "âœ“ VERDICT: System appears ready for MiOS-Build"
        else
            echo "âš  VERDICT: Check detailed reports for issues"
        fi
        
        echo ""
        echo "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"
        echo "NEXT STEPS"
        echo "â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”â”"
        echo ""
        echo "1. Review this summary: cat $summary"
        echo "2. Check full profile: less $RUN_DIR/03-full-system-profile.txt"
        echo "3. Examine IOMMU groups: cat $RUN_DIR/02-iommu-analysis.txt"
        echo ""
        echo "Search for specific info:"
        echo "  grep -i 'nvidia' $RUN_DIR/*.txt"
        echo "  grep 'IOMMU Group' $RUN_DIR/*.txt"
        echo "  grep -i 'virtualization' $RUN_DIR/*.txt"
        echo ""
        echo "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•"
        
    } > "$summary"
    
    print_success "Summary report created: 00-SUMMARY.txt"
}

show_results() {
    echo ""
    print_step "ALL PROFILERS COMPLETED!"
    
    echo -e "${BOLD}${GREEN}âœ“ All tools executed successfully!${NC}\n"
    
    echo -e "${BOLD}Output Directory:${NC}"
    echo -e "  ${CYAN}$RUN_DIR${NC}\n"
    
    echo -e "${BOLD}Files Generated:${NC}"
    ls -1 "$RUN_DIR"/*.txt | while read -r file; do
        local size=$(du -h "$file" | cut -f1)
        echo -e "  ${GREEN}âœ“${NC} $(basename "$file") ${CYAN}($size)${NC}"
    done
    
    echo ""
    echo -e "${BOLD}View Summary:${NC}"
    echo -e "  ${YELLOW}cat $RUN_DIR/00-SUMMARY.txt${NC}"
    echo ""
    echo -e "${BOLD}View Full Profile:${NC}"
    echo -e "  ${YELLOW}less $RUN_DIR/03-full-system-profile.txt${NC}"
    echo ""
    
    # Ask if user wants to view summary now
    read -p "Display summary now? (Y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo ""
        cat "$RUN_DIR/00-SUMMARY.txt"
    fi
}

main() {
    print_banner
    
    echo -e "${BOLD}This script will run all profiling tools consecutively:${NC}"
    echo -e "  1. Quick Summary      ${CYAN}(~30 seconds)${NC}"
    echo -e "  2. IOMMU Analyzer     ${CYAN}(~1-2 minutes)${NC}"
    echo -e "  3. Full System Profiler ${CYAN}(~3-5 minutes)${NC}"
    echo -e "  4. Generate Summary Report"
    echo ""
    echo -e "${BOLD}Total estimated time: 5-8 minutes${NC}"
    echo ""
    
    check_sudo
    
    read -p "Ready to start? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
    
    echo ""
    create_output_dir
    
    # Run each tool
    run_quick_summary
    sleep 2
    
    run_iommu_visualizer
    sleep 2
    
    run_system_profiler
    sleep 2
    
    generate_summary
    
    # Ensure all files are owned by the real user
    if [ -n "${SUDO_USER:-}" ]; then
        chown -R "$SUDO_USER:$(id -gn "$SUDO_USER")" "$RUN_DIR"
    fi
    
    show_results
    
    echo ""
    echo -e "${BOLD}${CYAN}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    echo -e "${BOLD}${CYAN}                    RUN COMPLETE!${NC}"
    echo -e "${BOLD}${CYAN}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}\n"
}

main "$@"

exit 0

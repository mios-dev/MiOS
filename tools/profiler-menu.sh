#!/bin/bash

################################################################################
# Interactive Profiler Menu
# Choose which profilers to run with an interactive menu
################################################################################

set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
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

readonly OUTPUT_DIR="$REAL_HOME/profiler-output"

# Track what's been run
QUICK_SUMMARY_DONE=false
IOMMU_DONE=false
FULL_PROFILE_DONE=false
LATEST_PROFILE=""

show_banner() {
    clear
    echo -e "${BOLD}${CYAN}"
    cat << 'EOF'
â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
â•‘           INTERACTIVE SYSTEM PROFILER MENU                    â•‘
â•‘              Choose Your Tools                                â•‘
â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
EOF
    echo -e "${NC}\n"
}

show_menu() {
    echo -e "${BOLD}${CYAN}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    echo -e "${BOLD}                    MAIN MENU${NC}"
    echo -e "${BOLD}${CYAN}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}\n"
    
    # Show status indicators
    if [ "$QUICK_SUMMARY_DONE" = true ]; then
        echo -e "  ${GREEN}âœ“${NC} 1) Quick System Summary        ${CYAN}[COMPLETED]${NC}"
    else
        echo -e "    1) Quick System Summary        ${YELLOW}[~30 seconds]${NC}"
    fi
    
    if [ "$IOMMU_DONE" = true ]; then
        echo -e "  ${GREEN}âœ“${NC} 2) IOMMU Group Analyzer        ${CYAN}[COMPLETED]${NC}"
    else
        echo -e "    2) IOMMU Group Analyzer        ${YELLOW}[~1-2 minutes]${NC}"
    fi
    
    if [ "$FULL_PROFILE_DONE" = true ]; then
        echo -e "  ${GREEN}âœ“${NC} 3) Full System Profiler        ${CYAN}[COMPLETED]${NC}"
    else
        echo -e "    3) Full System Profiler        ${YELLOW}[~3-5 minutes]${NC}"
    fi
    
    echo ""
    echo -e "    4) ${BOLD}Run All Tools Consecutively${NC}  ${YELLOW}[~5-8 minutes]${NC}"
    echo ""
    echo -e "${BOLD}${MAGENTA}â•â•â• Results & Comparison â•â•â•${NC}"
    echo -e "    5) View Latest Results"
    echo -e "    6) Compare Two Profiles"
    echo -e "    7) Open Output Directory"
    echo ""
    echo -e "${BOLD}${BLUE}â•â•â• Help & Info â•â•â•${NC}"
    echo -e "    h) Help - Tool Descriptions"
    echo -e "    s) System Status Check"
    echo ""
    echo -e "    q) Quit"
    echo ""
    echo -e "${CYAN}â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€${NC}"
}

show_help() {
    clear
    show_banner
    echo -e "${BOLD}${YELLOW}TOOL DESCRIPTIONS${NC}\n"
    
    echo -e "${BOLD}${CYAN}1) Quick System Summary${NC}"
    echo "   Fast 30-second health check of your system"
    echo "   Shows: CPU, RAM, GPU, virtualization status, IOMMU availability"
    echo "   Use when: Quick compatibility check, daily monitoring"
    echo ""
    
    echo -e "${BOLD}${CYAN}2) IOMMU Group Analyzer${NC}"
    echo "   Detailed PCIe/IOMMU group visualization"
    echo "   Shows: All IOMMU groups, GPU isolation, passthrough readiness"
    echo "   Use when: Planning GPU passthrough, checking PCIe topology"
    echo ""
    
    echo -e "${BOLD}${CYAN}3) Full System Profiler${NC}"
    echo "   Comprehensive system documentation (22+ sections)"
    echo "   Collects: Hardware, drivers, packages, BIOS, sensors, everything!"
    echo "   Use when: Pre-installation baseline, troubleshooting, documentation"
    echo ""
    
    echo -e "${BOLD}${CYAN}4) Run All Tools${NC}"
    echo "   Executes all three tools in sequence with summary report"
    echo "   Creates timestamped directory with all results"
    echo "   Use when: Complete system assessment needed"
    echo ""
    
    echo -e "${BOLD}${CYAN}6) Compare Profiles${NC}"
    echo "   Side-by-side comparison of two system profiles"
    echo "   Shows: What changed between two points in time"
    echo "   Use when: Troubleshooting issues, tracking changes after updates"
    echo ""
    
    read -p "Press Enter to return to menu..." -r
}

run_quick_summary() {
    clear
    show_banner
    echo -e "${BOLD}${YELLOW}Running Quick System Summary...${NC}\n"
    
    mkdir -p "$OUTPUT_DIR"
    
    # Set proper ownership if running with sudo
    if [ -n "${SUDO_USER:-}" ]; then
        chown "$SUDO_USER:$(id -gn "$SUDO_USER")" "$OUTPUT_DIR"
    fi
    
    if [ -f "$SCRIPT_DIR/quick-summary.sh" ]; then
        "$SCRIPT_DIR/quick-summary.sh" | tee "$OUTPUT_DIR/quick-summary-$(date +%Y%m%d_%H%M%S).txt"
        QUICK_SUMMARY_DONE=true
        echo ""
        echo -e "${GREEN}âœ“ Complete!${NC} Saved to: $OUTPUT_DIR"
    else
        echo -e "${RED}âœ— Error: quick-summary.sh not found!${NC}"
    fi
    
    echo ""
    read -p "Press Enter to return to menu..." -r
}

run_iommu_analyzer() {
    clear
    show_banner
    echo -e "${BOLD}${YELLOW}Running IOMMU Group Analyzer...${NC}\n"
    
    mkdir -p "$OUTPUT_DIR"
    
    # Set proper ownership if running with sudo
    if [ -n "${SUDO_USER:-}" ]; then
        chown "$SUDO_USER:$(id -gn "$SUDO_USER")" "$OUTPUT_DIR"
    fi
    
    if [ -f "$SCRIPT_DIR/iommu-visualizer.sh" ]; then
        "$SCRIPT_DIR/iommu-visualizer.sh" --no-menu 2>&1 | tee "$OUTPUT_DIR/iommu-analysis-$(date +%Y%m%d_%H%M%S).txt"
        IOMMU_DONE=true
        echo ""
        echo -e "${GREEN}âœ“ Complete!${NC} Saved to: $OUTPUT_DIR"
    else
        echo -e "${RED}âœ— Error: iommu-visualizer.sh not found!${NC}"
    fi
    
    echo ""
    read -p "Press Enter to return to menu..." -r
}

run_full_profiler() {
    clear
    show_banner
    echo -e "${BOLD}${YELLOW}Running Full System Profiler...${NC}"
    echo -e "${YELLOW}This will take 3-5 minutes...${NC}\n"
    
    if [ -f "$SCRIPT_DIR/system-profiler.sh" ]; then
        "$SCRIPT_DIR/system-profiler.sh"
        
        # Get the latest profile
        LATEST_PROFILE=$(ls -t ~/system-profile/system-profile-*.txt 2>/dev/null | head -1)
        
        if [ -f "$LATEST_PROFILE" ]; then
            FULL_PROFILE_DONE=true
            echo ""
            echo -e "${GREEN}âœ“ Complete!${NC}"
            echo -e "Profile saved to: ${CYAN}$LATEST_PROFILE${NC}"
        else
            echo -e "${RED}âœ— Error: Profile generation failed!${NC}"
        fi
    else
        echo -e "${RED}âœ— Error: system-profiler.sh not found!${NC}"
    fi
    
    echo ""
    read -p "Press Enter to return to menu..." -r
}

run_all_tools() {
    clear
    show_banner
    echo -e "${BOLD}${YELLOW}Running All Tools Consecutively...${NC}\n"
    
    echo "This will:"
    echo "  1. Run quick summary"
    echo "  2. Analyze IOMMU groups"
    echo "  3. Create full system profile"
    echo "  4. Generate summary report"
    echo ""
    echo "Estimated time: 5-8 minutes"
    echo ""
    
    read -p "Continue? (Y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Nn]$ ]]; then
        return
    fi
    
    if [ -f "$SCRIPT_DIR/run-all-profilers.sh" ]; then
        "$SCRIPT_DIR/run-all-profilers.sh"
        QUICK_SUMMARY_DONE=true
        IOMMU_DONE=true
        FULL_PROFILE_DONE=true
    else
        echo -e "${RED}âœ— Error: run-all-profilers.sh not found!${NC}"
        echo ""
        echo "Running tools individually instead..."
        echo ""
        run_quick_summary
        run_iommu_analyzer
        run_full_profiler
    fi
    
    echo ""
    read -p "Press Enter to return to menu..." -r
}

view_results() {
    clear
    show_banner
    echo -e "${BOLD}${YELLOW}Latest Results${NC}\n"
    
    # Check for recent files
    local has_results=false
    
    if [ -d "$OUTPUT_DIR" ] && [ "$(ls -A $OUTPUT_DIR 2>/dev/null)" ]; then
        echo -e "${BOLD}Recent Output Files:${NC}"
        ls -lht "$OUTPUT_DIR"/*.txt 2>/dev/null | head -10 | awk '{print "  "$9" ("$5")"}'
        echo ""
        has_results=true
    fi
    
    if [ -d ~/system-profile ] && [ "$(ls -A ~/system-profile 2>/dev/null)" ]; then
        echo -e "${BOLD}System Profiles:${NC}"
        ls -lht ~/system-profile/system-profile-*.txt 2>/dev/null | head -5 | awk '{print "  "$9" ("$5")"}'
        echo ""
        has_results=true
    fi
    
    if [ -d ~/mios-build-assessment-* 2>/dev/null ]; then
        echo -e "${BOLD}Assessment Reports:${NC}"
        ls -dlt ~/mios-build-assessment-* 2>/dev/null | head -5 | awk '{print "  "$9}'
        echo ""
        has_results=true
    fi
    
    if [ "$has_results" = false ]; then
        echo -e "${YELLOW}No results found yet.${NC}"
        echo "Run a profiler first!"
    else
        echo ""
        echo -e "${CYAN}View a file:${NC}"
        echo "  less [filename]"
        echo ""
        echo -e "${CYAN}Search files:${NC}"
        echo "  grep -i 'search-term' $OUTPUT_DIR/*.txt"
    fi
    
    echo ""
    read -p "Press Enter to return to menu..." -r
}

compare_profiles() {
    clear
    show_banner
    echo -e "${BOLD}${YELLOW}Compare Two System Profiles${NC}\n"
    
    # List available profiles
    if [ -d ~/system-profile ]; then
        local profiles=($(ls -t ~/system-profile/system-profile-*.txt 2>/dev/null))
        
        if [ ${#profiles[@]} -lt 2 ]; then
            echo -e "${YELLOW}Need at least 2 profiles to compare.${NC}"
            echo "Only ${#profiles[@]} profile(s) found."
            echo ""
            echo "Run the full system profiler multiple times to create profiles."
            read -p "Press Enter to return to menu..." -r
            return
        fi
        
        echo -e "${BOLD}Available Profiles:${NC}\n"
        for i in "${!profiles[@]}"; do
            local date=$(stat -c %y "${profiles[$i]}" 2>/dev/null | cut -d' ' -f1)
            echo "  $((i+1))) $(basename "${profiles[$i]}") ($date)"
        done
        
        echo ""
        read -p "Select first profile (1-${#profiles[@]}): " first
        read -p "Select second profile (1-${#profiles[@]}): " second
        
        if [ "$first" -ge 1 ] && [ "$first" -le "${#profiles[@]}" ] && \
           [ "$second" -ge 1 ] && [ "$second" -le "${#profiles[@]}" ]; then
            
            echo ""
            echo -e "${BOLD}Comparing profiles...${NC}\n"
            
            if [ -f "$SCRIPT_DIR/profile-compare.sh" ]; then
                "$SCRIPT_DIR/profile-compare.sh" \
                    "${profiles[$((first-1))]}" \
                    "${profiles[$((second-1))]}"
            else
                echo -e "${RED}âœ— Error: profile-compare.sh not found!${NC}"
            fi
        else
            echo -e "${RED}Invalid selection!${NC}"
        fi
    else
        echo -e "${YELLOW}No profiles found.${NC}"
        echo "Run the full system profiler first."
    fi
    
    echo ""
    read -p "Press Enter to return to menu..." -r
}

open_output_dir() {
    mkdir -p "$OUTPUT_DIR"
    
    echo ""
    echo -e "${BOLD}Output Directories:${NC}"
    echo -e "  Quick/IOMMU: ${CYAN}$OUTPUT_DIR${NC}"
    echo -e "  Full Profiles: ${CYAN}~/system-profile/${NC}"
    echo -e "  Assessments: ${CYAN}~/mios-build-assessment-*/${NC}"
    echo ""
    
    if command -v xdg-open >/dev/null 2>&1; then
        read -p "Open $OUTPUT_DIR in file manager? (Y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            xdg-open "$OUTPUT_DIR" 2>/dev/null &
            echo -e "${GREEN}âœ“ Opened!${NC}"
        fi
    else
        echo -e "Location: ${CYAN}$OUTPUT_DIR${NC}"
    fi
    
    echo ""
    read -p "Press Enter to return to menu..." -r
}

check_system_status() {
    clear
    show_banner
    echo -e "${BOLD}${YELLOW}Quick System Status Check${NC}\n"
    
    echo -e "${BOLD}Virtualization:${NC}"
    if grep -q -E '(vmx|svm)' /proc/cpuinfo 2>/dev/null; then
        echo -e "  ${GREEN}âœ“${NC} CPU virtualization enabled"
    else
        echo -e "  ${RED}âœ—${NC} CPU virtualization not detected"
    fi
    
    echo -e "\n${BOLD}IOMMU:${NC}"
    if [ -d /sys/kernel/iommu_groups ]; then
        local groups=$(ls -1 /sys/kernel/iommu_groups/ | wc -l)
        echo -e "  ${GREEN}âœ“${NC} IOMMU enabled ($groups groups)"
    else
        echo -e "  ${RED}âœ—${NC} IOMMU not available"
    fi
    
    echo -e "\n${BOLD}KVM:${NC}"
    if [ -e /dev/kvm ]; then
        echo -e "  ${GREEN}âœ“${NC} KVM available"
    else
        echo -e "  ${RED}âœ—${NC} KVM not available"
    fi
    
    echo -e "\n${BOLD}GPU:${NC}"
    local gpu_count=$(lspci | grep -c -E "VGA|3D" || echo "0")
    if [ "$gpu_count" -gt 0 ]; then
        echo -e "  ${GREEN}âœ“${NC} $gpu_count GPU(s) detected"
        lspci | grep -E "VGA|3D" | while read -r line; do
            echo "    â€¢ ${line#*: }"
        done
    else
        echo -e "  ${YELLOW}âš ${NC} No discrete GPU detected"
    fi
    
    echo -e "\n${BOLD}Memory:${NC}"
    free -h | grep "^Mem:" | awk '{print "  Total: "$2", Available: "$7}'
    
    echo -e "\n${BOLD}Disk Space:${NC}"
    df -h / | tail -1 | awk '{print "  Root: "$4" free / "$2" total ("$5" used)"}'
    
    echo ""
    read -p "Press Enter to return to menu..." -r
}

main() {
    while true; do
        show_banner
        show_menu
        
        read -p "Select option: " choice
        
        case "$choice" in
            1) run_quick_summary ;;
            2) run_iommu_analyzer ;;
            3) run_full_profiler ;;
            4) run_all_tools ;;
            5) view_results ;;
            6) compare_profiles ;;
            7) open_output_dir ;;
            h|H) show_help ;;
            s|S) check_system_status ;;
            q|Q)
                echo ""
                echo -e "${CYAN}Goodbye!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option!${NC}"
                sleep 1
                ;;
        esac
    done
}

main "$@"

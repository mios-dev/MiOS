#!/bin/bash
# run-all-profilers.sh -- execute all profiling tools consecutively
set -euo pipefail

readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect real user/home even under sudo
if [ -n "${SUDO_USER:-}" ]; then
    REAL_USER="$SUDO_USER"
    REAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
else
    REAL_USER="${USER:-$(whoami)}"
    REAL_HOME="${HOME:-$(eval echo ~$REAL_USER)}"
fi

readonly RUN_DIR="$REAL_HOME/profiler-run-$(date +%Y%m%d_%H%M%S)"

print_banner()  { clear; echo -e "${BOLD}${CYAN}SYSTEM PROFILER -- chain runner${NC}\n"; }
print_step()    { echo -e "\n${BOLD}${CYAN}>> $1${NC}"; }
print_info()    { echo -e "${BLUE}i${NC} $1"; }
print_success() { echo -e "${GREEN}+${NC} $1"; }
print_error()   { echo -e "${RED}-${NC} $1"; }

wait_for_user() {
    read -p "Press Enter to continue to next tool..." -r
}

check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${YELLOW}Warning: not running as root -- some tools will be limited.${NC}"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        [[ $REPLY =~ ^[Yy]$ ]] || { echo "Exiting. Run with: sudo $0"; exit 1; }
    fi
}

create_output_dir() {
    mkdir -p "$RUN_DIR"
    if [ -n "${SUDO_USER:-}" ]; then
        chown "$SUDO_USER:$(id -gn "$SUDO_USER")" "$RUN_DIR"
    fi
    print_success "Created output directory: $RUN_DIR"
}

run_quick_summary() {
    print_step "STEP 1/4: Quick System Summary (~30s)"
    if [ -f "$SCRIPT_DIR/quick-summary.sh" ]; then
        "$SCRIPT_DIR/quick-summary.sh" | tee "$RUN_DIR/01-quick-summary.txt"
        print_success "01-quick-summary.txt"
    else
        print_error "quick-summary.sh not found"
        return 1
    fi
}

run_iommu_visualizer() {
    print_step "STEP 2/4: IOMMU Group Analysis (~1-2m)"
    if [ -f "$SCRIPT_DIR/iommu-visualizer.sh" ]; then
        "$SCRIPT_DIR/iommu-visualizer.sh" --no-menu 2>&1 | tee "$RUN_DIR/02-iommu-analysis.txt"
        print_success "02-iommu-analysis.txt"
    else
        print_error "iommu-visualizer.sh not found"
        return 1
    fi
}

run_system_profiler() {
    print_step "STEP 3/4: Full System Profile (~3-5m)"
    if [ -f "$SCRIPT_DIR/system-profiler.sh" ]; then
        "$SCRIPT_DIR/system-profiler.sh" > /dev/null 2>&1
        local latest_profile
        latest_profile=$(ls -t ~/system-profile/system-profile-*.txt 2>/dev/null | head -1)
        if [ -f "$latest_profile" ]; then
            cp "$latest_profile" "$RUN_DIR/03-full-system-profile.txt"
            print_success "03-full-system-profile.txt (orig: $latest_profile)"
        else
            print_error "Profile generation failed"
            return 1
        fi
    else
        print_error "system-profiler.sh not found"
        return 1
    fi
}

generate_summary() {
    print_step "STEP 4/4: Summary Report"
    local summary="$RUN_DIR/00-SUMMARY.txt"
    {
        echo "PROFILER RUN SUMMARY"
        echo "Run Date: $(date)"
        echo "Hostname: $(hostname)"
        echo "User:     $(whoami)"
        echo "Output:   $RUN_DIR"
        echo
        echo "FILES"
        ls -lh "$RUN_DIR"/*.txt | awk '{print $9, "("$5")"}'
        echo
        echo "HIGHLIGHTS"
        if [ -f "$RUN_DIR/01-quick-summary.txt" ]; then
            for sec in SYSTEM CPU MEMORY GRAPHICS; do
                echo "[$sec]"
                grep -A4 "$sec" "$RUN_DIR/01-quick-summary.txt" | tail -4 || echo "N/A"
                echo
            done
        fi
        if [ -f "$RUN_DIR/02-iommu-analysis.txt" ]; then
            echo "[IOMMU/PASSTHROUGH]"
            grep -A5 "Summary" "$RUN_DIR/02-iommu-analysis.txt" | tail -5 || echo "N/A"
            if grep -q "Isolated GPUs" "$RUN_DIR/02-iommu-analysis.txt"; then
                echo "GPU PASSTHROUGH: capable (isolated GPU found)"
            else
                echo "GPU PASSTHROUGH: limited (GPU not isolated)"
            fi
            echo
        fi
        echo "READINESS"
        if grep -q "System ready for MiOS-Build" "$RUN_DIR/01-quick-summary.txt" 2>/dev/null; then
            echo "VERDICT: ready for MiOS-Build"
        else
            echo "VERDICT: check detailed reports for issues"
        fi
        echo
        echo "NEXT STEPS"
        echo "  cat $summary"
        echo "  less $RUN_DIR/03-full-system-profile.txt"
        echo "  cat $RUN_DIR/02-iommu-analysis.txt"
        echo "  grep -i 'nvidia' $RUN_DIR/*.txt"
        echo "  grep 'IOMMU Group' $RUN_DIR/*.txt"
    } > "$summary"
    print_success "00-SUMMARY.txt"
}

show_results() {
    print_step "ALL PROFILERS COMPLETED"
    echo -e "${BOLD}Output: ${CYAN}$RUN_DIR${NC}"
    ls -1 "$RUN_DIR"/*.txt | while read -r file; do
        local size
        size=$(du -h "$file" | cut -f1)
        echo -e "  ${GREEN}+${NC} $(basename "$file") ${CYAN}($size)${NC}"
    done
    echo -e "${BOLD}Summary:${NC} ${YELLOW}cat $RUN_DIR/00-SUMMARY.txt${NC}"
    echo -e "${BOLD}Profile:${NC} ${YELLOW}less $RUN_DIR/03-full-system-profile.txt${NC}"
    read -p "Display summary now? (Y/n) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Nn]$ ]] || cat "$RUN_DIR/00-SUMMARY.txt"
}

main() {
    print_banner
    echo -e "${BOLD}Will run:${NC} quick-summary, iommu-visualizer, system-profiler, summary."
    echo -e "${BOLD}Estimated:${NC} 5-8 minutes."
    check_sudo
    read -p "Ready to start? (Y/n) " -n 1 -r
    echo
    [[ $REPLY =~ ^[Nn]$ ]] && { echo "Cancelled."; exit 0; }
    create_output_dir
    run_quick_summary;     sleep 2
    run_iommu_visualizer;  sleep 2
    run_system_profiler;   sleep 2
    generate_summary
    if [ -n "${SUDO_USER:-}" ]; then
        chown -R "$SUDO_USER:$(id -gn "$SUDO_USER")" "$RUN_DIR"
    fi
    show_results
    echo -e "\n${BOLD}${CYAN}RUN COMPLETE${NC}"
}

main "$@"
exit 0

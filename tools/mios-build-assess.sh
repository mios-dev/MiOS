#!/bin/bash

################################################################################
# MiOS-Build Hardware Assessment Tool
# Automated workflow for complete system analysis
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
readonly ASSESSMENT_DIR="$HOME/mios-build-assessment-$(date +%Y%m%d_%H%M%S)"

print_banner() {
    clear
    echo -e "${BOLD}${CYAN}"
    cat << 'EOF'
╔═══════════════════════════════════════════════════════════════╗
║         MiOS-Build HARDWARE ASSESSMENT TOOL                     ║
║         Complete System Analysis & Compatibility Check        ║
╚═══════════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}\n"
}

print_step() {
    echo -e "\n${BOLD}${YELLOW}▶ $1${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

check_requirements() {
    print_step "Checking Requirements"
    
    local missing=0
    
    if [ "$EUID" -ne 0 ]; then
        print_warning "Not running as root - some information will be limited"
        echo "  Recommended: sudo $0"
        echo ""
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Check for helper scripts
    local scripts=("system-profiler.sh" "iommu-visualizer.sh" "quick-summary.sh")
    for script in "${scripts[@]}"; do
        if [ ! -f "$SCRIPT_DIR/$script" ]; then
            print_error "Missing: $script"
            missing=$((missing + 1))
        else
            print_success "Found: $script"
        fi
    done
    
    if [ $missing -gt 0 ]; then
        print_error "Missing $missing required script(s)"
        exit 1
    fi
    
    print_success "All requirements met"
}

create_assessment_dir() {
    print_step "Creating Assessment Directory"
    
    mkdir -p "$ASSESSMENT_DIR"
    print_success "Created: $ASSESSMENT_DIR"
}

run_quick_summary() {
    print_step "Running Quick Summary (Step 1/3)"
    
    "$SCRIPT_DIR/quick-summary.sh" | tee "$ASSESSMENT_DIR/01-quick-summary.txt"
    
    # Extract readiness status
    if grep -q "System ready for MiOS-Build" "$ASSESSMENT_DIR/01-quick-summary.txt"; then
        print_success "Quick check: System appears ready"
        return 0
    else
        print_warning "Quick check: Issues detected"
        return 1
    fi
}

run_iommu_analysis() {
    print_step "Running IOMMU Analysis (Step 2/3)"
    
    if [ ! -d /sys/kernel/iommu_groups ]; then
        print_warning "IOMMU not available - skipping detailed analysis"
        echo "IOMMU not available on this system" > "$ASSESSMENT_DIR/02-iommu-analysis.txt"
        return 1
    fi
    
    "$SCRIPT_DIR/iommu-visualizer.sh" --no-menu > "$ASSESSMENT_DIR/02-iommu-analysis.txt" 2>&1
    
    # Check for isolated GPUs
    if grep -q "Isolated GPUs" "$ASSESSMENT_DIR/02-iommu-analysis.txt"; then
        print_success "IOMMU check: GPU passthrough capable"
        return 0
    else
        print_warning "IOMMU check: No isolated GPUs found"
        return 1
    fi
}

run_full_profile() {
    print_step "Running Full System Profile (Step 3/3)"
    print_warning "This may take 2-5 minutes..."
    
    "$SCRIPT_DIR/system-profiler.sh" > /dev/null 2>&1
    
    # Copy latest profile to assessment dir
    local latest_profile=$(ls -t ~/system-profile/system-profile-*.txt | head -1)
    if [ -f "$latest_profile" ]; then
        cp "$latest_profile" "$ASSESSMENT_DIR/03-full-profile.txt"
        print_success "Full profile completed"
        return 0
    else
        print_error "Profile generation failed"
        return 1
    fi
}

generate_compatibility_report() {
    print_step "Generating Compatibility Report"
    
    local report="$ASSESSMENT_DIR/00-COMPATIBILITY-REPORT.txt"
    
    {
        echo "╔═══════════════════════════════════════════════════════════════╗"
        echo "║         MiOS-Build COMPATIBILITY REPORT                         ║"
        echo "╚═══════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Generated: $(date)"
        echo "Hostname: $(hostname)"
        echo "Assessment Directory: $ASSESSMENT_DIR"
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "SYSTEM OVERVIEW"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        grep -A4 "SYSTEM" "$ASSESSMENT_DIR/01-quick-summary.txt" | tail -4
        echo ""
        grep -A3 "CPU" "$ASSESSMENT_DIR/01-quick-summary.txt" | tail -3
        echo ""
        grep -A3 "MEMORY" "$ASSESSMENT_DIR/01-quick-summary.txt" | tail -3
        echo ""
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "GRAPHICS & PASSTHROUGH CAPABILITY"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        
        if [ -f "$ASSESSMENT_DIR/02-iommu-analysis.txt" ]; then
            if grep -q "Isolated GPUs" "$ASSESSMENT_DIR/02-iommu-analysis.txt"; then
                echo "✓ GPU PASSTHROUGH: READY"
                echo ""
                grep -A10 "Isolated GPUs" "$ASSESSMENT_DIR/02-iommu-analysis.txt"
            else
                echo "⚠ GPU PASSTHROUGH: LIMITED"
                echo ""
                echo "GPUs are not in isolated IOMMU groups."
                echo "Passthrough may require ACS override patch."
            fi
        else
            echo "✗ GPU PASSTHROUGH: NOT AVAILABLE"
            echo ""
            echo "IOMMU not enabled or not supported."
        fi
        
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "VIRTUALIZATION READINESS"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        grep -A20 "VIRTUALIZATION" "$ASSESSMENT_DIR/01-quick-summary.txt" | grep -E "(IOMMU|KVM|GPU Grp|CPU Virt)"
        
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "SECURITY FEATURES"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        grep -A10 "SECURITY" "$ASSESSMENT_DIR/01-quick-summary.txt" | grep -E "(Boot|TPM|SecBoot)"
        
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "OVERALL ASSESSMENT"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        
        # Determine overall readiness
        local ready=true
        local score=0
        local max_score=10
        
        # Check critical requirements
        if grep -q "CPU Virtualization.*✓" "$ASSESSMENT_DIR/01-quick-summary.txt"; then
            echo "✓ CPU Virtualization Support"
            score=$((score + 2))
        else
            echo "✗ CPU Virtualization Support"
            ready=false
        fi
        
        if grep -q "IOMMU.*✓" "$ASSESSMENT_DIR/01-quick-summary.txt"; then
            echo "✓ IOMMU Support"
            score=$((score + 2))
        else
            echo "✗ IOMMU Support"
            ready=false
        fi
        
        if grep -q "KVM.*✓" "$ASSESSMENT_DIR/01-quick-summary.txt"; then
            echo "✓ KVM Available"
            score=$((score + 2))
        else
            echo "✗ KVM Available"
            ready=false
        fi
        
        if grep -q "GPU.*isolated" "$ASSESSMENT_DIR/02-iommu-analysis.txt" 2>/dev/null; then
            echo "✓ GPU Passthrough Ready"
            score=$((score + 2))
        else
            echo "⚠ GPU Passthrough Limited"
            score=$((score + 1))
        fi
        
        if grep -q "UEFI" "$ASSESSMENT_DIR/01-quick-summary.txt"; then
            echo "✓ UEFI Boot Mode"
            score=$((score + 1))
        else
            echo "⚠ Legacy BIOS (UEFI recommended)"
        fi
        
        if grep -q "TPM.*Present" "$ASSESSMENT_DIR/01-quick-summary.txt"; then
            echo "✓ TPM 2.0 Present"
            score=$((score + 1))
        else
            echo "⚠ No TPM (required for Windows 11)"
        fi
        
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "SCORE: $score / $max_score"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        
        if [ "$ready" = true ] && [ $score -ge 8 ]; then
            echo "✓ VERDICT: EXCELLENT - Ready for MiOS-Build deployment"
            echo ""
            echo "Your system meets all requirements and is highly suitable for"
            echo "Cloud Workstation usage with GPU passthrough capabilities."
        elif [ "$ready" = true ] && [ $score -ge 6 ]; then
            echo "✓ VERDICT: GOOD - Ready with minor limitations"
            echo ""
            echo "Your system meets core requirements. Some optional features"
            echo "may be missing but MiOS-Build will work well."
        elif [ $score -ge 4 ]; then
            echo "⚠ VERDICT: PARTIAL - Limited functionality expected"
            echo ""
            echo "Your system can run MiOS-Build but some features may not work."
            echo "GPU passthrough may require additional configuration."
        else
            echo "✗ VERDICT: NOT READY - Critical requirements missing"
            echo ""
            echo "Your system does not meet minimum requirements for MiOS-Build."
            echo "Please enable virtualization features in BIOS and ensure"
            echo "hardware supports IOMMU/VT-d/AMD-Vi."
        fi
        
        echo ""
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "RECOMMENDATIONS"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        
        if ! grep -q "IOMMU.*✓" "$ASSESSMENT_DIR/01-quick-summary.txt"; then
            echo "1. Enable IOMMU/VT-d/AMD-Vi in BIOS settings"
            echo "2. Add kernel parameters: intel_iommu=on iommu=pt (Intel)"
            echo "                      or: amd_iommu=on iommu=pt (AMD)"
            echo ""
        fi
        
        if ! grep -q "TPM.*Present" "$ASSESSMENT_DIR/01-quick-summary.txt"; then
            echo "• Enable TPM 2.0 in BIOS for Windows 11 VM support"
            echo ""
        fi
        
        if ! grep -q "GPU.*isolated" "$ASSESSMENT_DIR/02-iommu-analysis.txt" 2>/dev/null; then
            echo "• GPU is not isolated - consider ACS override patch"
            echo "• Check motherboard documentation for PCIe slot isolation"
            echo ""
        fi
        
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo "DETAILED FILES"
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        echo "Quick Summary:    01-quick-summary.txt"
        echo "IOMMU Analysis:   02-iommu-analysis.txt"
        echo "Full Profile:     03-full-profile.txt"
        echo ""
        echo "For complete details, review files in:"
        echo "$ASSESSMENT_DIR"
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        
    } > "$report"
    
    print_success "Compatibility report generated"
}

show_summary() {
    print_step "Assessment Complete!"
    
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${GREEN}                    RESULTS SUMMARY${NC}"
    echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════════════${NC}\n"
    
    # Show the verdict from the report
    grep -A20 "OVERALL ASSESSMENT" "$ASSESSMENT_DIR/00-COMPATIBILITY-REPORT.txt" | head -30
    
    echo ""
    echo -e "${BOLD}📁 All assessment files saved to:${NC}"
    echo -e "   ${CYAN}$ASSESSMENT_DIR${NC}"
    echo ""
    echo -e "${BOLD}📄 Files generated:${NC}"
    echo -e "   ${GREEN}✓${NC} 00-COMPATIBILITY-REPORT.txt  (START HERE)"
    echo -e "   ${GREEN}✓${NC} 01-quick-summary.txt"
    echo -e "   ${GREEN}✓${NC} 02-iommu-analysis.txt"
    echo -e "   ${GREEN}✓${NC} 03-full-profile.txt"
    echo ""
    echo -e "${BOLD}💡 Next Steps:${NC}"
    echo -e "   1. Review: ${CYAN}cat $ASSESSMENT_DIR/00-COMPATIBILITY-REPORT.txt${NC}"
    echo -e "   2. Check details: ${CYAN}less $ASSESSMENT_DIR/03-full-profile.txt${NC}"
    echo -e "   3. If ready, proceed with MiOS-Build setup"
    echo ""
}

main() {
    print_banner
    
    echo -e "${BOLD}This tool will:${NC}"
    echo "  1. Run quick system checks"
    echo "  2. Analyze IOMMU/PCIe topology"
    echo "  3. Create comprehensive system profile"
    echo "  4. Generate compatibility report"
    echo ""
    echo "Estimated time: 3-5 minutes"
    echo ""
    
    read -p "Press Enter to start assessment... " -r
    echo ""
    
    # Run assessment steps
    check_requirements
    create_assessment_dir
    
    local quick_ok=0
    local iommu_ok=0
    
    run_quick_summary || quick_ok=$?
    run_iommu_analysis || iommu_ok=$?
    run_full_profile
    
    generate_compatibility_report
    show_summary
    
    echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}${CYAN}            Assessment Complete - Happy Building!${NC}"
    echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════════════${NC}\n"
}

main "$@"

exit 0

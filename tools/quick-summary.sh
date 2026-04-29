#!/bin/bash

################################################################################
# Quick System Summary
# Fast overview of critical system information for MiOS-Build
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

print_header() {
    echo -e "\n${BOLD}${CYAN}▶ $1${NC}"
    echo -e "${CYAN}$(printf '─%.0s' {1..60})${NC}"
}

check_status() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${RED}✗${NC}"
    fi
}

main() {
    clear
    echo -e "${BOLD}${CYAN}"
    cat << 'EOF'
╔══════════════════════════════════════════════════════════╗
║           QUICK SYSTEM SUMMARY - MiOS-Build                ║
╚══════════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}\n"
    
    # System basics
    print_header "SYSTEM"
    echo -e "${BOLD}Host:${NC}     $(hostname)"
    echo -e "${BOLD}Distro:${NC}   $(grep PRETTY_NAME /etc/os-release | cut -d'"' -f2)"
    echo -e "${BOLD}Kernel:${NC}   $(uname -r)"
    echo -e "${BOLD}Uptime:${NC}   $(uptime -p)"
    
    # CPU
    print_header "CPU"
    local cpu_model=$(grep -m1 "model name" /proc/cpuinfo | cut -d: -f2 | xargs)
    local cpu_cores=$(nproc)
    local cpu_threads=$(grep -c processor /proc/cpuinfo)
    echo -e "${BOLD}Model:${NC}    $cpu_model"
    echo -e "${BOLD}Cores:${NC}    $cpu_cores physical, $cpu_threads threads"
    
    # Check virtualization
    if grep -q -E '(vmx|svm)' /proc/cpuinfo; then
        local virt_type=$(grep -o -E '(vmx|svm)' /proc/cpuinfo | head -1)
        echo -e "${BOLD}Virt:${NC}     ${GREEN}✓${NC} Enabled ($virt_type)"
    else
        echo -e "${BOLD}Virt:${NC}     ${RED}✗${NC} Not detected"
    fi
    
    # Memory
    print_header "MEMORY"
    local mem_total=$(free -h | awk '/^Mem:/ {print $2}')
    local mem_used=$(free -h | awk '/^Mem:/ {print $3}')
    local mem_avail=$(free -h | awk '/^Mem:/ {print $7}')
    echo -e "${BOLD}Total:${NC}    $mem_total"
    echo -e "${BOLD}Used:${NC}     $mem_used"
    echo -e "${BOLD}Avail:${NC}    $mem_avail"
    
    # GPU
    print_header "GRAPHICS"
    local gpu_count=$(lspci | grep -c -E "VGA|3D" || echo "0")
    if [ "$gpu_count" -gt 0 ]; then
        lspci | grep -E "VGA|3D" | while read -r line; do
            echo -e "${BOLD}GPU:${NC}      ${line#*: }"
        done
        
        # NVIDIA check
        if command -v nvidia-smi >/dev/null 2>&1; then
            echo -e "${BOLD}NVIDIA:${NC}   ${GREEN}✓${NC} Driver loaded"
        fi
    else
        echo -e "${BOLD}GPU:${NC}      No discrete GPU detected"
    fi
    
    # Storage
    print_header "STORAGE"
    df -h / | tail -1 | awk '{printf "'"${BOLD}"'Root:'"${NC}"'     %s total, %s used, %s free (%s)\n", $2, $3, $4, $5}'
    
    # Count disks
    local disk_count=$(lsblk -d -o TYPE | grep -c disk || echo "0")
    echo -e "${BOLD}Disks:${NC}    $disk_count detected"
    
    # IOMMU
    print_header "VIRTUALIZATION"
    if [ -d /sys/kernel/iommu_groups ]; then
        local iommu_groups=$(ls -1 /sys/kernel/iommu_groups/ | wc -l)
        echo -e "${BOLD}IOMMU:${NC}    ${GREEN}✓${NC} Enabled ($iommu_groups groups)"
        
        # Quick GPU isolation check
        if [ "$gpu_count" -gt 0 ]; then
            echo -e "${BOLD}GPU Grp:${NC}  Checking isolation..."
            local isolated=0
            for gpu_addr in $(lspci | grep -E "VGA|3D" | awk '{print $1}'); do
                for d in /sys/kernel/iommu_groups/*/devices/*; do
                    if [[ "$d" == *"$gpu_addr"* ]]; then
                        n=${d#*/iommu_groups/*}
                        n=${n%%/*}
                        device_count=$(find /sys/kernel/iommu_groups/$n/devices/ -type l | wc -l)
                        if [ "$device_count" -le 2 ]; then
                            isolated=$((isolated + 1))
                        fi
                        break
                    fi
                done
            done
            
            if [ "$isolated" -gt 0 ]; then
                echo -e "          ${GREEN}✓${NC} $isolated GPU(s) in isolated group(s)"
            else
                echo -e "          ${YELLOW}⚠${NC} GPUs share IOMMU groups"
            fi
        fi
    else
        echo -e "${BOLD}IOMMU:${NC}    ${RED}✗${NC} Not available"
    fi
    
    # KVM
    if [ -e /dev/kvm ]; then
        echo -e "${BOLD}KVM:${NC}      ${GREEN}✓${NC} Available"
    else
        echo -e "${BOLD}KVM:${NC}      ${RED}✗${NC} Not available"
    fi
    
    # Security
    print_header "SECURITY"
    
    # Boot mode
    if [ -d /sys/firmware/efi ]; then
        echo -e "${BOLD}Boot:${NC}     ${GREEN}✓${NC} UEFI"
    else
        echo -e "${BOLD}Boot:${NC}     ${YELLOW}⚠${NC} Legacy BIOS"
    fi
    
    # TPM
    if [ -e /dev/tpm0 ]; then
        echo -e "${BOLD}TPM:${NC}      ${GREEN}✓${NC} Present (/dev/tpm0)"
    else
        echo -e "${BOLD}TPM:${NC}      ${RED}✗${NC} Not detected"
    fi
    
    # Secure Boot
    if command -v mokutil >/dev/null 2>&1; then
        if mokutil --sb-state 2>/dev/null | grep -q "SecureBoot enabled"; then
            echo -e "${BOLD}SecBoot:${NC}  ${GREEN}✓${NC} Enabled"
        else
            echo -e "${BOLD}SecBoot:${NC}  ${YELLOW}⚠${NC} Disabled"
        fi
    fi
    
    # Network
    print_header "NETWORK"
    local iface_count=$(ls /sys/class/net/ | grep -v lo | wc -l)
    echo -e "${BOLD}Ifaces:${NC}   $iface_count detected"
    ip -br addr show | grep -v "lo " | while read -r line; do
        local iface=$(echo $line | awk '{print $1}')
        local ip=$(echo $line | awk '{print $3}' | cut -d/ -f1)
        local state=$(echo $line | awk '{print $2}')
        if [ "$state" = "UP" ]; then
            echo -e "          ${GREEN}✓${NC} $iface: $ip"
        else
            echo -e "          ${YELLOW}○${NC} $iface: $state"
        fi
    done
    
    # Recommendations
    print_header "MiOS-Build READINESS"
    
    local ready=true
    local warnings=0
    
    # Check critical components
    echo -e "\n${BOLD}Critical Components:${NC}"
    
    if grep -q -E '(vmx|svm)' /proc/cpuinfo; then
        echo -e "  ${GREEN}✓${NC} CPU Virtualization"
    else
        echo -e "  ${RED}✗${NC} CPU Virtualization"
        ready=false
    fi
    
    if [ -d /sys/kernel/iommu_groups ]; then
        echo -e "  ${GREEN}✓${NC} IOMMU Support"
    else
        echo -e "  ${RED}✗${NC} IOMMU Support"
        ready=false
    fi
    
    if [ -e /dev/kvm ]; then
        echo -e "  ${GREEN}✓${NC} KVM Available"
    else
        echo -e "  ${RED}✗${NC} KVM Available"
        ready=false
    fi
    
    if [ "$gpu_count" -gt 0 ]; then
        echo -e "  ${GREEN}✓${NC} GPU Detected"
    else
        echo -e "  ${YELLOW}⚠${NC} No discrete GPU"
        warnings=$((warnings + 1))
    fi
    
    echo -e "\n${BOLD}Recommended Components:${NC}"
    
    if [ -d /sys/firmware/efi ]; then
        echo -e "  ${GREEN}✓${NC} UEFI Boot"
    else
        echo -e "  ${YELLOW}⚠${NC} Legacy BIOS (UEFI recommended)"
        warnings=$((warnings + 1))
    fi
    
    if [ -e /dev/tpm0 ]; then
        echo -e "  ${GREEN}✓${NC} TPM 2.0"
    else
        echo -e "  ${YELLOW}⚠${NC} No TPM (needed for Win11)"
        warnings=$((warnings + 1))
    fi
    
    # Final verdict
    echo ""
    if [ "$ready" = true ]; then
        echo -e "${GREEN}${BOLD}✓ System ready for MiOS-Build setup!${NC}"
        if [ "$warnings" -gt 0 ]; then
            echo -e "${YELLOW}  Note: $warnings optional component(s) missing${NC}"
        fi
    else
        echo -e "${RED}${BOLD}✗ System not ready - check failed components${NC}"
    fi
    
    echo ""
    echo -e "${CYAN}Run './system-profiler.sh' for detailed analysis${NC}"
    echo -e "${CYAN}Run './iommu-visualizer.sh' for IOMMU group details${NC}"
    echo ""
}

main "$@"

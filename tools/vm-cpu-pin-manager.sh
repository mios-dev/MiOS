#!/bin/bash
###############################################################################
# VM CPU Core Pinning Hook Manager
# For MiOS-Build Professional Virtualization Hosts
# Optimized for: AMD Ryzen X3D (dual-CCD), Intel Hybrid, NUMA systems
# Integrates with: libvirt, universal-cpu-isolator.sh, MiOS-Build framework
###############################################################################

set -euo pipefail

# Colors - MiOS-Build Theme (Teal/Coral/White)
readonly TEAL='\033[38;5;43m'
readonly TEAL_LIGHT='\033[38;5;80m'
readonly TEAL_DARK='\033[38;5;30m'
readonly CORAL='\033[38;5;210m'
readonly WHITE='\033[1;37m'
readonly GRAY='\033[38;5;245m'
readonly SUCCESS='\033[38;5;48m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly BOLD='\033[1m'
readonly DIM='\033[2m'
readonly NC='\033[0m'

# Configuration
readonly SCRIPT_VERSION="v0.1.1"
readonly HOOK_DIR="/etc/libvirt/hooks"
readonly CONFIG_DIR="/etc/libvirt/vm-cpu-pins"
readonly BACKUP_SUFFIX=".backup-$(date +%Y%m%d-%H%M%S)"

# CPU Topology Data
declare -A CPU_INFO
declare -a CCD_MAP=()
declare -A NUMA_MAP
declare -A VM_CONFIGS

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${SUCCESS}[Ã¢Å“"]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[Ã¢Å¡ ]${NC} $1"; }
log_error() { echo -e "${CORAL}[Ã¢Å“â€”]${NC} $1"; }
log_header() {
    echo ""
    echo -e "${TEAL}Ã¢â€¢"Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢â€”${NC}"
    echo -e "${TEAL}Ã¢â€¢'${NC} ${BOLD}$1${NC}"
    echo -e "${TEAL}Ã¢â€¢Å¡Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢${NC}"
    echo ""
}

# Check root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        echo "Usage: sudo $0"
        exit 1
    fi
}

# Detect CPU topology
detect_cpu_topology() {
    log_info "Detecting CPU topology..."
    
    # Basic CPU info
    CPU_INFO[vendor]=$(lscpu | grep "Vendor ID" | awk '{print $3}')
    CPU_INFO[model]=$(lscpu | grep "Model name" | sed 's/Model name:[[:space:]]*//')
    CPU_INFO[cores]=$(lscpu | grep "^Core(s) per socket:" | awk '{print $4}')
    CPU_INFO[threads]=$(lscpu | grep "^CPU(s):" | head -1 | awk '{print $2}')
    CPU_INFO[sockets]=$(lscpu | grep "Socket(s):" | awk '{print $2}')
    CPU_INFO[threads_per_core]=$(lscpu | grep "Thread(s) per core:" | awk '{print $4}')
    
    # Detect NUMA
    CPU_INFO[numa_nodes]=$(lscpu | grep "NUMA node(s):" | awk '{print $3}')
    
    # Build NUMA map
    for ((node=0; node<${CPU_INFO[numa_nodes]}; node+=1)); do
        local cpus=$(lscpu | grep "NUMA node${node} CPU(s):" | awk '{print $4}')
        NUMA_MAP[$node]="$cpus"
    done
    
    # Detect AMD CCD architecture
    detect_amd_ccds
    
    log_success "Detected: ${CPU_INFO[model]}"
    log_info "Topology: ${CPU_INFO[cores]} cores, ${CPU_INFO[threads]} threads"
}

# Detect AMD CCD layout (for Ryzen 9950X3D, 7950X3D, etc.)
detect_amd_ccds() {
    if [[ "${CPU_INFO[vendor]}" != "AuthenticAMD" ]]; then
        return
    fi
    
    # Check for X3D CPUs
    if [[ "${CPU_INFO[model]}" =~ (9950X3D|7950X3D|7900X3D) ]]; then
        local cores_per_ccd=$((${CPU_INFO[cores]} / 2))
        local threads_per_ccd=$((cores_per_ccd * ${CPU_INFO[threads_per_core]}))
        
        CPU_INFO[has_ccds]=1
        CPU_INFO[ccd_count]=2
        CPU_INFO[cores_per_ccd]=$cores_per_ccd
        
        # CCD0: Usually has V-Cache
        CCD_MAP[0]="0-$((threads_per_ccd - 1))"
        # CCD1: Usually higher frequency
        CCD_MAP[1]="$threads_per_ccd-$((${CPU_INFO[threads]} - 1))"
        
        log_success "AMD X3D dual-CCD architecture detected"
    fi
}

# List all VMs
list_vms() {
    local all_vms=$(virsh list --all --name 2>/dev/null | grep -v "^$")
    
    if [[ -z "$all_vms" ]]; then
        log_warning "No VMs found. Create VMs with virt-manager first."
        return 1
    fi
    
    echo "$all_vms"
}

# Display CPU topology visualization
display_cpu_topology() {
    echo -e "${CYAN}Ã¢â€¢"Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢â€”${NC}"
    echo -e "${CYAN}Ã¢â€¢'${NC} ${BOLD}CPU Configuration${NC}"
    echo -e "${CYAN}Ã¢â€¢ Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Â£${NC}"
    echo -e "${CYAN}Ã¢â€¢'${NC} Model:        ${CPU_INFO[model]}"
    echo -e "${CYAN}Ã¢â€¢'${NC} Cores:        ${CPU_INFO[cores]} physical"
    echo -e "${CYAN}Ã¢â€¢'${NC} Threads:      ${CPU_INFO[threads]} logical"
    echo -e "${CYAN}Ã¢â€¢'${NC} NUMA Nodes:   ${CPU_INFO[numa_nodes]}"
    
    if [[ -n "${CPU_INFO[has_ccds]}" ]]; then
        echo -e "${CYAN}Ã¢â€¢'${NC} CCDs:         ${CPU_INFO[ccd_count]} (AMD X3D)"
    fi
    
    echo -e "${CYAN}Ã¢â€¢Å¡Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢${NC}"
    echo ""
    
    # Visual CPU grid
    if [[ -n "${CPU_INFO[has_ccds]}" ]]; then
        display_ccd_layout
    else
        display_linear_layout
    fi
}

# Display CCD-based layout (AMD X3D)
display_ccd_layout() {
    echo -e "${BOLD}CPU Layout by CCD:${NC}"
    echo ""
    
    local threads_per_ccd=$((${CPU_INFO[threads]} / ${CPU_INFO[ccd_count]}))
    local cores_per_ccd=${CPU_INFO[cores_per_ccd]}
    
    for ((ccd=0; ccd<${CPU_INFO[ccd_count]}; ccd+=1)); do
        local start=$((ccd * threads_per_ccd))
        local end=$((start + threads_per_ccd - 1))
        
        if [[ $ccd -eq 0 ]]; then
            echo -e "${SUCCESS}CCD${ccd}${NC} ${BOLD}(V-Cache - Best for Gaming/Latency)${NC}"
        else
            echo -e "${YELLOW}CCD${ccd}${NC} ${BOLD}(High Frequency - Best for Throughput)${NC}"
        fi
        
        echo -n "  Cores: "
        for ((core=0; core<cores_per_ccd; core+=1)); do
            local cpu=$((start + core))
            local sibling=$((start + cores_per_ccd + core))
            
            if [[ ${CPU_INFO[threads_per_core]} -eq 2 ]]; then
                printf "${CYAN}%2d${NC}/${DIM}%2d${NC} " $cpu $sibling
            else
                printf "${CYAN}%2d${NC} " $cpu
            fi
        done
        echo ""
        echo ""
    done
    
    echo -e "${DIM}Format: ${CYAN}Physical${NC}/${DIM}SMT-Thread${NC}${NC}"
    echo ""
}

# Display linear layout
display_linear_layout() {
    echo -e "${BOLD}CPU Layout:${NC}"
    echo ""
    
    local cols=8
    for ((cpu=0; cpu<${CPU_INFO[threads]}; cpu+=1)); do
        printf "${CYAN}%3d${NC} " $cpu
        if [[ $(((cpu + 1) % cols)) -eq 0 ]]; then
            echo ""
        fi
    done
    echo ""
    echo ""
}

# Main menu
main_menu() {
    log_header "VM CPU Core Pinning Hook Manager v${SCRIPT_VERSION}"
    
    display_cpu_topology
    
    echo -e "${BOLD}Management Options:${NC}"
    echo ""
    echo "  ${TEAL}1)${NC} Configure VM CPU pinning (per-VM)"
    echo "  ${TEAL}2)${NC} View current VM configurations"
    echo "  ${TEAL}3)${NC} Remove VM configuration"
    echo "  ${TEAL}4)${NC} Test hook execution"
    echo "  ${TEAL}5)${NC} View CPU allocation map"
    echo "  ${TEAL}6)${NC} Generate XML snippets"
    echo "  ${TEAL}7)${NC} Export/Import configurations"
    echo "  ${TEAL}8)${NC} Verify hook integrity"
    echo "  ${TEAL}9)${NC} Exit"
    echo ""
    
    read -p "Selection [1-9]: " choice
    
    case $choice in
        1) configure_vm_pinning ;;
        2) view_configurations ;;
        3) remove_configuration ;;
        4) test_hook ;;
        5) view_allocation_map ;;
        6) generate_xml_snippets ;;
        7) export_import_menu ;;
        8) verify_hooks ;;
        9) exit 0 ;;
        *) log_error "Invalid selection"; sleep 2; main_menu ;;
    esac
}

# Configure VM CPU pinning
configure_vm_pinning() {
    log_header "Configure VM CPU Pinning"
    
    # List VMs
    local vm_list=$(list_vms)
    if [[ -z "$vm_list" ]]; then
        read -p "Press Enter to return to menu..."
        main_menu
        return
    fi
    
    echo "Available VMs:"
    echo ""
    local counter=1
    while IFS= read -r vm; do
        local state=$(virsh domstate "$vm" 2>/dev/null || echo "unknown")
        local vcpu_count=$(virsh dominfo "$vm" 2>/dev/null | grep "CPU(s):" | awk '{print $2}')
        
        echo -e "  ${TEAL}${counter})${NC} ${WHITE}${vm}${NC}"
        echo -e "     State: ${GRAY}${state}${NC} | vCPUs: ${GRAY}${vcpu_count:-unknown}${NC}"
        
        # Check if already configured
        if [[ -f "$CONFIG_DIR/${vm}.conf" ]]; then
            echo -e "     ${SUCCESS}Ã¢Å“" Configured${NC}"
        else
            echo -e "     ${CORAL}Ã¢Å“â€“ Not configured${NC}"
        fi
        echo ""
        
        counter=$((counter + 1))
    done <<< "$vm_list"
    
    read -p "Select VM to configure (number or name): " vm_selection
    
    # Parse selection
    local selected_vm=""
    if [[ "$vm_selection" =~ ^[0-9]+$ ]]; then
        selected_vm=$(echo "$vm_list" | sed -n "${vm_selection}p")
    else
        selected_vm="$vm_selection"
    fi
    
    if [[ -z "$selected_vm" ]]; then
        log_error "Invalid selection"
        sleep 2
        main_menu
        return
    fi
    
    # Check if VM exists
    if ! virsh dominfo "$selected_vm" &>/dev/null; then
        log_error "VM not found: $selected_vm"
        sleep 2
        main_menu
        return
    fi
    
    configure_vm_cores "$selected_vm"
}

# Configure cores for specific VM
configure_vm_cores() {
    local vm_name="$1"
    
    log_header "Configure: $vm_name"
    
    display_cpu_topology
    
    # Get VM info
    local vcpu_count=$(virsh dominfo "$vm_name" | grep "CPU(s):" | awk '{print $2}')
    log_info "VM has ${vcpu_count} vCPUs configured"
    echo ""
    
    echo -e "${BOLD}Core Selection Strategy:${NC}"
    echo ""
    
    if [[ -n "${CPU_INFO[has_ccds]}" ]]; then
        echo "  ${TEAL}1)${NC} Quick Presets (AMD X3D optimized)"
        echo "  ${TEAL}2)${NC} Entire CCD (8 cores / 16 threads)"
        echo "  ${TEAL}3)${NC} Partial CCD (custom core range)"
        echo "  ${TEAL}4)${NC} Mixed CCDs (advanced)"
        echo "  ${TEAL}5)${NC} Custom core list"
        echo "  ${TEAL}6)${NC} Cancel"
    else
        echo "  ${TEAL}1)${NC} Quick Presets"
        echo "  ${TEAL}2)${NC} Sequential cores (e.g., 0-7)"
        echo "  ${TEAL}3)${NC} Custom core list"
        echo "  ${TEAL}4)${NC} Cancel"
    fi
    
    echo ""
    read -p "Selection: " strategy
    
    case $strategy in
        1) select_preset "$vm_name" "$vcpu_count" ;;
        2) 
            if [[ -n "${CPU_INFO[has_ccds]}" ]]; then
                select_entire_ccd "$vm_name" "$vcpu_count"
            else
                select_sequential "$vm_name" "$vcpu_count"
            fi
            ;;
        3) 
            if [[ -n "${CPU_INFO[has_ccds]}" ]]; then
                select_partial_ccd "$vm_name" "$vcpu_count"
            else
                select_custom "$vm_name" "$vcpu_count"
            fi
            ;;
        4)
            if [[ -n "${CPU_INFO[has_ccds]}" ]]; then
                select_mixed_ccd "$vm_name" "$vcpu_count"
            else
                main_menu
                return
            fi
            ;;
        5)
            if [[ -n "${CPU_INFO[has_ccds]}" ]]; then
                select_custom "$vm_name" "$vcpu_count"
            else
                main_menu
                return
            fi
            ;;
        6|*) main_menu; return ;;
    esac
}

# Quick presets for X3D
select_preset() {
    local vm_name="$1"
    local vcpu_count="$2"
    
    echo ""
    echo -e "${BOLD}Quick Presets:${NC}"
    echo ""
    
    if [[ -n "${CPU_INFO[has_ccds]}" ]]; then
        echo "  ${TEAL}1)${NC} Gaming VM ${SUCCESS}(CCD0 V-Cache - 16 threads)${NC}"
        echo "  ${TEAL}2)${NC} Gaming VM ${SUCCESS}(CCD0 V-Cache - 12 threads)${NC}"
        echo "  ${TEAL}3)${NC} Gaming VM ${SUCCESS}(CCD0 V-Cache - 8 threads)${NC}"
        echo "  ${TEAL}4)${NC} Workstation VM ${YELLOW}(CCD1 High-Freq - 16 threads)${NC}"
        echo "  ${TEAL}5)${NC} Workstation VM ${YELLOW}(CCD1 High-Freq - 12 threads)${NC}"
        echo "  ${TEAL}6)${NC} Workstation VM ${YELLOW}(CCD1 High-Freq - 8 threads)${NC}"
        echo "  ${TEAL}7)${NC} Balanced ${GRAY}(8 threads from each CCD)${NC}"
    else
        echo "  ${TEAL}1)${NC} First half (CPUs 0 to $((${CPU_INFO[threads]} / 2 - 1)))"
        echo "  ${TEAL}2)${NC} Second half (CPUs $((${CPU_INFO[threads]} / 2)) to $((${CPU_INFO[threads]} - 1)))"
        echo "  ${TEAL}3)${NC} First quarter"
        echo "  ${TEAL}4)${NC} Custom"
    fi
    
    echo ""
    read -p "Preset: " preset
    
    local cpus=""
    local emulator_cpus=""
    local description=""
    
    if [[ -n "${CPU_INFO[has_ccds]}" ]]; then
        case $preset in
            1)
                cpus="0-15"
                emulator_cpus="16-19"
                description="Gaming VM - CCD0 Full (V-Cache)"
                ;;
            2)
                cpus="2-7,18-23"
                emulator_cpus="0-1"
                description="Gaming VM - CCD0 Cores 2-7 (V-Cache)"
                ;;
            3)
                cpus="0-7"
                emulator_cpus="16-19"
                description="Gaming VM - CCD0 Physical Cores (V-Cache)"
                ;;
            4)
                cpus="16-31"
                emulator_cpus="0-3"
                description="Workstation VM - CCD1 Full (High Freq)"
                ;;
            5)
                cpus="18-23,26-31"
                emulator_cpus="16-17"
                description="Workstation VM - CCD1 Cores 10-15 (High Freq)"
                ;;
            6)
                cpus="16-23"
                emulator_cpus="0-3"
                description="Workstation VM - CCD1 Physical Cores (High Freq)"
                ;;
            7)
                cpus="0-7,16-23"
                emulator_cpus="8-11"
                description="Balanced - 8 cores from each CCD"
                ;;
            *)
                log_error "Invalid preset"
                sleep 2
                configure_vm_cores "$vm_name"
                return
                ;;
        esac
    else
        local half=$((${CPU_INFO[threads]} / 2))
        local quarter=$((${CPU_INFO[threads]} / 4))
        
        case $preset in
            1)
                cpus="0-$((half - 1))"
                emulator_cpus="$half-$((half + 3))"
                description="First half of CPUs"
                ;;
            2)
                cpus="$half-$((${CPU_INFO[threads]} - 1))"
                emulator_cpus="0-3"
                description="Second half of CPUs"
                ;;
            3)
                cpus="0-$((quarter - 1))"
                emulator_cpus="$quarter-$((quarter + 3))"
                description="First quarter of CPUs"
                ;;
            4)
                select_custom "$vm_name" "$vcpu_count"
                return
                ;;
            *)
                log_error "Invalid preset"
                sleep 2
                configure_vm_cores "$vm_name"
                return
                ;;
        esac
    fi
    
    save_vm_config "$vm_name" "$cpus" "$emulator_cpus" "$description"
}

# Select entire CCD
select_entire_ccd() {
    local vm_name="$1"
    local vcpu_count="$2"
    
    echo ""
    echo -e "${BOLD}Select CCD:${NC}"
    echo ""
    echo "  ${TEAL}1)${NC} CCD0 ${SUCCESS}(V-Cache)${NC} - CPUs ${CCD_MAP[0]}"
    echo "  ${TEAL}2)${NC} CCD1 ${YELLOW}(High Freq)${NC} - CPUs ${CCD_MAP[1]}"
    echo ""
    
    read -p "CCD: " ccd_choice
    
    local cpus=""
    local emulator_cpus=""
    local description=""
    
    case $ccd_choice in
        1)
            cpus="${CCD_MAP[0]}"
            emulator_cpus="16-19"
            description="Full CCD0 (V-Cache)"
            ;;
        2)
            cpus="${CCD_MAP[1]}"
            emulator_cpus="0-3"
            description="Full CCD1 (High Frequency)"
            ;;
        *)
            log_error "Invalid selection"
            sleep 2
            configure_vm_cores "$vm_name"
            return
            ;;
    esac
    
    save_vm_config "$vm_name" "$cpus" "$emulator_cpus" "$description"
}

# Select partial CCD
select_partial_ccd() {
    local vm_name="$1"
    local vcpu_count="$2"
    
    echo ""
    echo -e "${BOLD}Partial CCD Selection:${NC}"
    echo ""
    echo "  ${TEAL}1)${NC} CCD0 ${SUCCESS}(V-Cache)${NC}"
    echo "  ${TEAL}2)${NC} CCD1 ${YELLOW}(High Freq)${NC}"
    echo ""
    
    read -p "CCD: " ccd_choice
    
    local start_cpu=""
    local ccd_name=""
    
    case $ccd_choice in
        1)
            start_cpu=0
            ccd_name="CCD0 (V-Cache)"
            ;;
        2)
            start_cpu=16
            ccd_name="CCD1 (High Freq)"
            ;;
        *)
            log_error "Invalid selection"
            sleep 2
            configure_vm_cores "$vm_name"
            return
            ;;
    esac
    
    echo ""
    echo "Enter core range within $ccd_name"
    echo "Examples: 0-7, 2-7, 0-3"
    echo ""
    read -p "Core range (relative to CCD start): " range
    
    # Parse range and adjust for actual CPU numbers
    if [[ "$range" =~ ^([0-9]+)-([0-9]+)$ ]]; then
        local rel_start="${BASH_REMATCH[1]}"
        local rel_end="${BASH_REMATCH[2]}"
        local abs_start=$((start_cpu + rel_start))
        local abs_end=$((start_cpu + rel_end))
        
        # If SMT enabled, include siblings
        if [[ ${CPU_INFO[threads_per_core]} -eq 2 ]]; then
            local smt_start=$((abs_start + 8))
            local smt_end=$((abs_end + 8))
            cpus="${abs_start}-${abs_end},${smt_start}-${smt_end}"
        else
            cpus="${abs_start}-${abs_end}"
        fi
        
        # Emulator on different CCD
        if [[ $ccd_choice -eq 1 ]]; then
            emulator_cpus="16-19"
        else
            emulator_cpus="0-3"
        fi
        
        description="Partial ${ccd_name} - Cores ${rel_start}-${rel_end}"
        
        save_vm_config "$vm_name" "$cpus" "$emulator_cpus" "$description"
    else
        log_error "Invalid range format"
        sleep 2
        configure_vm_cores "$vm_name"
    fi
}

# Select mixed CCDs
select_mixed_ccd() {
    local vm_name="$1"
    local vcpu_count="$2"
    
    echo ""
    log_warning "Mixed CCD allocation may cause cross-CCD latency"
    echo ""
    echo "Enter cores from each CCD (comma-separated)"
    echo "Example: 0-3,16-19 (4 from CCD0, 4 from CCD1)"
    echo ""
    
    read -p "Core list: " cpus
    read -p "Emulator cores: " emulator_cpus
    
    description="Mixed CCD allocation"
    
    save_vm_config "$vm_name" "$cpus" "$emulator_cpus" "$description"
}

# Sequential core selection
select_sequential() {
    local vm_name="$1"
    local vcpu_count="$2"
    
    echo ""
    echo "Enter sequential core range"
    echo "Example: 0-7, 8-15, 16-23"
    echo ""
    
    read -p "Core range: " cpus
    read -p "Emulator cores (separate range): " emulator_cpus
    
    description="Sequential cores: $cpus"
    
    save_vm_config "$vm_name" "$cpus" "$emulator_cpus" "$description"
}

# Custom core selection
select_custom() {
    local vm_name="$1"
    local vcpu_count="$2"
    
    echo ""
    echo "Enter custom core list"
    echo "Formats:"
    echo "  - Ranges: 0-7,16-23"
    echo "  - Individual: 0,1,2,3,16,17,18,19"
    echo "  - Mixed: 0-3,8,9,16-19"
    echo ""
    
    read -p "vCPU cores: " cpus
    read -p "Emulator cores: " emulator_cpus
    read -p "Description: " description
    
    save_vm_config "$vm_name" "$cpus" "$emulator_cpus" "$description"
}

# Save VM configuration
save_vm_config() {
    local vm_name="$1"
    local cpus="$2"
    local emulator_cpus="$3"
    local description="$4"
    
    # Create config directory
    mkdir -p "$CONFIG_DIR"
    
    # Create config file
    cat > "$CONFIG_DIR/${vm_name}.conf" << EOF
# VM CPU Pinning Configuration
# Generated: $(date)
# VM: $vm_name

DESCRIPTION="$description"
VCPU_CPUS="$cpus"
EMULATOR_CPUS="$emulator_cpus"
EOF
    
    # Create hook directories
    local vm_hook_dir="$HOOK_DIR/qemu.d/${vm_name}"
    mkdir -p "$vm_hook_dir/prepare/begin"
    mkdir -p "$vm_hook_dir/release/end"
    
    # Create prepare/begin hook
    cat > "$vm_hook_dir/prepare/begin/cpu-pin.sh" << 'EOFHOOK'
#!/bin/bash
# CPU pinning hook - prepare/begin
# VM: VM_NAME_PLACEHOLDER
# Description: DESCRIPTION_PLACEHOLDER

VCPU_CPUS="VCPU_CPUS_PLACEHOLDER"
EMULATOR_CPUS="EMULATOR_CPUS_PLACEHOLDER"

LOG_FILE="/var/log/libvirt/qemu/VM_NAME_PLACEHOLDER-cpu-pin.log"

echo "$(date): VM starting - CPU pinning configuration" >> "$LOG_FILE"
echo "  vCPU cores: $VCPU_CPUS" >> "$LOG_FILE"
echo "  Emulator cores: $EMULATOR_CPUS" >> "$LOG_FILE"

# Get VM PID
VM_PID=$(pgrep -f "qemu.*VM_NAME_PLACEHOLDER")

if [[ -z "$VM_PID" ]]; then
    echo "  Warning: Could not find VM process" >> "$LOG_FILE"
    exit 0
fi

# Pin emulator threads
echo "  Pinning emulator to cores: $EMULATOR_CPUS" >> "$LOG_FILE"
taskset -acp "$EMULATOR_CPUS" "$VM_PID" >> "$LOG_FILE" 2>&1

# Pin vCPU threads
for vcpu_thread in $(ps -T -p "$VM_PID" | grep "CPU " | awk '{print $2}'); do
    taskset -cp "$VCPU_CPUS" "$vcpu_thread" >> "$LOG_FILE" 2>&1
done

echo "  CPU pinning complete" >> "$LOG_FILE"

exit 0
EOFHOOK
    
    # Replace placeholders
    sed -i "s/VM_NAME_PLACEHOLDER/$vm_name/g" "$vm_hook_dir/prepare/begin/cpu-pin.sh"
    sed -i "s/DESCRIPTION_PLACEHOLDER/$description/g" "$vm_hook_dir/prepare/begin/cpu-pin.sh"
    sed -i "s/VCPU_CPUS_PLACEHOLDER/$cpus/g" "$vm_hook_dir/prepare/begin/cpu-pin.sh"
    sed -i "s/EMULATOR_CPUS_PLACEHOLDER/$emulator_cpus/g" "$vm_hook_dir/prepare/begin/cpu-pin.sh"
    
    chmod +x "$vm_hook_dir/prepare/begin/cpu-pin.sh"
    
    # Create release/end hook
    cat > "$vm_hook_dir/release/end/cpu-cleanup.sh" << 'EOFHOOK'
#!/bin/bash
# CPU cleanup hook - release/end
# VM: VM_NAME_PLACEHOLDER

LOG_FILE="/var/log/libvirt/qemu/VM_NAME_PLACEHOLDER-cpu-pin.log"

echo "$(date): VM stopped - CPU resources released" >> "$LOG_FILE"

exit 0
EOFHOOK
    
    sed -i "s/VM_NAME_PLACEHOLDER/$vm_name/g" "$vm_hook_dir/release/end/cpu-cleanup.sh"
    chmod +x "$vm_hook_dir/release/end/cpu-cleanup.sh"
    
    log_success "Configuration saved for $vm_name"
    log_info "Description: $description"
    log_info "vCPU cores: $cpus"
    log_info "Emulator cores: $emulator_cpus"
    
    echo ""
    echo -e "${BOLD}Next Steps:${NC}"
    echo "  1. Edit VM XML to match these cores (Option 6 for snippet)"
    echo "  2. Test the configuration (Option 4)"
    echo "  3. Start the VM normally"
    echo ""
    
    read -p "Press Enter to return to menu..."
    main_menu
}

# View current configurations
view_configurations() {
    log_header "Current VM Configurations"
    
    if [[ ! -d "$CONFIG_DIR" ]] || [[ -z "$(ls -A "$CONFIG_DIR" 2>/dev/null)" ]]; then
        log_warning "No VM configurations found"
        echo ""
        read -p "Press Enter to return to menu..."
        main_menu
        return
    fi
    
    local counter=1
    for config in "$CONFIG_DIR"/*.conf; do
        local vm_name=$(basename "$config" .conf)
        
        # Source config
        source "$config"
        
        echo -e "${CYAN}Ã¢â€¢"Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢â€”${NC}"
        echo -e "${CYAN}Ã¢â€¢'${NC} ${BOLD}${counter}. VM: ${vm_name}${NC}"
        echo -e "${CYAN}Ã¢â€¢ Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Â£${NC}"
        echo -e "${CYAN}Ã¢â€¢'${NC} Description:    ${DESCRIPTION}"
        echo -e "${CYAN}Ã¢â€¢'${NC} vCPU cores:     ${VCPU_CPUS}"
        echo -e "${CYAN}Ã¢â€¢'${NC} Emulator cores: ${EMULATOR_CPUS}"
        
        # Check hook status
        if [[ -x "$HOOK_DIR/qemu.d/${vm_name}/prepare/begin/cpu-pin.sh" ]]; then
            echo -e "${CYAN}Ã¢â€¢'${NC} Hook status:    ${SUCCESS}Ã¢Å“" Active${NC}"
        else
            echo -e "${CYAN}Ã¢â€¢'${NC} Hook status:    ${CORAL}Ã¢Å“â€“ Missing${NC}"
        fi
        
        echo -e "${CYAN}Ã¢â€¢Å¡Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢Ã¢â€¢${NC}"
        echo ""
        
        counter=$((counter + 1))
    done
    
    read -p "Press Enter to return to menu..."
    main_menu
}

# Remove configuration
remove_configuration() {
    log_header "Remove VM Configuration"
    
    if [[ ! -d "$CONFIG_DIR" ]] || [[ -z "$(ls -A "$CONFIG_DIR" 2>/dev/null)" ]]; then
        log_warning "No VM configurations found"
        echo ""
        read -p "Press Enter to return to menu..."
        main_menu
        return
    fi
    
    echo "Configured VMs:"
    echo ""
    
    local counter=1
    for config in "$CONFIG_DIR"/*.conf; do
        local vm_name=$(basename "$config" .conf)
        echo -e "  ${TEAL}${counter})${NC} ${vm_name}"
        counter=$((counter + 1))
    done
    
    echo ""
    read -p "Select VM to remove (number or name): " selection
    
    local selected_vm=""
    if [[ "$selection" =~ ^[0-9]+$ ]]; then
        local configs=("$CONFIG_DIR"/*.conf)
        selected_vm=$(basename "${configs[$((selection - 1))]}" .conf)
    else
        selected_vm="$selection"
    fi
    
    if [[ ! -f "$CONFIG_DIR/${selected_vm}.conf" ]]; then
        log_error "Configuration not found"
        sleep 2
        main_menu
        return
    fi
    
    echo ""
    log_warning "This will remove:"
    echo "  - Configuration file: $CONFIG_DIR/${selected_vm}.conf"
    echo "  - Hook directory: $HOOK_DIR/qemu.d/${selected_vm}"
    echo ""
    
    read -p "Confirm removal? [y/N]: " confirm
    
    if [[ "$confirm" =~ ^[Yy]$ ]]; then
        rm -f "$CONFIG_DIR/${selected_vm}.conf"
        rm -rf "$HOOK_DIR/qemu.d/${selected_vm}"
        log_success "Configuration removed for $selected_vm"
    else
        log_info "Cancelled"
    fi
    
    sleep 2
    main_menu
}

# Test hook execution
test_hook() {
    log_header "Test Hook Execution"
    
    if [[ ! -d "$CONFIG_DIR" ]] || [[ -z "$(ls -A "$CONFIG_DIR" 2>/dev/null)" ]]; then
        log_warning "No VM configurations found"
        echo ""
        read -p "Press Enter to return to menu..."
        main_menu
        return
    fi
    
    echo "Select VM to test:"
    echo ""
    
    local counter=1
    for config in "$CONFIG_DIR"/*.conf; do
        local vm_name=$(basename "$config" .conf)
        echo -e "  ${TEAL}${counter})${NC} ${vm_name}"
        counter=$((counter + 1))
    done
    
    echo ""
    read -p "Selection: " selection
    
    local selected_vm=""
    if [[ "$selection" =~ ^[0-9]+$ ]]; then
        local configs=("$CONFIG_DIR"/*.conf)
        selected_vm=$(basename "${configs[$((selection - 1))]}" .conf)
    else
        selected_vm="$selection"
    fi
    
    if [[ ! -f "$CONFIG_DIR/${selected_vm}.conf" ]]; then
        log_error "Configuration not found"
        sleep 2
        main_menu
        return
    fi
    
    local hook_script="$HOOK_DIR/qemu.d/${selected_vm}/prepare/begin/cpu-pin.sh"
    
    if [[ ! -x "$hook_script" ]]; then
        log_error "Hook script not found or not executable"
        sleep 2
        main_menu
        return
    fi
    
    echo ""
    log_info "Testing hook: $hook_script"
    echo ""
    echo -e "${GRAY}--- Hook Output ---${NC}"
    
    # Simulate hook execution (dry run)
    bash -x "$hook_script" 2>&1 | head -20
    
    echo -e "${GRAY}--- End Output ---${NC}"
    echo ""
    
    log_info "Check log: /var/log/libvirt/qemu/${selected_vm}-cpu-pin.log"
    
    echo ""
    read -p "Press Enter to return to menu..."
    main_menu
}

# View CPU allocation map
view_allocation_map() {
    log_header "CPU Allocation Map"
    
    display_cpu_topology
    
    if [[ ! -d "$CONFIG_DIR" ]] || [[ -z "$(ls -A "$CONFIG_DIR" 2>/dev/null)" ]]; then
        log_warning "No VM configurations found"
        echo ""
        read -p "Press Enter to return to menu..."
        main_menu
        return
    fi
    
    echo -e "${BOLD}VM Core Allocations:${NC}"
    echo ""
    
    # Create allocation array
    declare -a cpu_alloc
    for ((i=0; i<${CPU_INFO[threads]}; i+=1)); do
        cpu_alloc[$i]="HOST"
    done
    
    # Mark VM allocations
    for config in "$CONFIG_DIR"/*.conf; do
        local vm_name=$(basename "$config" .conf)
        source "$config"
        
        # Parse VCPU_CPUS ranges
        local IFS=','
        for range in $VCPU_CPUS; do
            if [[ "$range" =~ ^([0-9]+)-([0-9]+)$ ]]; then
                local start="${BASH_REMATCH[1]}"
                local end="${BASH_REMATCH[2]}"
                for ((cpu=start; cpu<=end; cpu+=1)); do
                    cpu_alloc[$cpu]="$vm_name"
                done
            elif [[ "$range" =~ ^[0-9]+$ ]]; then
                cpu_alloc[$range]="$vm_name"
            fi
        done
    done
    
    # Display allocation
    echo -e "${CYAN}Ã¢"Å’Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"Â¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"${NC}"
    echo -e "${CYAN}Ã¢"â€š${NC} CPU ${CYAN}Ã¢"â€š${NC} Allocated To              ${CYAN}Ã¢"â€š${NC}"
    echo -e "${CYAN}Ã¢"Å“Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"Â¼Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"Â¤${NC}"
    
    for ((cpu=0; cpu<${CPU_INFO[threads]}; cpu+=1)); do
        local alloc="${cpu_alloc[$cpu]}"
        local color="$GRAY"
        
        if [[ "$alloc" != "HOST" ]]; then
            color="$SUCCESS"
        fi
        
        printf "${CYAN}Ã¢"â€š${NC} %3d ${CYAN}Ã¢"â€š${NC} ${color}%-25s${NC} ${CYAN}Ã¢"â€š${NC}\n" "$cpu" "$alloc"
    done
    
    echo -e "${CYAN}Ã¢""Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"Â´Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"â‚¬Ã¢"Ëœ${NC}"
    
    echo ""
    read -p "Press Enter to return to menu..."
    main_menu
}

# Generate XML snippets
generate_xml_snippets() {
    log_header "Generate libvirt XML Snippets"
    
    if [[ ! -d "$CONFIG_DIR" ]] || [[ -z "$(ls -A "$CONFIG_DIR" 2>/dev/null)" ]]; then
        log_warning "No VM configurations found"
        echo ""
        read -p "Press Enter to return to menu..."
        main_menu
        return
    fi
    
    echo "Select VM:"
    echo ""
    
    local counter=1
    for config in "$CONFIG_DIR"/*.conf; do
        local vm_name=$(basename "$config" .conf)
        echo -e "  ${TEAL}${counter})${NC} ${vm_name}"
        counter=$((counter + 1))
    done
    
    echo ""
    read -p "Selection: " selection
    
    local selected_vm=""
    if [[ "$selection" =~ ^[0-9]+$ ]]; then
        local configs=("$CONFIG_DIR"/*.conf)
        selected_vm=$(basename "${configs[$((selection - 1))]}" .conf)
    else
        selected_vm="$selection"
    fi
    
    if [[ ! -f "$CONFIG_DIR/${selected_vm}.conf" ]]; then
        log_error "Configuration not found"
        sleep 2
        main_menu
        return
    fi
    
    source "$CONFIG_DIR/${selected_vm}.conf"
    
    # Generate XML
    echo ""
    echo -e "${BOLD}libvirt XML Configuration Snippet:${NC}"
    echo ""
    echo -e "${GRAY}<!-- Add to <domain> section -->${NC}"
    echo ""
    
    # Parse CPU list to count vCPUs
    local vcpu_count=0
    local IFS=','
    for range in $VCPU_CPUS; do
        if [[ "$range" =~ ^([0-9]+)-([0-9]+)$ ]]; then
            local start="${BASH_REMATCH[1]}"
            local end="${BASH_REMATCH[2]}"
            vcpu_count=$((vcpu_count + end - start + 1))
        elif [[ "$range" =~ ^[0-9]+$ ]]; then
            vcpu_count=$((vcpu_count + 1))
        fi
    done
    
    cat << EOFXML
<vcpu placement='static'>$vcpu_count</vcpu>
<cputune>
  <!-- Pin each vCPU to specific cores -->
EOFXML
    
    # Generate vcpupin entries
    local vcpu_idx=0
    local IFS=','
    for range in $VCPU_CPUS; do
        if [[ "$range" =~ ^([0-9]+)-([0-9]+)$ ]]; then
            local start="${BASH_REMATCH[1]}"
            local end="${BASH_REMATCH[2]}"
            for ((cpu=start; cpu<=end; cpu+=1)); do
                echo "  <vcpupin vcpu='$vcpu_idx' cpuset='$cpu'/>"
                vcpu_idx=$((vcpu_idx + 1))
            done
        elif [[ "$range" =~ ^[0-9]+$ ]]; then
            echo "  <vcpupin vcpu='$vcpu_idx' cpuset='$range'/>"
            vcpu_idx=$((vcpu_idx + 1))
        fi
    done
    
    cat << EOFXML
  
  <!-- Pin emulator threads -->
  <emulatorpin cpuset='$EMULATOR_CPUS'/>
  
  <!-- Optional: IOThread pinning -->
  <iothreadpin iothread='1' cpuset='$EMULATOR_CPUS'/>
</cputune>

<!-- CPU topology (adjust based on your config) -->
<cpu mode='host-passthrough'>
  <topology sockets='1' dies='1' cores='$(($vcpu_count / 2))' threads='2'/>
  <cache mode='passthrough'/>
  <feature policy='require' name='topoext'/>
</cpu>
EOFXML
    
    echo ""
    echo -e "${BOLD}To apply:${NC}"
    echo "  1. virsh edit $selected_vm"
    echo "  2. Copy the above XML into the <domain> section"
    echo "  3. Save and restart the VM"
    
    echo ""
    read -p "Save to file? [y/N]: " save
    
    if [[ "$save" =~ ^[Yy]$ ]]; then
        local output_file="/home/$SUDO_USER/${selected_vm}-cpu-config.xml"
        
        cat > "$output_file" << EOFXML
<!-- VM CPU Configuration for: $selected_vm -->
<!-- Description: $DESCRIPTION -->
<!-- Generated: $(date) -->

<vcpu placement='static'>$vcpu_count</vcpu>
<cputune>
EOFXML
        
        local vcpu_idx=0
        local IFS=','
        for range in $VCPU_CPUS; do
            if [[ "$range" =~ ^([0-9]+)-([0-9]+)$ ]]; then
                local start="${BASH_REMATCH[1]}"
                local end="${BASH_REMATCH[2]}"
                for ((cpu=start; cpu<=end; cpu+=1)); do
                    echo "  <vcpupin vcpu='$vcpu_idx' cpuset='$cpu'/>" >> "$output_file"
                    vcpu_idx=$((vcpu_idx + 1))
                done
            elif [[ "$range" =~ ^[0-9]+$ ]]; then
                echo "  <vcpupin vcpu='$vcpu_idx' cpuset='$range'/>" >> "$output_file"
                vcpu_idx=$((vcpu_idx + 1))
            fi
        done
        
        cat >> "$output_file" << EOFXML
  <emulatorpin cpuset='$EMULATOR_CPUS'/>
  <iothreadpin iothread='1' cpuset='$EMULATOR_CPUS'/>
</cputune>

<cpu mode='host-passthrough'>
  <topology sockets='1' dies='1' cores='$(($vcpu_count / 2))' threads='2'/>
  <cache mode='passthrough'/>
  <feature policy='require' name='topoext'/>
</cpu>
EOFXML
        
        chown "$SUDO_USER:$SUDO_USER" "$output_file"
        log_success "Saved to: $output_file"
    fi
    
    echo ""
    read -p "Press Enter to return to menu..."
    main_menu
}

# Export/Import menu
export_import_menu() {
    log_header "Export/Import Configurations"
    
    echo "  ${TEAL}1)${NC} Export all configurations"
    echo "  ${TEAL}2)${NC} Import configurations"
    echo "  ${TEAL}3)${NC} Back to main menu"
    echo ""
    
    read -p "Selection: " choice
    
    case $choice in
        1) export_configs ;;
        2) import_configs ;;
        3) main_menu ;;
        *) main_menu ;;
    esac
}

# Export configurations
export_configs() {
    local export_file="/home/$SUDO_USER/vm-cpu-configs-$(date +%Y%m%d-%H%M%S).tar.gz"
    
    if [[ ! -d "$CONFIG_DIR" ]] || [[ -z "$(ls -A "$CONFIG_DIR" 2>/dev/null)" ]]; then
        log_warning "No configurations to export"
        sleep 2
        main_menu
        return
    fi
    
    tar czf "$export_file" -C "$(dirname "$CONFIG_DIR")" "$(basename "$CONFIG_DIR")"
    chown "$SUDO_USER:$SUDO_USER" "$export_file"
    
    log_success "Exported to: $export_file"
    
    sleep 2
    main_menu
}

# Import configurations
import_configs() {
    echo ""
    read -p "Path to import file: " import_file
    
    if [[ ! -f "$import_file" ]]; then
        log_error "File not found"
        sleep 2
        main_menu
        return
    fi
    
    # Backup existing configs
    if [[ -d "$CONFIG_DIR" ]]; then
        mv "$CONFIG_DIR" "${CONFIG_DIR}${BACKUP_SUFFIX}"
        log_info "Backed up existing configs"
    fi
    
    tar xzf "$import_file" -C "$(dirname "$CONFIG_DIR")"
    
    # Recreate hooks
    for config in "$CONFIG_DIR"/*.conf; do
        local vm_name=$(basename "$config" .conf)
        source "$config"
        
        # Recreate hook structure
        local vm_hook_dir="$HOOK_DIR/qemu.d/${vm_name}"
        mkdir -p "$vm_hook_dir/prepare/begin"
        mkdir -p "$vm_hook_dir/release/end"
        
        # Note: Hooks need to be regenerated with current paths
        log_warning "Hooks for $vm_name need to be regenerated"
    done
    
    log_success "Import complete - regenerate hooks via Option 1"
    
    sleep 2
    main_menu
}

# Verify hook integrity
verify_hooks() {
    log_header "Hook Integrity Verification"
    
    if [[ ! -d "$CONFIG_DIR" ]] || [[ -z "$(ls -A "$CONFIG_DIR" 2>/dev/null)" ]]; then
        log_warning "No configurations found"
        echo ""
        read -p "Press Enter to return to menu..."
        main_menu
        return
    fi
    
    local errors=0
    
    for config in "$CONFIG_DIR"/*.conf; do
        local vm_name=$(basename "$config" .conf)
        
        echo -e "${CYAN}Checking: ${vm_name}${NC}"
        
        # Check config file
        if [[ ! -f "$config" ]]; then
            echo -e "  ${CORAL}Ã¢Å“â€” Config file missing${NC}"
            errors=$((errors + 1))
        else
            echo -e "  ${SUCCESS}Ã¢Å“" Config file present${NC}"
        fi
        
        # Check hook directory
        if [[ ! -d "$HOOK_DIR/qemu.d/${vm_name}" ]]; then
            echo -e "  ${CORAL}Ã¢Å“â€” Hook directory missing${NC}"
            errors=$((errors + 1))
        else
            echo -e "  ${SUCCESS}Ã¢Å“" Hook directory present${NC}"
        fi
        
        # Check prepare hook
        if [[ ! -x "$HOOK_DIR/qemu.d/${vm_name}/prepare/begin/cpu-pin.sh" ]]; then
            echo -e "  ${CORAL}Ã¢Å“â€” Prepare hook missing or not executable${NC}"
            errors=$((errors + 1))
        else
            echo -e "  ${SUCCESS}Ã¢Å“" Prepare hook executable${NC}"
        fi
        
        # Check release hook
        if [[ ! -x "$HOOK_DIR/qemu.d/${vm_name}/release/end/cpu-cleanup.sh" ]]; then
            echo -e "  ${CORAL}Ã¢Å“â€” Release hook missing or not executable${NC}"
            errors=$((errors + 1))
        else
            echo -e "  ${SUCCESS}Ã¢Å“" Release hook executable${NC}"
        fi
        
        echo ""
    done
    
    if [[ $errors -eq 0 ]]; then
        log_success "All hooks verified successfully"
    else
        log_warning "Found $errors issue(s)"
    fi
    
    echo ""
    read -p "Press Enter to return to menu..."
    main_menu
}

# Main execution
main() {
    check_root
    
    # Create directories
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$HOOK_DIR/qemu.d"
    mkdir -p /var/log/libvirt/qemu
    
    # Detect topology
    detect_cpu_topology
    
    # Show main menu
    main_menu
}

main "$@"

#!/bin/bash
###############################################################################
# Universal CPU Core Isolation Configurator
# For MiOS-Build Professional Virtualization Hosts
# Optimized for: AMD Ryzen X3D (dual-CCD), Intel Hybrid (P/E-cores), NUMA
# Compatible with: systemd-boot, GRUB, dynamic affinity management
###############################################################################

set -euo pipefail

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly BOLD='\033[1m'
readonly DIM='\033[2m'
readonly NC='\033[0m'

# Configuration
readonly BACKUP_SUFFIX=".backup-$(date +%Y%m%d-%H%M%S)"

# CPU Topology Data
declare -A CPU_INFO
declare -a ISOLATED_CPUS=()
declare -a HOST_CPUS=()
declare -a CCD_MAP=()
declare -A NUMA_MAP

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[âœ"]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[âš ]${NC} $1"; }
log_error() { echo -e "${RED}[âœ--]${NC} $1"; }
log_header() {
    echo ""
    echo -e "${CYAN}â*"â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*--${NC}"
    echo -e "${CYAN}â*'${NC} ${BOLD}$1${NC}"
    echo -e "${CYAN}â*šâ*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*${NC}"
    echo ""
}

# Check root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

# Detect CPU topology
detect_cpu_topology() {
    log_header "CPU Topology Detection"
    
    # Basic CPU info
    CPU_INFO[vendor]=$(lscpu | grep "Vendor ID" | awk '{print $3}')
    CPU_INFO[model]=$(lscpu | grep "Model name" | sed 's/Model name:[[:space:]]*//')
    CPU_INFO[cores]=$(lscpu | grep "^Core(s) per socket:" | awk '{print $4}')
    CPU_INFO[threads]=$(lscpu | grep "^CPU(s):" | head -1 | awk '{print $2}')
    CPU_INFO[sockets]=$(lscpu | grep "Socket(s):" | awk '{print $2}')
    CPU_INFO[threads_per_core]=$(lscpu | grep "Thread(s) per core:" | awk '{print $4}')
    
    log_success "CPU: ${CPU_INFO[model]}"
    log_info "Topology: ${CPU_INFO[sockets]} socket(s), ${CPU_INFO[cores]} cores, ${CPU_INFO[threads]} threads"
    
    # Detect NUMA
    CPU_INFO[numa_nodes]=$(lscpu | grep "NUMA node(s):" | awk '{print $3}')
    log_info "NUMA nodes: ${CPU_INFO[numa_nodes]}"
    
    # Build NUMA map
    for ((node=0; node<${CPU_INFO[numa_nodes]}; node+=1)); do
        local cpus=$(lscpu | grep "NUMA node${node} CPU(s):" | awk '{print $4}')
        NUMA_MAP[$node]="$cpus"
    done
    
    # Detect AMD CCD architecture (Ryzen X3D)
    detect_amd_ccds
    
    # Detect Intel Hybrid (P-cores/E-cores)
    detect_intel_hybrid
    
    echo ""
}

# Detect AMD CCD layout (for Ryzen 9950X3D, 7950X3D, etc.)
detect_amd_ccds() {
    if [[ "${CPU_INFO[vendor]}" != "AuthenticAMD" ]]; then
        return
    fi
    
    # Check for X3D CPUs
    if [[ "${CPU_INFO[model]}" =~ (9950X3D|7950X3D|7900X3D) ]]; then
        log_info "Detected AMD X3D CPU with dual-CCD architecture"
        
        # For 9950X3D and 7950X3D: 16 cores split into 2 CCDs
        local cores_per_ccd=$((${CPU_INFO[cores]} / 2))
        local threads_per_ccd=$((cores_per_ccd * ${CPU_INFO[threads_per_core]}))
        
        CPU_INFO[has_ccds]=1
        CPU_INFO[ccd_count]=2
        CPU_INFO[cores_per_ccd]=$cores_per_ccd
        
        # CCD0: Usually has V-Cache
        CCD_MAP[0]="0-$((threads_per_ccd - 1))"
        # CCD1: Usually higher frequency
        CCD_MAP[1]="$threads_per_ccd-$((${CPU_INFO[threads]} - 1))"
        
        log_success "CCD0 (V-Cache): CPUs ${CCD_MAP[0]}"
        log_success "CCD1 (High Freq): CPUs ${CCD_MAP[1]}"
        
        # Check for V-Cache indicator
        if [[ -f /sys/devices/system/cpu/cpu0/cache/index3/size ]]; then
            local l3_size=$(cat /sys/devices/system/cpu/cpu0/cache/index3/size)
            log_info "L3 Cache detected: $l3_size"
        fi
    fi
}

# Detect Intel Hybrid architecture (12th gen+)
detect_intel_hybrid() {
    if [[ "${CPU_INFO[vendor]}" != "GenuineIntel" ]]; then
        return
    fi
    
    # Check for hybrid architecture markers
    if lscpu | grep -q "Core(s) per socket:.*P-core\|E-core"; then
        log_info "Detected Intel Hybrid architecture (P-cores + E-cores)"
        CPU_INFO[has_hybrid]=1
        
        # Parse P-core and E-core counts (requires detailed lscpu parsing)
        # This is a simplified detection
        log_warning "Intel Hybrid detected - manual verification recommended"
    fi
}

# Visual CPU topology display
display_cpu_topology() {
    log_header "CPU Topology Visualization"
    
    local total_cpus=${CPU_INFO[threads]}
    local smt_enabled=$([[ ${CPU_INFO[threads_per_core]} -eq 2 ]] && echo "Yes" || echo "No")
    
    echo -e "${CYAN}â*"â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*--${NC}"
    echo -e "${CYAN}â*'${NC} ${BOLD}CPU Configuration${NC}"
    echo -e "${CYAN}â* â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*£${NC}"
    echo -e "${CYAN}â*'${NC} Model:        ${CPU_INFO[model]}"
    echo -e "${CYAN}â*'${NC} Cores:        ${CPU_INFO[cores]} physical"
    echo -e "${CYAN}â*'${NC} Threads:      ${CPU_INFO[threads]} logical (SMT: $smt_enabled)"
    echo -e "${CYAN}â*'${NC} NUMA Nodes:   ${CPU_INFO[numa_nodes]}"
    
    if [[ -n "${CPU_INFO[has_ccds]}" ]]; then
        echo -e "${CYAN}â*'${NC} CCDs:         ${CPU_INFO[ccd_count]} (AMD X3D)"
    fi
    
    echo -e "${CYAN}â*šâ*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*${NC}"
    echo ""
    
    # Visual CPU grid
    if [[ -n "${CPU_INFO[has_ccds]}" ]]; then
        display_ccd_layout
    elif [[ ${CPU_INFO[numa_nodes]} -gt 1 ]]; then
        display_numa_layout
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
            echo -e "${GREEN}CCD${ccd}${NC} ${BOLD}(V-Cache - Best for Gaming/Latency)${NC}"
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

# Display NUMA-based layout
display_numa_layout() {
    echo -e "${BOLD}CPU Layout by NUMA Node:${NC}"
    echo ""
    
    for ((node=0; node<${CPU_INFO[numa_nodes]}; node+=1)); do
        echo -e "${MAGENTA}NUMA Node ${node}${NC}"
        echo "  CPUs: ${NUMA_MAP[$node]}"
        echo ""
    done
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

# Interactive isolation mode selection
select_isolation_mode() {
    log_header "Isolation Mode Selection"
    
    echo "Choose isolation strategy:"
    echo ""
    echo "  ${BOLD}1)${NC} Quick Presets (Recommended)"
    echo "     - Gaming VM (isolate V-Cache CCD)"
    echo "     - Balanced (50/50 split)"
    echo "     - Host Priority (minimal isolation)"
    echo ""
    echo "  ${BOLD}2)${NC} CCD-Based Selection (AMD X3D)"
    echo "     - Select entire CCDs"
    echo ""
    echo "  ${BOLD}3)${NC} NUMA-Based Selection"
    echo "     - Select by NUMA node"
    echo ""
    echo "  ${BOLD}4)${NC} Custom Core Selection"
    echo "     - Manually select cores/threads"
    echo ""
    echo "  ${BOLD}5)${NC} Advanced (Hybrid P/E-cores, ranges)"
    echo ""
    
    read -p "Selection [1-5]: " mode
    
    case $mode in
        1) select_quick_preset ;;
        2) select_by_ccd ;;
        3) select_by_numa ;;
        4) select_custom_cores ;;
        5) select_advanced ;;
        *) log_error "Invalid selection"; exit 1 ;;
    esac
}

# Quick presets
select_quick_preset() {
    log_header "Quick Presets"
    
    echo "Available presets:"
    echo ""
    
    if [[ -n "${CPU_INFO[has_ccds]}" ]]; then
        echo "  ${BOLD}1)${NC} Gaming VM Optimized ${GREEN}(Recommended for X3D)${NC}"
        echo "     - Isolate: CCD0 (V-Cache) for VM"
        echo "     - Host: CCD1 (High Freq)"
        echo ""
        echo "  ${BOLD}2)${NC} Render/Compute Optimized"
        echo "     - Isolate: CCD1 (High Freq) for VM"
        echo "     - Host: CCD0 (V-Cache)"
        echo ""
        echo "  ${BOLD}3)${NC} Balanced (50/50)"
        echo "     - Isolate: Half of each CCD"
        echo "     - Host: Remaining half"
        echo ""
        echo "  ${BOLD}4)${NC} Host Priority ${DIM}(Minimal Host - Maximum VM Performance)${NC}"
        echo "     - Host: Cores 0,1,8,9 + SMT (8 threads)"
        echo "     - VMs: Cores 2-7,10-15 + SMT (24 threads)"
        echo "     - ${GREEN}Maximizes V-Cache availability${NC}"
        echo ""
    else
        echo "  ${BOLD}1)${NC} Balanced (50/50)"
        echo "     - Isolate: Half of cores"
        echo "     - Host: Half of cores"
        echo ""
        echo "  ${BOLD}2)${NC} VM Priority (75/25)"
        echo "     - Isolate: 75% of cores"
        echo "     - Host: 25% of cores"
        echo ""
        echo "  ${BOLD}3)${NC} Host Priority (25/75)"
        echo "     - Isolate: 25% of cores"
        echo "     - Host: 75% of cores"
        echo ""
    fi
    
    read -p "Preset [1-4]: " preset
    
    if [[ -n "${CPU_INFO[has_ccds]}" ]]; then
        case $preset in
            1) preset_x3d_gaming ;;
            2) preset_x3d_compute ;;
            3) preset_balanced ;;
            4) preset_host_priority ;;
            *) log_error "Invalid preset"; exit 1 ;;
        esac
    else
        case $preset in
            1) preset_balanced ;;
            2) preset_vm_priority ;;
            3) preset_host_priority ;;
            *) log_error "Invalid preset"; exit 1 ;;
        esac
    fi
}

# X3D Gaming preset (isolate CCD0)
preset_x3d_gaming() {
    log_info "Applying Gaming VM preset (CCD0 isolation)..."
    
    local threads_per_ccd=$((${CPU_INFO[threads]} / 2))
    
    # Isolate CCD0 (0 to threads_per_ccd-1)
    for ((cpu=0; cpu<threads_per_ccd; cpu+=1)); do
        ISOLATED_CPUS+=($cpu)
    done
    
    # Host gets CCD1
    for ((cpu=threads_per_ccd; cpu<${CPU_INFO[threads]}; cpu+=1)); do
        HOST_CPUS+=($cpu)
    done
    
    log_success "Isolated CCD0 (V-Cache): CPUs ${ISOLATED_CPUS[*]}"
    log_success "Host CCD1 (High Freq): CPUs ${HOST_CPUS[*]}"
}

# X3D Compute preset (isolate CCD1)
preset_x3d_compute() {
    log_info "Applying Compute preset (CCD1 isolation)..."
    
    local threads_per_ccd=$((${CPU_INFO[threads]} / 2))
    
    # Host gets CCD0
    for ((cpu=0; cpu<threads_per_ccd; cpu+=1)); do
        HOST_CPUS+=($cpu)
    done
    
    # Isolate CCD1
    for ((cpu=threads_per_ccd; cpu<${CPU_INFO[threads]}; cpu+=1)); do
        ISOLATED_CPUS+=($cpu)
    done
    
    log_success "Host CCD0 (V-Cache): CPUs ${HOST_CPUS[*]}"
    log_success "Isolated CCD1 (High Freq): CPUs ${ISOLATED_CPUS[*]}"
}

# Balanced preset
preset_balanced() {
    log_info "Applying Balanced preset (50/50 split)..."
    
    local half=$((${CPU_INFO[threads]} / 2))
    
    for ((cpu=0; cpu<half; cpu+=1)); do
        ISOLATED_CPUS+=($cpu)
    done
    
    for ((cpu=half; cpu<${CPU_INFO[threads]}; cpu+=1)); do
        HOST_CPUS+=($cpu)
    done
    
    log_success "Isolated: CPUs ${ISOLATED_CPUS[*]}"
    log_success "Host: CPUs ${HOST_CPUS[*]}"
}

# Host priority preset (optimized for dual-CCD systems)
preset_host_priority() {
    log_info "Applying Host Priority preset (Minimal host cores)..."
    
    if [[ -n "${CPU_INFO[has_ccds]}" ]]; then
        # Dual-CCD optimization: Physical cores 0,1 from CCD0 and cores 8,9 from CCD1
        # With SMT, this is CPUs: 0,1,8,9 (first threads) + 16,17,24,25 (SMT siblings)
        local total_cores=${CPU_INFO[cores]}
        local threads_per_core=${CPU_INFO[threads_per_core]}
        
        # Host gets: Physical cores 0, 1, 8, 9 and their SMT siblings
        # For 16 physical cores with SMT: cores 0-7 map to CPUs 0-7,16-23 and cores 8-15 map to CPUs 8-15,24-31
        
        # CCD0 core 0 and core 1: CPUs 0, 1 (first thread)
        HOST_CPUS+=(0 1)
        # CCD1 core 8 and core 9: CPUs 8, 9 (first thread)  
        HOST_CPUS+=(8 9)
        
        # Add SMT siblings if SMT is enabled
        if [[ $threads_per_core -eq 2 ]]; then
            # SMT siblings are typically at +cores offset
            HOST_CPUS+=(16 17 24 25)
        fi
        
        # VMs get everything else
        for ((cpu=0; cpu<${CPU_INFO[threads]}; cpu+=1)); do
            if [[ ! " ${HOST_CPUS[*]} " =~ " $cpu " ]]; then
                ISOLATED_CPUS+=($cpu)
            fi
        done
        
        # Sort the arrays for cleaner display
        HOST_CPUS=($(printf '%s\n' "${HOST_CPUS[@]}" | sort -n))
        ISOLATED_CPUS=($(printf '%s\n' "${ISOLATED_CPUS[@]}" | sort -n))
        
        log_success "Host CPUs (cores 0,1,8,9): ${HOST_CPUS[*]}"
        log_success "VM CPUs (remaining cores): ${ISOLATED_CPUS[*]}"
        log_success "Total: Host ${#HOST_CPUS[@]} threads (4 cores), VMs ${#ISOLATED_CPUS[@]} threads (12 cores)"
    else
        # Generic CPU: Reserve minimum 8 threads for host
        local vm_cores=$((${CPU_INFO[threads]} - 8))
        
        # First threads for host
        for ((cpu=0; cpu<8; cpu+=1)); do
            HOST_CPUS+=($cpu)
        done
        
        # Rest for VMs
        for ((cpu=8; cpu<${CPU_INFO[threads]}; cpu+=1)); do
            ISOLATED_CPUS+=($cpu)
        done
        
        log_success "Host: CPUs ${HOST_CPUS[*]}"
        log_success "Isolated: CPUs ${ISOLATED_CPUS[*]}"
    fi
}

# VM priority preset
preset_vm_priority() {
    log_info "Applying VM Priority preset (75/25)..."
    
    local host_cores=$((${CPU_INFO[threads]} / 4))
    
    # Host gets 25%
    for ((cpu=0; cpu<host_cores; cpu+=1)); do
        HOST_CPUS+=($cpu)
    done
    
    # VMs get 75%
    for ((cpu=host_cores; cpu<${CPU_INFO[threads]}; cpu+=1)); do
        ISOLATED_CPUS+=($cpu)
    done
    
    log_success "Host: CPUs ${HOST_CPUS[*]}"
    log_success "Isolated: CPUs ${ISOLATED_CPUS[*]}"
}

# CCD-based selection
select_by_ccd() {
    if [[ -z "${CPU_INFO[has_ccds]}" ]]; then
        log_error "CCD detection not available for this CPU"
        exit 1
    fi
    
    log_header "CCD-Based Selection"
    
    echo "Select CCDs to isolate for VMs:"
    echo ""
    echo "  CCD0: ${CCD_MAP[0]} ${GREEN}(V-Cache - Gaming)${NC}"
    echo "  CCD1: ${CCD_MAP[1]} ${YELLOW}(High Freq - Compute)${NC}"
    echo ""
    echo "Options:"
    echo "  1) Isolate CCD0 only"
    echo "  2) Isolate CCD1 only"
    echo "  3) Isolate both CCDs (host uses minimal cores)"
    echo ""
    
    read -p "Selection [1-3]: " ccd_choice
    
    local threads_per_ccd=$((${CPU_INFO[threads]} / 2))
    
    case $ccd_choice in
        1)
            for ((cpu=0; cpu<threads_per_ccd; cpu+=1)); do
                ISOLATED_CPUS+=($cpu)
            done
            for ((cpu=threads_per_ccd; cpu<${CPU_INFO[threads]}; cpu+=1)); do
                HOST_CPUS+=($cpu)
            done
            ;;
        2)
            for ((cpu=0; cpu<threads_per_ccd; cpu+=1)); do
                HOST_CPUS+=($cpu)
            done
            for ((cpu=threads_per_ccd; cpu<${CPU_INFO[threads]}; cpu+=1)); do
                ISOLATED_CPUS+=($cpu)
            done
            ;;
        3)
            # Reserve first 4 threads for host, rest isolated
            for ((cpu=0; cpu<4; cpu+=1)); do
                HOST_CPUS+=($cpu)
            done
            for ((cpu=4; cpu<${CPU_INFO[threads]}; cpu+=1)); do
                ISOLATED_CPUS+=($cpu)
            done
            ;;
        *)
            log_error "Invalid selection"
            exit 1
            ;;
    esac
    
    log_success "Isolated CPUs: ${ISOLATED_CPUS[*]}"
    log_success "Host CPUs: ${HOST_CPUS[*]}"
}

# NUMA-based selection
select_by_numa() {
    if [[ ${CPU_INFO[numa_nodes]} -eq 1 ]]; then
        log_error "Single NUMA node system - use other selection methods"
        exit 1
    fi
    
    log_header "NUMA-Based Selection"
    
    echo "Select NUMA nodes to isolate:"
    echo ""
    
    for ((node=0; node<${CPU_INFO[numa_nodes]}; node+=1)); do
        echo "  NUMA Node $node: ${NUMA_MAP[$node]}"
    done
    
    echo ""
    read -p "Isolate which NUMA node(s)? (e.g., '0' or '0 1'): " numa_selection
    
    # Parse selected nodes
    for node in $numa_selection; do
        local cpus="${NUMA_MAP[$node]}"
        # Expand range (e.g., "0-7" to individual CPUs)
        eval "local cpu_array=({$cpus})"
        ISOLATED_CPUS+=("${cpu_array[@]}")
    done
    
    # Remaining CPUs for host
    for ((cpu=0; cpu<${CPU_INFO[threads]}; cpu+=1)); do
        if [[ ! " ${ISOLATED_CPUS[*]} " =~ " $cpu " ]]; then
            HOST_CPUS+=($cpu)
        fi
    done
    
    log_success "Isolated CPUs: ${ISOLATED_CPUS[*]}"
    log_success "Host CPUs: ${HOST_CPUS[*]}"
}

# Custom core selection
select_custom_cores() {
    log_header "Custom Core Selection"
    
    display_cpu_topology
    
    echo "Enter CPU numbers to isolate for VMs."
    echo "Formats supported:"
    echo "  - Individual: 0 1 2 3"
    echo "  - Ranges: 0-7 16-23"
    echo "  - Mixed: 0-7 16 17 18-23"
    echo ""
    
    read -p "CPUs to isolate: " cpu_input
    
    # Parse input
    for token in $cpu_input; do
        if [[ "$token" =~ ^([0-9]+)-([0-9]+)$ ]]; then
            # Range
            local start="${BASH_REMATCH[1]}"
            local end="${BASH_REMATCH[2]}"
            for ((cpu=start; cpu<=end; cpu+=1)); do
                ISOLATED_CPUS+=($cpu)
            done
        elif [[ "$token" =~ ^[0-9]+$ ]]; then
            # Individual CPU
            ISOLATED_CPUS+=($token)
        fi
    done
    
    # Validate and deduplicate
    ISOLATED_CPUS=($(printf '%s\n' "${ISOLATED_CPUS[@]}" | sort -nu))
    
    # Remaining for host
    for ((cpu=0; cpu<${CPU_INFO[threads]}; cpu+=1)); do
        if [[ ! " ${ISOLATED_CPUS[*]} " =~ " $cpu " ]]; then
            HOST_CPUS+=($cpu)
        fi
    done
    
    if [[ ${#ISOLATED_CPUS[@]} -eq 0 ]]; then
        log_error "No CPUs selected"
        exit 1
    fi
    
    log_success "Isolated CPUs (${#ISOLATED_CPUS[@]}): ${ISOLATED_CPUS[*]}"
    log_success "Host CPUs (${#HOST_CPUS[@]}): ${HOST_CPUS[*]}"
}

# Advanced selection
select_advanced() {
    log_header "Advanced Selection"
    
    echo "Advanced options:"
    echo ""
    echo "  1) SMT-aware (isolate physical cores + siblings)"
    echo "  2) Exclude specific cores (e.g., keep core 0 for host)"
    echo "  3) Performance cores only (Intel Hybrid)"
    echo "  4) Import from file"
    echo ""
    
    read -p "Selection [1-4]: " adv_choice
    
    case $adv_choice in
        1) select_smt_aware ;;
        2) select_exclude_cores ;;
        3) select_performance_cores ;;
        4) select_from_file ;;
        *) log_error "Invalid selection"; exit 1 ;;
    esac
}

# SMT-aware selection
select_smt_aware() {
    echo ""
    echo "Enter physical core numbers (SMT siblings will be included automatically):"
    read -p "Physical cores: " cores_input
    
    local cores_per_socket=$((${CPU_INFO[threads]} / ${CPU_INFO[threads_per_core]}))
    
    for core in $cores_input; do
        if [[ $core -ge $cores_per_socket ]]; then
            log_error "Invalid core number: $core (max: $((cores_per_socket - 1)))"
            exit 1
        fi
        
        # Add physical core
        ISOLATED_CPUS+=($core)
        
        # Add SMT sibling if exists
        if [[ ${CPU_INFO[threads_per_core]} -eq 2 ]]; then
            local sibling=$((core + cores_per_socket))
            ISOLATED_CPUS+=($sibling)
        fi
    done
    
    # Sort and deduplicate
    ISOLATED_CPUS=($(printf '%s\n' "${ISOLATED_CPUS[@]}" | sort -nu))
    
    # Remaining for host
    for ((cpu=0; cpu<${CPU_INFO[threads]}; cpu+=1)); do
        if [[ ! " ${ISOLATED_CPUS[*]} " =~ " $cpu " ]]; then
            HOST_CPUS+=($cpu)
        fi
    done
    
    log_success "Isolated CPUs: ${ISOLATED_CPUS[*]}"
    log_success "Host CPUs: ${HOST_CPUS[*]}"
}

# Exclude specific cores
select_exclude_cores() {
    echo ""
    echo "This will isolate all cores EXCEPT the ones you specify."
    echo "Common: Keep CPU 0 for host (kernel interrupts)"
    echo ""
    read -p "CPUs to keep for host: " host_input
    
    # Parse host CPUs
    for token in $host_input; do
        if [[ "$token" =~ ^([0-9]+)-([0-9]+)$ ]]; then
            local start="${BASH_REMATCH[1]}"
            local end="${BASH_REMATCH[2]}"
            for ((cpu=start; cpu<=end; cpu+=1)); do
                HOST_CPUS+=($cpu)
            done
        elif [[ "$token" =~ ^[0-9]+$ ]]; then
            HOST_CPUS+=($token)
        fi
    done
    
    HOST_CPUS=($(printf '%s\n' "${HOST_CPUS[@]}" | sort -nu))
    
    # Remaining for VMs
    for ((cpu=0; cpu<${CPU_INFO[threads]}; cpu+=1)); do
        if [[ ! " ${HOST_CPUS[*]} " =~ " $cpu " ]]; then
            ISOLATED_CPUS+=($cpu)
        fi
    done
    
    log_success "Host CPUs: ${HOST_CPUS[*]}"
    log_success "Isolated CPUs: ${ISOLATED_CPUS[*]}"
}

# Performance cores (Intel Hybrid)
select_performance_cores() {
    if [[ -z "${CPU_INFO[has_hybrid]}" ]]; then
        log_warning "Hybrid architecture not detected - using generic selection"
    fi
    
    echo ""
    echo "Enter range for Performance cores (e.g., 0-15):"
    read -p "P-core range: " pcore_range
    
    if [[ "$pcore_range" =~ ^([0-9]+)-([0-9]+)$ ]]; then
        local start="${BASH_REMATCH[1]}"
        local end="${BASH_REMATCH[2]}"
        for ((cpu=start; cpu<=end; cpu+=1)); do
            ISOLATED_CPUS+=($cpu)
        done
    fi
    
    # Remaining for host
    for ((cpu=0; cpu<${CPU_INFO[threads]}; cpu+=1)); do
        if [[ ! " ${ISOLATED_CPUS[*]} " =~ " $cpu " ]]; then
            HOST_CPUS+=($cpu)
        fi
    done
    
    log_success "Isolated P-cores: ${ISOLATED_CPUS[*]}"
    log_success "Host CPUs: ${HOST_CPUS[*]}"
}

# Import from file
select_from_file() {
    echo ""
    read -p "Path to CPU list file: " file_path
    
    if [[ ! -f "$file_path" ]]; then
        log_error "File not found: $file_path"
        exit 1
    fi
    
    while read -r line; do
        for token in $line; do
            if [[ "$token" =~ ^[0-9]+$ ]]; then
                ISOLATED_CPUS+=($token)
            fi
        done
    done < "$file_path"
    
    ISOLATED_CPUS=($(printf '%s\n' "${ISOLATED_CPUS[@]}" | sort -nu))
    
    # Remaining for host
    for ((cpu=0; cpu<${CPU_INFO[threads]}; cpu+=1)); do
        if [[ ! " ${ISOLATED_CPUS[*]} " =~ " $cpu " ]]; then
            HOST_CPUS+=($cpu)
        fi
    done
    
    log_success "Loaded from file: ${ISOLATED_CPUS[*]}"
}

# Review selection
review_selection() {
    log_header "Review Selection"
    
    echo -e "${BOLD}Configuration Summary:${NC}"
    echo ""
    echo -e "${GREEN}Isolated CPUs (for VMs):${NC}"
    echo "  Count: ${#ISOLATED_CPUS[@]}"
    echo "  CPUs: ${ISOLATED_CPUS[*]}"
    echo ""
    echo -e "${YELLOW}Host CPUs (for system):${NC}"
    echo "  Count: ${#HOST_CPUS[@]}"
    echo "  CPUs: ${HOST_CPUS[*]}"
    echo ""
    
    # Validate
    local total=$((${#ISOLATED_CPUS[@]} + ${#HOST_CPUS[@]}))
    if [[ $total -ne ${CPU_INFO[threads]} ]]; then
        log_error "CPU count mismatch: $total vs ${CPU_INFO[threads]}"
        exit 1
    fi
    
    if [[ ${#HOST_CPUS[@]} -lt 2 ]]; then
        log_warning "Host has only ${#HOST_CPUS[@]} CPU(s) - may cause performance issues"
    fi
    
    echo ""
    read -p "Proceed with this configuration? [Y/n]: " confirm
    
    if [[ "$confirm" =~ ^[Nn] ]]; then
        log_info "Configuration cancelled"
        exit 0
    fi
}

# Configure isolation method
configure_isolation() {
    log_header "Isolation Method Configuration"
    
    echo "Choose isolation implementation:"
    echo ""
    echo "  ${BOLD}1)${NC} Kernel isolcpus (Recommended)"
    echo "     - Boot-time CPU isolation"
    echo "     - Maximum performance"
    echo "     - Requires reboot"
    echo ""
    echo "  ${BOLD}2)${NC} systemd CPUAffinity"
    echo "     - Dynamic host affinity"
    echo "     - No reboot needed"
    echo "     - Slightly lower isolation"
    echo ""
    echo "  ${BOLD}3)${NC} Both (Maximum isolation)"
    echo "     - Kernel isolcpus + systemd"
    echo "     - Best for production"
    echo ""
    
    read -p "Selection [1-3]: " method
    
    case $method in
        1) configure_isolcpus ;;
        2) configure_systemd_affinity ;;
        3) configure_isolcpus; configure_systemd_affinity ;;
        *) log_error "Invalid selection"; exit 1 ;;
    esac
    
    # Always create libvirt hooks
    create_libvirt_hooks
    
    # Create helper scripts
    create_helper_scripts
}

# Configure kernel isolcpus
configure_isolcpus() {
    log_info "Configuring kernel isolcpus parameter..."
    
    # Build isolcpus range
    local isolcpus_param=$(printf '%s,' "${ISOLATED_CPUS[@]}")
    isolcpus_param=${isolcpus_param%,}  # Remove trailing comma
    
    # Detect bootloader
    if [[ -d /boot/loader/entries ]] && command -v bootctl &>/dev/null; then
        configure_isolcpus_systemd_boot "$isolcpus_param"
    elif [[ -f /etc/default/grub ]]; then
        configure_isolcpus_grub "$isolcpus_param"
    else
        log_warning "Bootloader not detected - manual configuration required"
        echo "Add this to kernel parameters:"
        echo "  isolcpus=$isolcpus_param nohz_full=$isolcpus_param rcu_nocbs=$isolcpus_param"
    fi
}

# Configure isolcpus for systemd-boot
configure_isolcpus_systemd_boot() {
    local isolcpus="$1"
    local params="isolcpus=$isolcpus nohz_full=$isolcpus rcu_nocbs=$isolcpus"
    
    log_info "Updating systemd-boot entries..."
    
    local entries=$(find /boot/loader/entries -name "*.conf" | grep -v backup | sort)
    
    echo "Found boot entries:"
    echo "$entries" | nl -w2 -s'. '
    echo ""
    
    read -p "Update which entry? (number or 'all'): " entry_choice
    
    local selected
    if [[ "$entry_choice" == "all" ]]; then
        selected="$entries"
    else
        selected=$(echo "$entries" | sed -n "${entry_choice}p")
    fi
    
    for entry in $selected; do
        cp "$entry" "${entry}${BACKUP_SUFFIX}"
        
        # Remove old isolcpus parameters
        sed -i 's/isolcpus=[^ ]* //g' "$entry"
        sed -i 's/nohz_full=[^ ]* //g' "$entry"
        sed -i 's/rcu_nocbs=[^ ]* //g' "$entry"
        
        # Add new parameters
        sed -i "/^options / s/$/ $params/" "$entry"
        
        log_success "Updated: $(basename $entry)"
    done
    
    bootctl update
}

# Configure isolcpus for GRUB
configure_isolcpus_grub() {
    local isolcpus="$1"
    local params="isolcpus=$isolcpus nohz_full=$isolcpus rcu_nocbs=$isolcpus"
    
    log_info "Updating GRUB configuration..."
    
    local grub_conf="/etc/default/grub"
    cp "$grub_conf" "${grub_conf}${BACKUP_SUFFIX}"
    
    # Remove old parameters
    sed -i 's/isolcpus=[^ "]* //g' "$grub_conf"
    sed -i 's/nohz_full=[^ "]* //g' "$grub_conf"
    sed -i 's/rcu_nocbs=[^ "]* //g' "$grub_conf"
    
    # Add new parameters
    sed -i "/GRUB_CMDLINE_LINUX_DEFAULT/ s/\"$/ $params\"/" "$grub_conf"
    
    # Regenerate GRUB config
    if command -v grub-mkconfig &>/dev/null; then
        grub-mkconfig -o /boot/grub/grub.cfg
    elif command -v grub2-mkconfig &>/dev/null; then
        grub2-mkconfig -o /boot/grub2/grub.cfg
    fi
    
    log_success "GRUB configuration updated"
}

# Configure systemd CPUAffinity
configure_systemd_affinity() {
    log_info "Configuring systemd CPUAffinity..."
    
    local host_cpus=$(printf '%s ' "${HOST_CPUS[@]}")
    host_cpus=${host_cpus% }  # Remove trailing space
    
    local systemd_conf="/etc/systemd/system.conf"
    cp "$systemd_conf" "${systemd_conf}${BACKUP_SUFFIX}"
    
    # Handle both commented and uncommented CPUAffinity lines
    if grep -q "^CPUAffinity=" "$systemd_conf"; then
        # Already uncommented, just update value
        sed -i "s/^CPUAffinity=.*/CPUAffinity=$host_cpus/" "$systemd_conf"
    elif grep -q "^#CPUAffinity=" "$systemd_conf"; then
        # Commented out, uncomment and set value
        sed -i "s/^#CPUAffinity=.*/CPUAffinity=$host_cpus/" "$systemd_conf"
    else
        # Doesn't exist at all, append to [Manager] section
        sed -i '/^\[Manager\]/a CPUAffinity='"$host_cpus" "$systemd_conf"
    fi
    
    log_success "systemd CPUAffinity configured: $host_cpus"
    
    # Reload systemd daemon immediately
    log_info "Reloading systemd daemon..."
    systemctl daemon-reexec
    log_success "systemd daemon reloaded"
    
    # Move all existing processes to host cores immediately
    log_info "Moving all processes to host cores..."
    local moved=0
    local failed=0
    
    for pid in $(ps -eo pid --no-headers); do
        if taskset -cp "$host_cpus" "$pid" &>/dev/null; then
            moved=$((moved + 1))
        else
            failed=$((failed + 1))
        fi
    done
    
    log_success "Moved $moved processes to host cores (${failed} failed - expected for kernel threads)"
    log_info "CPU affinity is now active - check with 'htop' to verify"
}

# Create libvirt hooks for VM CPU pinning
create_libvirt_hooks() {
    log_info "Creating libvirt hooks for automatic VM CPU pinning..."
    
    local hook_dir="/etc/libvirt/hooks"
    mkdir -p "$hook_dir"
    
    # Create qemu hook
    cat > "$hook_dir/qemu" << 'EOFHOOK'
#!/bin/bash
# Libvirt hook for CPU affinity management
# Auto-pins VMs to isolated CPUs

GUEST_NAME="$1"
HOOK_NAME="$2"
STATE_NAME="$3"
MISC="${@:4}"

ISOLATED_CPUS="ISOLATED_CPUS_PLACEHOLDER"
HOST_CPUS="HOST_CPUS_PLACEHOLDER"

case "$STATE_NAME" in
    prepare/begin)
        # Move host processes to host CPUs before VM starts
        echo "Moving host processes to CPUs: $HOST_CPUS"
        for pid in $(ps -eo pid=); do
            taskset -cp $HOST_CPUS $pid 2>/dev/null || true
        done
        ;;
        
    release/end)
        # Restore CPU affinity after VM stops
        echo "VM $GUEST_NAME stopped - restoring CPU affinity"
        ;;
esac

exit 0
EOFHOOK
    
    # Replace placeholders
    local isolated_range=$(printf '%s,' "${ISOLATED_CPUS[@]}")
    isolated_range=${isolated_range%,}
    local host_range=$(printf '%s,' "${HOST_CPUS[@]}")
    host_range=${host_range%,}
    
    sed -i "s/ISOLATED_CPUS_PLACEHOLDER/$isolated_range/" "$hook_dir/qemu"
    sed -i "s/HOST_CPUS_PLACEHOLDER/$host_range/" "$hook_dir/qemu"
    
    chmod +x "$hook_dir/qemu"
    
    log_success "Libvirt hooks created"
}

# Create helper scripts
create_helper_scripts() {
    log_info "Creating helper scripts..."
    
    # CPU topology viewer
    cat > /usr/local/bin/cpu-topology << 'EOFSCRIPT'
#!/bin/bash
echo "CPU Topology:"
lscpu --extended
echo ""
echo "NUMA Nodes:"
numactl --hardware
echo ""
echo "Current CPU Affinity:"
taskset -cp $$
EOFSCRIPT
    
    chmod +x /usr/local/bin/cpu-topology
    log_success "Created: cpu-topology"
    
    # Dynamic affinity switcher
    local isolated_range=$(printf '%s,' "${ISOLATED_CPUS[@]}")
    isolated_range=${isolated_range%,}
    local host_range=$(printf '%s,' "${HOST_CPUS[@]}")
    host_range=${host_range%,}
    
    cat > /usr/local/bin/cpu-isolate << EOFSCRIPT
#!/bin/bash
# Dynamic CPU isolation toggle

ISOLATED_CPUS="$isolated_range"
HOST_CPUS="$host_range"

case "\$1" in
    on)
        echo "Enabling CPU isolation. Isolated: \$ISOLATED_CPUS  Host: \$HOST_CPUS"
        echo "Moving all processes to host cores..."
        
        moved=0
        failed=0
        total=\$(ps -eo pid --no-headers | wc -l)
        
        for pid in \$(ps -eo pid --no-headers); do
            if taskset -cp \$HOST_CPUS \$pid 2>/dev/null; then
                moved=$((moved + 1))
            else
                failed=$((failed + 1))
            fi
            
            # Show progress every 100 processes
            if (( (moved + failed) % 100 == 0 )); then
                echo -ne "\rProgress: \$((moved + failed))/\$total processes processed..."
            fi
        done
        
        echo -e "\rProgress: \$((moved + failed))/\$total processes processed... Done!"
        echo ""
        echo "âœ" Successfully moved \$moved processes to host cores"
        echo "  (Failed: \$failed - expected for kernel threads)"
        echo ""
        echo "Isolation active. Check with 'htop' to verify."
        ;;
    off)
        echo "Disabling CPU isolation -- allowing all processes to use all CPUs..."
        
        all_cpus="0-\$(($(nproc) - 1))"
        moved=0
        failed=0
        
        for pid in \$(ps -eo pid --no-headers); do
            if taskset -cp \$all_cpus \$pid 2>/dev/null; then
                moved=$((moved + 1))
            else
                failed=$((failed + 1))
            fi
        done
        
        echo "âœ" Restored access to all CPUs for \$moved processes"
        echo "  (Failed: \$failed - expected for kernel threads)"
        ;;
    status)
        echo "CPU isolation status -- Isolated: \$ISOLATED_CPUS  Host: \$HOST_CPUS"
        echo ""
        echo "Kernel parameters:"
        cat /proc/cmdline | grep -o "isolcpus=[^ ]*" || echo "  No isolcpus parameter"
        echo ""
        echo "systemd CPUAffinity:"
        grep "^CPUAffinity=" /etc/systemd/system.conf 2>/dev/null || echo "  Not configured"
        echo ""
        echo "Current shell affinity (PID \$\$):"
        taskset -cp \$\$
        echo ""
        echo "Sample of running processes:"
        ps -eo pid,psr,comm | head -20
        ;;
    *)
        echo "Usage: cpu-isolate {on|off|status}"
        echo ""
        echo "  on     - Move all processes to host cores (enable isolation)"
        echo "  off    - Allow all processes to use all CPUs (disable isolation)"
        echo "  status - Show current isolation configuration"
        exit 1
        ;;
esac
EOFSCRIPT
    
    chmod +x /usr/local/bin/cpu-isolate
    log_success "Created: cpu-isolate"
    
    # Verification script
    cat > /usr/local/bin/cpu-verify << EOFSCRIPT
#!/bin/bash
echo "CPU Isolation Verification"
echo "Kernel Parameters:"
cat /proc/cmdline | grep -o "isolcpus=[^ ]*\|nohz_full=[^ ]*\|rcu_nocbs=[^ ]*"
echo ""
echo "Isolated CPUs: $isolated_range"
echo "Host CPUs: $host_range"
echo ""
echo "systemd CPUAffinity:"
grep "^CPUAffinity=" /etc/systemd/system.conf 2>/dev/null || echo "  Not configured"
echo ""
echo "Current process affinity:"
taskset -cp 1
EOFSCRIPT
    
    chmod +x /usr/local/bin/cpu-verify
    log_success "Created: cpu-verify"
}

# Generate summary
generate_summary() {
    log_header "Configuration Summary"
    
    echo -e "${BOLD}CPU Isolation Configuration:${NC}"
    echo ""
    echo -e "${GREEN}Isolated CPUs (for VMs):${NC}"
    echo "  CPUs: ${ISOLATED_CPUS[*]}"
    echo "  Count: ${#ISOLATED_CPUS[@]} threads"
    echo ""
    echo -e "${YELLOW}Host CPUs (for system):${NC}"
    echo "  CPUs: ${HOST_CPUS[*]}"
    echo "  Count: ${#HOST_CPUS[@]} threads"
    echo ""
    
    if [[ -n "${CPU_INFO[has_ccds]}" ]]; then
        echo -e "${BOLD}CCD Assignment:${NC}"
        echo "  CCD0 (V-Cache): ${CCD_MAP[0]}"
        echo "  CCD1 (High Freq): ${CCD_MAP[1]}"
        echo ""
    fi
    
    echo -e "${BOLD}Configuration Files:${NC}"
    echo "  Bootloader: Updated (backed up)"
    echo "  systemd: /etc/systemd/system.conf"
    echo "  Libvirt hooks: /etc/libvirt/hooks/qemu"
    echo ""
    
    echo -e "${BOLD}Helper Commands:${NC}"
    echo "  cpu-topology  - View CPU layout and NUMA"
    echo "  cpu-isolate   - Toggle isolation dynamically"
    echo "  cpu-verify    - Verify configuration"
    echo ""
    
    # Check if systemd affinity was configured
    if grep -q "^CPUAffinity=" /etc/systemd/system.conf 2>/dev/null; then
        echo -e "${GREEN}âœ" systemd CPUAffinity is active (processes already moved)${NC}"
        echo "  You can verify with: htop (press 't' for tree view)"
        echo "  Host cores should show activity, VM cores should be idle"
        echo ""
    fi
    
    echo -e "${BOLD}Next Steps:${NC}"
    if grep -q "^CPUAffinity=" /etc/systemd/system.conf 2>/dev/null; then
        echo "  1. ${GREEN}Verify with htop${NC} - host cores should be active"
        echo "  2. Reboot system (for kernel isolcpus to take full effect)"
        echo "  3. Run 'cpu-verify' after reboot to confirm"
        echo "  4. Configure VMs with CPU pinning in virt-manager"
    else
        echo "  1. Reboot system (for isolcpus to take effect)"
        echo "  2. Run 'cpu-verify' to confirm configuration"
        echo "  3. Configure VMs with CPU pinning in virt-manager"
        echo "  4. Use 'cpu-isolate on' before starting VMs"
    fi
    echo ""
    
    echo -e "${BOLD}VM CPU Pinning Example (libvirt XML):${NC}"
    echo "  <vcpu placement='static'>${#ISOLATED_CPUS[@]}</vcpu>"
    echo "  <cputune>"
    local cpu_index=0
    for cpu in "${ISOLATED_CPUS[@]}"; do
        echo "    <vcpupin vcpu='$cpu_index' cpuset='$cpu'/>"
        cpu_index=$((cpu_index + 1))
        [[ $cpu_index -ge 4 ]] && break  # Show only first 4 as example
    done
    [[ ${#ISOLATED_CPUS[@]} -gt 4 ]] && echo "    <!-- ... additional pins ... -->"
    echo "  </cputune>"
    echo ""
}

# Main execution
main() {
    log_header "Universal CPU Core Isolation Configurator"
    
    check_root
    detect_cpu_topology
    display_cpu_topology
    select_isolation_mode
    review_selection
    configure_isolation
    generate_summary
    
    echo -e "${YELLOW}â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*â*${NC}"
    read -p "Reboot now to apply kernel changes? [y/N]: " reboot_now
    
    if [[ "$reboot_now" =~ ^[Yy]$ ]]; then
        log_info "Rebooting system..."
        systemctl reboot
    else
        log_warning "Remember to reboot for isolcpus changes to take effect!"
        echo ""
        echo "After reboot, run: cpu-verify"
    fi
}

main "$@"

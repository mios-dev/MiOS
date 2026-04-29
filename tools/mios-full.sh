#!/bin/bash
###############################################################################
#
#   â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ•—      â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•— â–ˆâ–ˆâ•—   â–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—       â–ˆâ–ˆâ•—    â–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—
#  â–ˆâ–ˆâ•”â•â•â•â•â•â–ˆâ–ˆâ•‘     â–ˆâ–ˆâ•”â•â•â•â–ˆâ–ˆâ•—â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•—      â–ˆâ–ˆâ•‘    â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â•â•â•
#  â–ˆâ–ˆâ•‘     â–ˆâ–ˆâ•‘     â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘  â–ˆâ–ˆâ•‘â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ•‘ â–ˆâ•— â–ˆâ–ˆâ•‘â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—
#  â–ˆâ–ˆâ•‘     â–ˆâ–ˆâ•‘     â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘  â–ˆâ–ˆâ•‘â•šâ•â•â•â•â•â–ˆâ–ˆâ•‘â–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ•‘â•šâ•â•â•â•â–ˆâ–ˆâ•‘
#  â•šâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â•šâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â•â•šâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â•â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â•      â•šâ–ˆâ–ˆâ–ˆâ•”â–ˆâ–ˆâ–ˆâ•”â•â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•‘
#   â•šâ•â•â•â•â•â•â•šâ•â•â•â•â•â•â• â•šâ•â•â•â•â•â•  â•šâ•â•â•â•â•â• â•šâ•â•â•â•â•â•        â•šâ•â•â•â•šâ•â•â• â•šâ•â•â•â•â•â•â•
#
#  MiOS-Build Unified Management System
#  Version: v0.1.1 - Complete Integrated Edition
#
#  A single comprehensive tool for:
#    â€¢ Pre-installation system assessment
#    â€¢ Full MiOS-Build installation (15 phases)
#    â€¢ VFIO GPU passthrough configuration
#    â€¢ CPU core isolation & optimization
#    â€¢ VM CPU pinning & hook management
#    â€¢ System verification & health checks
#    â€¢ Troubleshooting & diagnostics
#    â€¢ Log management & reporting
#
#  Target: CachyOS / Arch Linux based systems
#  Hardware: AMD Ryzen (X3D optimized), Intel, NVIDIA/AMD GPUs
#
#  Usage:
#    sudo ./mios-full.sh                    # Interactive menu
#    sudo ./mios-full.sh [mode] [options]   # Direct mode
#
#  Modes:
#    assess, install, configure, verify, diagnose, status, logs, help
#
###############################################################################

set -o pipefail

#==============================================================================
# VERSION & GLOBAL CONFIGURATION
#==============================================================================
readonly MIOS_VERSION="v0.1.1"
readonly MIOS_NAME="MiOS-Build Unified Management System"
readonly MIOS_CODENAME="Integrated Edition"

# Directory structure
readonly MIOS_BASE="/var/lib/mios"
readonly MIOS_LOG_DIR="/var/log/mios"
readonly MIOS_STATE_FILE="$MIOS_BASE/state.json"
readonly MIOS_CONFIG_DIR="$MIOS_BASE/config"
readonly MIOS_BACKUP_DIR="$MIOS_BASE/backups"

# Session identifiers
readonly SESSION_ID="$(date +%Y%m%d-%H%M%S)-$$"
readonly TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
readonly BACKUP_SUFFIX=".backup-$TIMESTAMP"

# Detect real user (even under sudo)
if [[ -n "${SUDO_USER:-}" ]]; then
    REAL_USER="$SUDO_USER"
    REAL_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    REAL_UID=$(id -u "$SUDO_USER")
    REAL_GID=$(id -g "$SUDO_USER")
else
    REAL_USER="${USER:-$(whoami)}"
    REAL_HOME="${HOME:-$(eval echo ~$REAL_USER)}"
    REAL_UID=$(id -u)
    REAL_GID=$(id -g)
fi

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Installation settings
MAX_RETRY=3
INSTALL_TIMEOUT=300

# Package lists (for installation)
readonly PKGS_VIRTUALIZATION=(
    qemu-full libvirt virt-manager virt-install virt-viewer
    dnsmasq openbsd-netcat dmidecode bridge-utils
    edk2-ovmf swtpm libtpms
)

readonly PKGS_COCKPIT=(
    cockpit cockpit-machines cockpit-podman
    cockpit-storaged cockpit-packagekit cockpit-files
)

readonly PKGS_CONTAINERS=(
    podman podman-compose buildah passt
)

readonly PKGS_NETWORK=(
    firewalld nftables iptables-nft
    samba wsdd avahi nss-mdns
)

readonly PKGS_DESKTOP=(
    gdm gnome-shell gnome-console gnome-control-center
    gnome-tweaks gnome-backgrounds nautilus file-roller
    xdg-desktop-portal-gnome gcr
)

readonly PKGS_UTILITIES=(
    git base-devel flatpak p7zip wget curl
    htop btop tuned tpm2-tools sbctl kexec-tools
    pcp lm_sensors
)

#==============================================================================
# COLOR THEME - MiOS-Build Professional (Teal/Coral/White)
#==============================================================================
# Primary palette
readonly TEAL='\033[38;5;43m'
readonly TEAL_LIGHT='\033[38;5;80m'
readonly TEAL_DARK='\033[38;5;30m'
readonly CORAL='\033[38;5;210m'
readonly WHITE='\033[1;37m'
readonly GRAY='\033[38;5;245m'
readonly DARK_GRAY='\033[38;5;240m'
readonly SUCCESS='\033[38;5;48m'
readonly WARNING='\033[38;5;214m'

# Text styling
readonly BOLD='\033[1m'
readonly DIM='\033[2m'
readonly ITALIC='\033[3m'
readonly UNDERLINE='\033[4m'
readonly BLINK='\033[5m'
readonly REVERSE='\033[7m'
readonly NC='\033[0m'

# Semantic color aliases
readonly C_HEADER="$TEAL"
readonly C_SUBHEADER="$TEAL_LIGHT"
readonly C_MENU="$TEAL_LIGHT"
readonly C_SUCCESS="$SUCCESS"
readonly C_WARNING="$WARNING"
readonly C_ERROR="$CORAL"
readonly C_INFO="$TEAL_LIGHT"
readonly C_MUTED="$GRAY"
readonly C_HIGHLIGHT="$WHITE"
readonly C_ACCENT="$CORAL"

# GPU vendor colors (for VFIO display)
readonly C_NVIDIA="$SUCCESS"
readonly C_AMD="$CORAL"
readonly C_INTEL="$TEAL_LIGHT"

#==============================================================================
# GLOBAL STATE VARIABLES
#==============================================================================
# Persistent state (saved to disk)
declare -A STATE=(
    [install_phase]="not_started"
    [install_mode]=""
    [install_timestamp]=""
    [assessment_done]="false"
    [vfio_configured]="false"
    [cpu_isolated]="false"
    [vm_hooks_configured]="false"
    [looking_glass_installed]="false"
    [last_session]=""
    [reboot_required]="false"
)

# Session state (runtime only)
declare -A SESSION=(
    [root_checked]="false"
    [network_checked]="false"
    [system_detected]="false"
)

# Hardware detection results
declare -A SYSTEM_INFO
declare -A CPU_INFO
declare -A GPU_INFO
declare -A NUMA_MAP
declare -a CCD_MAP=()
declare -a IOMMU_GROUPS=()

# Task tracking
declare -a SUCCESS_TASKS=()
declare -a FAILED_TASKS=()
declare -a SKIPPED_TASKS=()
declare -a WARNING_TASKS=()

# VFIO configuration
declare -a VFIO_SELECTED_DEVICES=()
declare -a VFIO_SELECTED_IDS=()
declare -a VFIO_SELECTED_DRIVERS=()

# CPU isolation configuration
declare -a ISOLATED_CPUS=()
declare -a HOST_CPUS=()

#==============================================================================
# LOGGING SYSTEM
#==============================================================================
LOG_FILE=""
DEBUG_LOG=""
REPORT_FILE=""

init_logging() {
    mkdir -p "$MIOS_LOG_DIR" 2>/dev/null || true
    mkdir -p "$MIOS_BASE" 2>/dev/null || true
    mkdir -p "$MIOS_CONFIG_DIR" 2>/dev/null || true
    mkdir -p "$MIOS_BACKUP_DIR" 2>/dev/null || true
    
    LOG_FILE="$MIOS_LOG_DIR/session-$SESSION_ID.log"
    DEBUG_LOG="$MIOS_LOG_DIR/debug-$SESSION_ID.log"
    REPORT_FILE="$MIOS_LOG_DIR/report-$SESSION_ID.txt"
    
    # Set ownership for user access
    if [[ $EUID -eq 0 && -n "${SUDO_USER:-}" ]]; then
        chown -R "$REAL_USER:$(id -gn "$REAL_USER")" "$MIOS_LOG_DIR" 2>/dev/null || true
        chown -R "$REAL_USER:$(id -gn "$REAL_USER")" "$MIOS_BASE" 2>/dev/null || true
    fi
    
    # Initialize log files
    {
        echo "================================================================================"
        echo " MiOS-Build Unified Management System - Session Log"
        echo " Version: $MIOS_VERSION"
        echo " Session: $SESSION_ID"
        echo " Started: $(date)"
        echo " User: $REAL_USER (UID: $REAL_UID)"
        echo " Hostname: $(hostname)"
        echo "================================================================================"
        echo ""
    } > "$LOG_FILE"
    
    {
        echo "=== Debug Log: $SESSION_ID ==="
        echo "Started: $(date)"
        echo ""
    } > "$DEBUG_LOG"
}

# Log to file with timestamp
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

log_debug() {
    local timestamp=$(date '+%H:%M:%S.%3N')
    echo "[$timestamp] $*" >> "$DEBUG_LOG"
}

# Log command execution
log_cmd() {
    local cmd="$1"
    log_debug "EXEC: $cmd"
    eval "$cmd" >> "$DEBUG_LOG" 2>&1
    local exit_code=$?
    log_debug "EXIT: $exit_code"
    return $exit_code
}

#==============================================================================
# STATE PERSISTENCE
#==============================================================================
load_state() {
    if [[ -f "$MIOS_STATE_FILE" ]]; then
        # Simple JSON parsing for bash
        while IFS=':' read -r key value; do
            key=$(echo "$key" | tr -d ' "')
            value=$(echo "$value" | tr -d ' ",' | sed 's/}$//')
            if [[ -n "$key" && -n "$value" && "$key" != "{" && "$key" != "}" ]]; then
                STATE["$key"]="$value"
            fi
        done < "$MIOS_STATE_FILE"
        log "INFO" "Loaded state from $MIOS_STATE_FILE"
    fi
}

save_state() {
    mkdir -p "$(dirname "$MIOS_STATE_FILE")" 2>/dev/null
    
    cat > "$MIOS_STATE_FILE" << EOF
{
    "version": "$MIOS_VERSION",
    "last_updated": "$(date -Iseconds)",
    "session_id": "$SESSION_ID",
    "install_phase": "${STATE[install_phase]}",
    "install_mode": "${STATE[install_mode]}",
    "install_timestamp": "${STATE[install_timestamp]}",
    "assessment_done": "${STATE[assessment_done]}",
    "vfio_configured": "${STATE[vfio_configured]}",
    "cpu_isolated": "${STATE[cpu_isolated]}",
    "vm_hooks_configured": "${STATE[vm_hooks_configured]}",
    "looking_glass_installed": "${STATE[looking_glass_installed]}",
    "last_session": "$SESSION_ID",
    "reboot_required": "${STATE[reboot_required]}"
}
EOF
    
    # Set ownership
    if [[ $EUID -eq 0 && -n "${SUDO_USER:-}" ]]; then
        chown "$REAL_USER:$(id -gn "$REAL_USER")" "$MIOS_STATE_FILE" 2>/dev/null || true
    fi
    
    log "INFO" "Saved state to $MIOS_STATE_FILE"
}

#==============================================================================
# UI COMPONENTS - BANNERS & HEADERS
#==============================================================================
print_banner() {
    clear
    echo -e "${C_HEADER}"
    cat << 'BANNER'
    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
    â•‘                                                                           â•‘
    â•‘     â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ•—      â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•— â–ˆâ–ˆâ•—   â–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—       â–ˆâ–ˆâ•—    â–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—     â•‘
    â•‘    â–ˆâ–ˆâ•”â•â•â•â•â•â–ˆâ–ˆâ•‘     â–ˆâ–ˆâ•”â•â•â•â–ˆâ–ˆâ•—â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•—      â–ˆâ–ˆâ•‘    â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â•â•â•     â•‘
    â•‘    â–ˆâ–ˆâ•‘     â–ˆâ–ˆâ•‘     â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘  â–ˆâ–ˆâ•‘â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ•‘ â–ˆâ•— â–ˆâ–ˆâ•‘â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—     â•‘
    â•‘    â–ˆâ–ˆâ•‘     â–ˆâ–ˆâ•‘     â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘  â–ˆâ–ˆâ•‘â•šâ•â•â•â•â•â–ˆâ–ˆâ•‘â–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ•‘â•šâ•â•â•â•â–ˆâ–ˆâ•‘     â•‘
    â•‘    â•šâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â•šâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â•â•šâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â•â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â•      â•šâ–ˆâ–ˆâ–ˆâ•”â–ˆâ–ˆâ–ˆâ•”â•â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•‘     â•‘
    â•‘     â•šâ•â•â•â•â•â•â•šâ•â•â•â•â•â•â• â•šâ•â•â•â•â•â•  â•šâ•â•â•â•â•â• â•šâ•â•â•â•â•â•        â•šâ•â•â•â•šâ•â•â• â•šâ•â•â•â•â•â•â•     â•‘
    â•‘                                                                           â•‘
BANNER
    echo -e "    â•‘           ${WHITE}Unified Management System${C_HEADER}  v${MIOS_VERSION}                            â•‘"
    echo -e "    â•‘           ${GRAY}Professional Virtualization Platform${C_HEADER}                          â•‘"
    echo -e "    â•‘                                                                           â•‘"
    echo -e "    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    echo ""
}

print_small_banner() {
    local title="${1:-MiOS-Build}"
    echo ""
    echo -e "${C_HEADER}    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”${NC}"
    echo -e "${C_HEADER}    â”‚${NC}  ${WHITE}MiOS-Build${NC}  â”‚  ${C_SUBHEADER}$title${NC}"
    echo -e "${C_HEADER}    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜${NC}"
    echo ""
}

print_section() {
    local title="$1"
    echo ""
    echo -e "${C_HEADER}    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”${NC}"
    echo -e "${C_HEADER}    â”‚${NC}  ${WHITE}$title${NC}"
    echo -e "${C_HEADER}    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜${NC}"
}

print_subsection() {
    local title="$1"
    echo ""
    echo -e "    ${C_SUBHEADER}â–¸ $title${NC}"
    echo -e "    ${C_MUTED}â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€${NC}"
}

print_phase() {
    local phase_num="$1"
    local phase_name="$2"
    echo ""
    echo -e "${C_HEADER}    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”${NC}"
    echo -e "${C_HEADER}    â”‚${NC}  ${C_ACCENT}PHASE $phase_num:${NC} ${WHITE}$phase_name${NC}"
    echo -e "${C_HEADER}    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜${NC}"
}

#==============================================================================
# UI COMPONENTS - STATUS MESSAGES
#==============================================================================
msg_success() {
    local msg="$1"
    echo -e "      ${C_SUCCESS}âœ”${NC} $msg"
    SUCCESS_TASKS+=("$msg")
    log "OK" "$msg"
}

msg_fail() {
    local msg="$1"
    echo -e "      ${C_ERROR}âœ–${NC} $msg"
    FAILED_TASKS+=("$msg")
    log "FAIL" "$msg"
}

msg_skip() {
    local msg="$1"
    local reason="${2:-skipped}"
    echo -e "      ${C_MUTED}â—¦${NC} $msg ${C_MUTED}($reason)${NC}"
    SKIPPED_TASKS+=("$msg: $reason")
    log "SKIP" "$msg: $reason"
}

msg_warn() {
    local msg="$1"
    echo -e "      ${C_WARNING}âš ${NC} $msg"
    WARNING_TASKS+=("$msg")
    log "WARN" "$msg"
}

msg_info() {
    local msg="$1"
    echo -e "      ${C_INFO}â–¸${NC} $msg"
    log "INFO" "$msg"
}

msg_wait() {
    local msg="$1"
    echo -e "      ${C_MUTED}â³${NC} $msg"
}

msg_debug() {
    local msg="$1"
    echo -e "      ${C_MUTED}[DEBUG]${NC} $msg"
    log_debug "$msg"
}

#==============================================================================
# UI COMPONENTS - PROGRESS & SPINNERS
#==============================================================================
show_progress() {
    local current=$1
    local total=$2
    local label="${3:-Progress}"
    local width=50
    local percent=$((current * 100 / total))
    local filled=$((current * width / total))
    local empty=$((width - filled))
    
    printf "\r      ${C_INFO}%s:${NC} [" "$label"
    printf "%${filled}s" | tr ' ' 'â–ˆ'
    printf "%${empty}s" | tr ' ' 'â–‘'
    printf "] %3d%%" "$percent"
    
    [[ $current -eq $total ]] && echo ""
}

spinner() {
    local pid=$1
    local message="${2:-Working...}"
    local spin='â ‹â ™â ¹â ¸â ¼â ´â ¦â §â ‡â '
    local i=0
    
    while kill -0 $pid 2>/dev/null; do
        printf "\r      ${C_INFO}%s${NC} %s" "${spin:i%${#spin}:1}" "$message"
        i=$((i + 1))
        sleep 0.1
    done
    printf "\r      ${C_SUCCESS}âœ”${NC} %s\n" "$message"
}

#==============================================================================
# UI COMPONENTS - PROMPTS
#==============================================================================
ask_yes_no() {
    local prompt="$1"
    local default="${2:-n}"
    local response
    
    if [[ "$default" == "y" ]]; then
        read -rp $'      \033[38;5;80m?\033[0m '"$prompt"$' [\033[1;37mY\033[0m/n]: ' response
        [[ -z "$response" || "$response" =~ ^[Yy] ]]
    else
        read -rp $'      \033[38;5;80m?\033[0m '"$prompt"$' [y/\033[1;37mN\033[0m]: ' response
        [[ "$response" =~ ^[Yy] ]]
    fi
}

ask_choice() {
    local prompt="$1"
    shift
    local options=("$@")
    local choice
    
    echo -e "      ${C_INFO}?${NC} $prompt"
    echo ""
    for i in "${!options[@]}"; do
        echo -e "        ${C_HIGHLIGHT}$((i+1)))${NC} ${options[$i]}"
    done
    echo ""
    
    while true; do
        read -rp "      Enter choice [1-${#options[@]}]: " choice
        if [[ "$choice" =~ ^[0-9]+$ ]] && ((choice >= 1 && choice <= ${#options[@]})); then
            return $((choice - 1))
        fi
        echo -e "      ${C_WARNING}Invalid choice. Please enter 1-${#options[@]}${NC}"
    done
}

ask_input() {
    local prompt="$1"
    local default="${2:-}"
    local response
    
    if [[ -n "$default" ]]; then
        read -rp $'      \033[38;5;80m?\033[0m '"$prompt"$' [\033[38;5;245m'"$default"$'\033[0m]: ' response
        echo "${response:-$default}"
    else
        read -rp $'      \033[38;5;80m?\033[0m '"$prompt"$': ' response
        echo "$response"
    fi
}

press_enter() {
    echo ""
    read -rp "      Press Enter to continue..."
}

confirm_action() {
    local action="$1"
    local warning="${2:-}"
    
    echo ""
    if [[ -n "$warning" ]]; then
        msg_warn "$warning"
    fi
    
    if ! ask_yes_no "Proceed with: $action?"; then
        msg_info "Action cancelled"
        return 1
    fi
    return 0
}

#==============================================================================
# PREREQUISITE CHECKS
#==============================================================================
check_root() {
    if [[ "${SESSION[root_checked]}" == "true" ]]; then
        return 0
    fi
    
    if [[ $EUID -ne 0 ]]; then
        echo -e "${C_ERROR}Error: This operation requires root privileges${NC}"
        echo -e "Usage: ${C_HIGHLIGHT}sudo $0${NC}"
        return 1
    fi
    
    if [[ "$REAL_USER" == "root" ]]; then
        echo -e "${C_ERROR}Error: Run with sudo, not as root directly${NC}"
        echo -e "Usage: ${C_HIGHLIGHT}sudo $0${NC} (from regular user)"
        return 1
    fi
    
    SESSION[root_checked]="true"
    return 0
}

check_network() {
    if [[ "${SESSION[network_checked]}" == "true" ]]; then
        return 0
    fi
    
    msg_info "Checking network connectivity..."
    
    if getent hosts archlinux.org &>/dev/null || \
       getent hosts Project-Target.com &>/dev/null || \
       ping -c1 -W3 1.1.1.1 &>/dev/null; then
        msg_success "Network: DNS and connectivity OK"
        SESSION[network_checked]="true"
        return 0
    fi
    
    msg_fail "Network: DNS resolution failed"
    echo ""
    echo -e "    ${C_HEADER}â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”${NC}"
    echo -e "    ${C_HEADER}â”‚${NC}  ${C_ERROR}DNS RESOLUTION FAILED${NC}"
    echo -e "    ${C_HEADER}â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤${NC}"
    echo -e "    ${C_HEADER}â”‚${NC}"
    echo -e "    ${C_HEADER}â”‚${NC}  ${WHITE}Fix DNS before running installation:${NC}"
    echo -e "    ${C_HEADER}â”‚${NC}"
    echo -e "    ${C_HEADER}â”‚${NC}  ${C_MUTED}sudo bash -c 'echo \"nameserver 1.1.1.1\" > /etc/resolv.conf'${NC}"
    echo -e "    ${C_HEADER}â”‚${NC}  ${C_MUTED}sudo bash -c 'echo \"nameserver 8.8.8.8\" >> /etc/resolv.conf'${NC}"
    echo -e "    ${C_HEADER}â”‚${NC}"
    echo -e "    ${C_HEADER}â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜${NC}"
    echo ""
    return 1
}

check_distribution() {
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        SYSTEM_INFO[distro_id]="${ID:-unknown}"
        SYSTEM_INFO[distro_name]="${NAME:-Unknown}"
        SYSTEM_INFO[distro_version]="${VERSION_ID:-}"
        
        # Check for Arch-based
        if [[ "${ID:-}" == "cachyos" ]] || \
           [[ "${ID:-}" == "arch" ]] || \
           [[ "${ID_LIKE:-}" == *"arch"* ]]; then
            SYSTEM_INFO[is_arch_based]="true"
            return 0
        fi
    fi
    
    SYSTEM_INFO[is_arch_based]="false"
    msg_warn "This system may not be fully compatible (Arch-based recommended)"
    return 0
}

#==============================================================================
# PACKAGE MANAGEMENT
#==============================================================================
install_packages() {
    local description="$1"
    shift
    local packages=("$@")
    local attempt=1
    
    while [[ $attempt -le $MAX_RETRY ]]; do
        if pacman -S --noconfirm --needed "${packages[@]}" >> "$DEBUG_LOG" 2>&1; then
            msg_success "$description"
            return 0
        fi
        
        if [[ $attempt -lt $MAX_RETRY ]]; then
            echo -e "        ${C_MUTED}â†» Retry $attempt/$MAX_RETRY...${NC}"
            sleep 2
        fi
        attempt=$((attempt + 1))
    done
    
    msg_fail "$description"
    return 1
}

install_aur() {
    local package="$1"
    
    if ! command -v yay &>/dev/null; then
        msg_skip "$package" "yay not available"
        return 1
    fi
    
    if pacman -Qs "^${package}$" &>/dev/null; then
        msg_skip "$package" "already installed"
        return 0
    fi
    
    local attempt=1
    while [[ $attempt -le $MAX_RETRY ]]; do
        if sudo -u "$REAL_USER" yay -S --noconfirm --needed \
           --answerdiff=None --answerclean=None "$package" >> "$DEBUG_LOG" 2>&1; then
            msg_success "$package (AUR)"
            return 0
        fi
        
        if [[ $attempt -lt $MAX_RETRY ]]; then
            echo -e "        ${C_MUTED}â†» Retry $attempt/$MAX_RETRY...${NC}"
            sleep 2
        fi
        attempt=$((attempt + 1))
    done
    
    msg_fail "$package (AUR)"
    return 1
}

sync_package_db() {
    msg_info "Synchronizing package databases..."
    if pacman -Sy --noconfirm >> "$DEBUG_LOG" 2>&1; then
        msg_success "Package database synchronized"
        return 0
    else
        msg_fail "Package database sync failed"
        return 1
    fi
}

install_yay() {
    if command -v yay &>/dev/null; then
        msg_skip "yay" "already installed"
        return 0
    fi
    
    msg_info "Installing yay AUR helper..."
    
    local build_dir="/tmp/yay-build-$$"
    mkdir -p "$build_dir"
    cd "$build_dir"
    
    if sudo -u "$REAL_USER" git clone https://aur.archlinux.org/yay-bin.git >> "$DEBUG_LOG" 2>&1; then
        cd yay-bin
        if sudo -u "$REAL_USER" makepkg -si --noconfirm >> "$DEBUG_LOG" 2>&1; then
            msg_success "yay AUR helper"
            cd /
            rm -rf "$build_dir"
            return 0
        fi
    fi
    
    msg_fail "yay installation"
    cd /
    rm -rf "$build_dir" 2>/dev/null
    return 1
}

#==============================================================================
# SYSTEM DETECTION - COMPREHENSIVE HARDWARE ANALYSIS
#==============================================================================
detect_system() {
    if [[ "${SESSION[system_detected]}" == "true" ]]; then
        return 0
    fi
    
    msg_info "Detecting system configuration..."
    
    detect_cpu
    detect_memory
    detect_gpu
    detect_iommu
    detect_virtualization
    detect_storage
    detect_bootloader
    detect_initramfs
    detect_tpm
    detect_secureboot
    detect_distribution
    
    SESSION[system_detected]="true"
    log "INFO" "System detection complete"
}

detect_cpu() {
    # Basic CPU info from lscpu
    CPU_INFO[vendor]=$(lscpu 2>/dev/null | grep "Vendor ID" | awk '{print $3}')
    CPU_INFO[model]=$(lscpu 2>/dev/null | grep "Model name" | sed 's/Model name:[[:space:]]*//')
    CPU_INFO[cores]=$(lscpu 2>/dev/null | grep "^Core(s) per socket:" | awk '{print $4}')
    CPU_INFO[threads]=$(lscpu 2>/dev/null | grep "^CPU(s):" | head -1 | awk '{print $2}')
    CPU_INFO[sockets]=$(lscpu 2>/dev/null | grep "Socket(s):" | awk '{print $2}')
    CPU_INFO[threads_per_core]=$(lscpu 2>/dev/null | grep "Thread(s) per core:" | awk '{print $4}')
    CPU_INFO[numa_nodes]=$(lscpu 2>/dev/null | grep "NUMA node(s):" | awk '{print $3}')
    
    # CPU feature flags
    if grep -qE "(vmx|svm)" /proc/cpuinfo 2>/dev/null; then
        CPU_INFO[virt_ext]=$(grep -oE '(vmx|svm)' /proc/cpuinfo | head -1)
    else
        CPU_INFO[virt_ext]="none"
    fi
    
    # NUMA topology
    for ((node=0; node<${CPU_INFO[numa_nodes]:-1}; node+=1)); do
        local cpus=$(lscpu 2>/dev/null | grep "NUMA node${node} CPU(s):" | awk '{print $4}')
        NUMA_MAP[$node]="$cpus"
    done
    
    # AMD CCD detection (X3D processors)
    detect_amd_ccd_topology
    
    # Intel hybrid detection (P/E cores)
    detect_intel_hybrid
    
    # Store for easy access
    SYSTEM_INFO[cpu_vendor]="${CPU_INFO[vendor]}"
    SYSTEM_INFO[cpu_model]="${CPU_INFO[model]}"
    SYSTEM_INFO[cpu_cores]="${CPU_INFO[cores]}"
    SYSTEM_INFO[cpu_threads]="${CPU_INFO[threads]}"
    
    log_debug "CPU: ${CPU_INFO[model]} - ${CPU_INFO[threads]} threads"
}

detect_amd_ccd_topology() {
    if [[ "${CPU_INFO[vendor]}" != "AuthenticAMD" ]]; then
        return
    fi
    
    # Check for X3D CPUs
    if [[ "${CPU_INFO[model]}" =~ (9950X3D|7950X3D|7900X3D|5800X3D) ]]; then
        CPU_INFO[is_x3d]="true"
        
        # Determine CCD layout based on model
        if [[ "${CPU_INFO[model]}" =~ (9950X3D|7950X3D) ]]; then
            # 16 cores, 2 CCDs
            CPU_INFO[ccd_count]=2
            CPU_INFO[cores_per_ccd]=8
            
            local threads_per_ccd=$((${CPU_INFO[threads]} / 2))
            CCD_MAP[0]="0-$((threads_per_ccd - 1))"
            CCD_MAP[1]="$threads_per_ccd-$((${CPU_INFO[threads]} - 1))"
            
        elif [[ "${CPU_INFO[model]}" =~ 7900X3D ]]; then
            # 12 cores, 2 CCDs (6+6)
            CPU_INFO[ccd_count]=2
            CPU_INFO[cores_per_ccd]=6
            
            local threads_per_ccd=$((${CPU_INFO[threads]} / 2))
            CCD_MAP[0]="0-$((threads_per_ccd - 1))"
            CCD_MAP[1]="$threads_per_ccd-$((${CPU_INFO[threads]} - 1))"
            
        elif [[ "${CPU_INFO[model]}" =~ 5800X3D ]]; then
            # 8 cores, 1 CCD with V-Cache
            CPU_INFO[ccd_count]=1
            CPU_INFO[cores_per_ccd]=8
            CCD_MAP[0]="0-$((${CPU_INFO[threads]} - 1))"
        fi
        
        log_debug "AMD X3D detected: ${CPU_INFO[ccd_count]} CCDs"
    else
        CPU_INFO[is_x3d]="false"
    fi
}

detect_intel_hybrid() {
    if [[ "${CPU_INFO[vendor]}" != "GenuineIntel" ]]; then
        return
    fi
    
    # Check for hybrid architecture (12th gen+)
    # This is a simplified check - full detection would require cpuid
    if [[ "${CPU_INFO[model]}" =~ (12th|13th|14th|Core.*Ultra) ]] || \
       grep -q "E-core\|P-core" /proc/cpuinfo 2>/dev/null; then
        CPU_INFO[is_hybrid]="true"
        log_debug "Intel Hybrid architecture detected"
    else
        CPU_INFO[is_hybrid]="false"
    fi
}

detect_memory() {
    SYSTEM_INFO[ram_total]=$(free -h 2>/dev/null | awk '/^Mem:/{print $2}')
    SYSTEM_INFO[ram_available]=$(free -h 2>/dev/null | awk '/^Mem:/{print $7}')
    SYSTEM_INFO[swap_total]=$(free -h 2>/dev/null | awk '/^Swap:/{print $2}')
    
    # Get exact bytes for calculations
    SYSTEM_INFO[ram_bytes]=$(free -b 2>/dev/null | awk '/^Mem:/{print $2}')
    SYSTEM_INFO[ram_gb]=$((${SYSTEM_INFO[ram_bytes]:-0} / 1024 / 1024 / 1024))
    
    log_debug "RAM: ${SYSTEM_INFO[ram_total]}"
}

detect_gpu() {
    # Reset GPU info
    GPU_INFO[has_nvidia]="false"
    GPU_INFO[has_amd]="false"
    GPU_INFO[has_intel]="false"
    GPU_INFO[gpu_count]=0
    
    local gpu_count=0
    
    # NVIDIA detection
    if lspci 2>/dev/null | grep -qi "nvidia"; then
        GPU_INFO[has_nvidia]="true"
        GPU_INFO[nvidia_model]=$(lspci 2>/dev/null | grep -i "VGA.*nvidia\|3D.*nvidia" | head -1 | sed 's/.*: //')
        gpu_count=$((gpu_count + 1))
        
        # Check for nvidia driver
        if lsmod | grep -q "^nvidia"; then
            GPU_INFO[nvidia_driver]="nvidia"
        elif lsmod | grep -q "^nouveau"; then
            GPU_INFO[nvidia_driver]="nouveau"
        else
            GPU_INFO[nvidia_driver]="none"
        fi
    fi
    
    # AMD detection
    if lspci 2>/dev/null | grep -qiE "amd.*vga|radeon|amd.*display"; then
        GPU_INFO[has_amd]="true"
        GPU_INFO[amd_model]=$(lspci 2>/dev/null | grep -iE "VGA.*amd|VGA.*radeon|Display.*amd" | head -1 | sed 's/.*: //')
        gpu_count=$((gpu_count + 1))
        
        if lsmod | grep -q "^amdgpu"; then
            GPU_INFO[amd_driver]="amdgpu"
        elif lsmod | grep -q "^radeon"; then
            GPU_INFO[amd_driver]="radeon"
        else
            GPU_INFO[amd_driver]="none"
        fi
    fi
    
    # Intel detection (integrated or Arc)
    if lspci 2>/dev/null | grep -qiE "intel.*vga|intel.*display|intel.*graphics"; then
        GPU_INFO[has_intel]="true"
        GPU_INFO[intel_model]=$(lspci 2>/dev/null | grep -iE "VGA.*intel|Display.*intel" | head -1 | sed 's/.*: //')
        gpu_count=$((gpu_count + 1))
        
        if lsmod | grep -q "^i915"; then
            GPU_INFO[intel_driver]="i915"
        elif lsmod | grep -q "^xe"; then
            GPU_INFO[intel_driver]="xe"
        else
            GPU_INFO[intel_driver]="none"
        fi
    fi
    
    GPU_INFO[gpu_count]=$gpu_count
    
    # Copy to SYSTEM_INFO for convenience
    SYSTEM_INFO[has_nvidia]="${GPU_INFO[has_nvidia]}"
    SYSTEM_INFO[gpu_nvidia]="${GPU_INFO[nvidia_model]:-}"
    SYSTEM_INFO[gpu_count]="$gpu_count"
    
    log_debug "GPUs detected: $gpu_count"
}

detect_iommu() {
    if [[ -d /sys/kernel/iommu_groups ]] && \
       [[ $(ls /sys/kernel/iommu_groups 2>/dev/null | wc -l) -gt 0 ]]; then
        SYSTEM_INFO[iommu_enabled]="true"
        SYSTEM_INFO[iommu_groups]=$(ls /sys/kernel/iommu_groups 2>/dev/null | wc -l)
        
        # Determine IOMMU type
        if dmesg 2>/dev/null | grep -qi "AMD-Vi"; then
            SYSTEM_INFO[iommu_type]="AMD-Vi"
        elif dmesg 2>/dev/null | grep -qi "Intel.*VT-d\|DMAR"; then
            SYSTEM_INFO[iommu_type]="Intel VT-d"
        else
            SYSTEM_INFO[iommu_type]="Unknown"
        fi
        
        log_debug "IOMMU: ${SYSTEM_INFO[iommu_groups]} groups (${SYSTEM_INFO[iommu_type]})"
    else
        SYSTEM_INFO[iommu_enabled]="false"
        SYSTEM_INFO[iommu_groups]="0"
        SYSTEM_INFO[iommu_type]="Not enabled"
        log_debug "IOMMU: Not enabled"
    fi
}

detect_virtualization() {
    # KVM support
    if [[ -e /dev/kvm ]]; then
        SYSTEM_INFO[kvm_available]="true"
    else
        SYSTEM_INFO[kvm_available]="false"
    fi
    
    # Check if running in VM
    if systemd-detect-virt --quiet 2>/dev/null; then
        SYSTEM_INFO[is_vm]="true"
        SYSTEM_INFO[hypervisor]=$(systemd-detect-virt 2>/dev/null)
    else
        SYSTEM_INFO[is_vm]="false"
        SYSTEM_INFO[hypervisor]="none"
    fi
    
    # Nested virtualization
    if [[ -f /sys/module/kvm_amd/parameters/nested ]]; then
        SYSTEM_INFO[nested_virt]=$(cat /sys/module/kvm_amd/parameters/nested 2>/dev/null)
    elif [[ -f /sys/module/kvm_intel/parameters/nested ]]; then
        SYSTEM_INFO[nested_virt]=$(cat /sys/module/kvm_intel/parameters/nested 2>/dev/null)
    else
        SYSTEM_INFO[nested_virt]="unknown"
    fi
    
    log_debug "KVM: ${SYSTEM_INFO[kvm_available]}, Nested: ${SYSTEM_INFO[nested_virt]}"
}

detect_storage() {
    # Root filesystem
    SYSTEM_INFO[root_fs]=$(df -T / 2>/dev/null | awk 'NR==2{print $2}')
    SYSTEM_INFO[root_device]=$(df / 2>/dev/null | awk 'NR==2{print $1}')
    SYSTEM_INFO[root_size]=$(df -h / 2>/dev/null | awk 'NR==2{print $2}')
    SYSTEM_INFO[root_used]=$(df -h / 2>/dev/null | awk 'NR==2{print $5}')
    
    # Check for ZFS
    if command -v zfs &>/dev/null && zpool list &>/dev/null 2>&1; then
        SYSTEM_INFO[has_zfs]="true"
        SYSTEM_INFO[zfs_pools]=$(zpool list -H -o name 2>/dev/null | wc -l)
    else
        SYSTEM_INFO[has_zfs]="false"
    fi
    
    # NVMe/SSD detection
    SYSTEM_INFO[nvme_count]=$(ls /dev/nvme* 2>/dev/null | grep -c "nvme[0-9]$" || echo "0")
    
    log_debug "Storage: ${SYSTEM_INFO[root_fs]} (${SYSTEM_INFO[root_size]})"
}

detect_bootloader() {
    if [[ -d /boot/loader/entries ]] && command -v bootctl &>/dev/null; then
        SYSTEM_INFO[bootloader]="systemd-boot"
        SYSTEM_INFO[boot_entries_dir]="/boot/loader/entries"
    elif [[ -f /boot/grub/grub.cfg ]] || [[ -f /boot/grub2/grub.cfg ]]; then
        SYSTEM_INFO[bootloader]="grub"
        if [[ -f /etc/default/grub ]]; then
            SYSTEM_INFO[grub_config]="/etc/default/grub"
        fi
    elif [[ -f /boot/refind_linux.conf ]] || [[ -d /boot/EFI/refind ]]; then
        SYSTEM_INFO[bootloader]="refind"
    else
        SYSTEM_INFO[bootloader]="unknown"
    fi
    
    log_debug "Bootloader: ${SYSTEM_INFO[bootloader]}"
}

detect_initramfs() {
    if [[ -f /etc/mkinitcpio.conf ]]; then
        SYSTEM_INFO[initramfs]="mkinitcpio"
    elif command -v dracut &>/dev/null; then
        SYSTEM_INFO[initramfs]="dracut"
    else
        SYSTEM_INFO[initramfs]="unknown"
    fi
    
    log_debug "Initramfs: ${SYSTEM_INFO[initramfs]}"
}

detect_tpm() {
    if [[ -c /dev/tpm0 ]] || [[ -c /dev/tpmrm0 ]]; then
        SYSTEM_INFO[has_tpm]="true"
        
        # Try to get TPM version
        if command -v tpm2_getcap &>/dev/null; then
            if tpm2_getcap properties-fixed 2>/dev/null | grep -q "TPM2"; then
                SYSTEM_INFO[tpm_version]="2.0"
            fi
        else
            SYSTEM_INFO[tpm_version]="detected"
        fi
    else
        SYSTEM_INFO[has_tpm]="false"
        SYSTEM_INFO[tpm_version]="none"
    fi
    
    log_debug "TPM: ${SYSTEM_INFO[has_tpm]} (${SYSTEM_INFO[tpm_version]:-})"
}

detect_secureboot() {
    if command -v mokutil &>/dev/null; then
        if mokutil --sb-state 2>/dev/null | grep -qi "enabled"; then
            SYSTEM_INFO[secureboot]="enabled"
        else
            SYSTEM_INFO[secureboot]="disabled"
        fi
    elif [[ -d /sys/firmware/efi ]]; then
        # EFI system but can't determine SB state
        SYSTEM_INFO[secureboot]="unknown"
    else
        SYSTEM_INFO[secureboot]="not_applicable"
    fi
    
    # Check for sbctl
    if command -v sbctl &>/dev/null; then
        SYSTEM_INFO[has_sbctl]="true"
        if sbctl status 2>/dev/null | grep -q "Setup Mode"; then
            SYSTEM_INFO[sbctl_setup_mode]="true"
        else
            SYSTEM_INFO[sbctl_setup_mode]="false"
        fi
    else
        SYSTEM_INFO[has_sbctl]="false"
    fi
    
    log_debug "Secure Boot: ${SYSTEM_INFO[secureboot]}"
}

detect_distribution() {
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        SYSTEM_INFO[distro_id]="${ID:-unknown}"
        SYSTEM_INFO[distro_name]="${NAME:-Unknown}"
        SYSTEM_INFO[distro_version]="${VERSION_ID:-}"
        SYSTEM_INFO[distro_pretty]="${PRETTY_NAME:-Unknown}"
        
        if [[ "${ID:-}" == "cachyos" ]]; then
            SYSTEM_INFO[is_cachyos]="true"
        else
            SYSTEM_INFO[is_cachyos]="false"
        fi
    fi
    
    SYSTEM_INFO[kernel]=$(uname -r)
    SYSTEM_INFO[kernel_version]=$(uname -v)
    SYSTEM_INFO[arch]=$(uname -m)
    
    log_debug "Distro: ${SYSTEM_INFO[distro_name]} (${SYSTEM_INFO[kernel]})"
}

#==============================================================================
# SYSTEM INFORMATION DISPLAY
#==============================================================================
show_system_summary() {
    print_subsection "System Summary"
    
    echo -e "      ${C_INFO}CPU:${NC}          ${SYSTEM_INFO[cpu_model]:-Unknown}"
    echo -e "      ${C_INFO}Cores:${NC}        ${SYSTEM_INFO[cpu_threads]:-?} threads (${SYSTEM_INFO[cpu_cores]:-?} cores)"
    echo -e "      ${C_INFO}RAM:${NC}          ${SYSTEM_INFO[ram_total]:-Unknown}"
    
    # GPU info
    if [[ "${GPU_INFO[has_nvidia]}" == "true" ]]; then
        echo -e "      ${C_INFO}GPU:${NC}          ${C_NVIDIA}NVIDIA${NC} - ${GPU_INFO[nvidia_model]:-Unknown}"
    fi
    if [[ "${GPU_INFO[has_amd]}" == "true" ]]; then
        echo -e "      ${C_INFO}GPU:${NC}          ${C_AMD}AMD${NC} - ${GPU_INFO[amd_model]:-Unknown}"
    fi
    if [[ "${GPU_INFO[has_intel]}" == "true" ]]; then
        echo -e "      ${C_INFO}GPU:${NC}          ${C_INTEL}Intel${NC} - ${GPU_INFO[intel_model]:-Unknown}"
    fi
    
    echo -e "      ${C_INFO}IOMMU:${NC}        ${SYSTEM_INFO[iommu_groups]:-0} groups (${SYSTEM_INFO[iommu_type]:-Not enabled})"
    echo -e "      ${C_INFO}KVM:${NC}          ${SYSTEM_INFO[kvm_available]:-unknown}"
    echo -e "      ${C_INFO}TPM:${NC}          ${SYSTEM_INFO[tpm_version]:-none}"
    echo -e "      ${C_INFO}Bootloader:${NC}   ${SYSTEM_INFO[bootloader]:-Unknown}"
    echo -e "      ${C_INFO}Distro:${NC}       ${SYSTEM_INFO[distro_name]:-Unknown}"
    echo -e "      ${C_INFO}Kernel:${NC}       ${SYSTEM_INFO[kernel]:-Unknown}"
}

show_cpu_topology() {
    print_subsection "CPU Topology"
    
    echo -e "${C_HEADER}    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—${NC}"
    echo -e "${C_HEADER}    â•‘${NC} ${BOLD}CPU Configuration${NC}"
    echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    echo -e "${C_HEADER}    â•‘${NC} Model:        ${CPU_INFO[model]:-Unknown}"
    echo -e "${C_HEADER}    â•‘${NC} Vendor:       ${CPU_INFO[vendor]:-Unknown}"
    echo -e "${C_HEADER}    â•‘${NC} Cores:        ${CPU_INFO[cores]:-?} physical"
    echo -e "${C_HEADER}    â•‘${NC} Threads:      ${CPU_INFO[threads]:-?} logical (SMT: $([[ ${CPU_INFO[threads_per_core]:-1} -eq 2 ]] && echo "Yes" || echo "No"))"
    echo -e "${C_HEADER}    â•‘${NC} Sockets:      ${CPU_INFO[sockets]:-1}"
    echo -e "${C_HEADER}    â•‘${NC} NUMA Nodes:   ${CPU_INFO[numa_nodes]:-1}"
    
    if [[ "${CPU_INFO[is_x3d]}" == "true" ]]; then
        echo -e "${C_HEADER}    â•‘${NC} Architecture: ${C_SUCCESS}AMD X3D (V-Cache)${NC}"
        echo -e "${C_HEADER}    â•‘${NC} CCDs:         ${CPU_INFO[ccd_count]:-2}"
        for ((i=0; i<${CPU_INFO[ccd_count]:-0}; i+=1)); do
            local label="CCD$i"
            [[ $i -eq 0 ]] && label="CCD0 (V-Cache)"
            echo -e "${C_HEADER}    â•‘${NC}   $label: CPUs ${CCD_MAP[$i]:-?}"
        done
    fi
    
    if [[ "${CPU_INFO[is_hybrid]}" == "true" ]]; then
        echo -e "${C_HEADER}    â•‘${NC} Architecture: ${C_INTEL}Intel Hybrid (P+E cores)${NC}"
    fi
    
    echo -e "${C_HEADER}    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    
    # Visual CPU grid
    echo ""
    echo -e "    ${BOLD}CPU Thread Layout:${NC}"
    echo -n "    "
    
    local threads=${CPU_INFO[threads]:-0}
    local per_row=16
    
    for ((i=0; i<threads; i+=1)); do
        if [[ $((i % per_row)) -eq 0 ]] && [[ $i -gt 0 ]]; then
            echo ""
            echo -n "    "
        fi
        
        # Color by CCD/NUMA
        local color="$C_INFO"
        if [[ "${CPU_INFO[is_x3d]}" == "true" ]]; then
            local half=$((threads / 2))
            if [[ $i -lt $half ]]; then
                color="$C_SUCCESS"  # CCD0 (V-Cache)
            else
                color="$C_WARNING"  # CCD1
            fi
        fi
        
        printf "${color}%2d${NC} " $i
    done
    echo ""
    
    if [[ "${CPU_INFO[is_x3d]}" == "true" ]]; then
        echo ""
        echo -e "    Legend: ${C_SUCCESS}â– ${NC} CCD0 (V-Cache)  ${C_WARNING}â– ${NC} CCD1 (High Freq)"
    fi
}


#==============================================================================
# IOMMU GROUP ANALYSIS
#==============================================================================
analyze_iommu_groups() {
    print_subsection "IOMMU Group Analysis"
    
    if [[ "${SYSTEM_INFO[iommu_enabled]}" != "true" ]]; then
        msg_warn "IOMMU is not enabled"
        echo ""
        echo -e "    ${C_MUTED}To enable IOMMU:${NC}"
        echo -e "    ${C_MUTED}  1. Enable IOMMU in BIOS/UEFI (AMD-Vi or Intel VT-d)${NC}"
        echo -e "    ${C_MUTED}  2. Add kernel parameter: amd_iommu=on or intel_iommu=on${NC}"
        echo -e "    ${C_MUTED}  3. Reboot${NC}"
        return 1
    fi
    
    local isolated_gpus=0
    local problematic_groups=0
    
    echo -e "${C_HEADER}    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—${NC}"
    echo -e "${C_HEADER}    â•‘${NC} ${BOLD}IOMMU Groups Overview${NC}"
    echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    
    for group_path in /sys/kernel/iommu_groups/*/; do
        [[ -d "$group_path" ]] || continue
        
        local group_num=$(basename "$group_path")
        local devices=()
        local has_gpu=false
        local gpu_count=0
        local total_count=0
        
        for device_path in "$group_path"/devices/*; do
            [[ -e "$device_path" ]] || continue
            
            local pci_addr=$(basename "$device_path")
            local device_info=$(lspci -nns "$pci_addr" 2>/dev/null)
            
            devices+=("$device_info")
            total_count=$((total_count + 1))
            
            if echo "$device_info" | grep -qiE "VGA|3D controller|Display"; then
                has_gpu=true
                gpu_count=$((gpu_count + 1))
            fi
        done
        
        # Only show groups with GPUs or interesting devices
        if [[ "$has_gpu" == "true" ]] || [[ $total_count -gt 5 ]]; then
            local status_color="$C_SUCCESS"
            local status_icon="âœ”"
            
            if [[ $total_count -gt 5 ]]; then
                status_color="$C_WARNING"
                status_icon="âš "
                problematic_groups=$((problematic_groups + 1))
            fi
            
            if [[ $total_count -le 2 ]] && [[ "$has_gpu" == "true" ]]; then
                isolated_gpus=$((isolated_gpus + 1))
            fi
            
            echo -e "${C_HEADER}    â•‘${NC}"
            echo -e "${C_HEADER}    â•‘${NC} ${status_color}${status_icon}${NC} ${BOLD}IOMMU Group $group_num${NC} ($total_count devices)"
            
            for device in "${devices[@]}"; do
                local color="$C_MUTED"
                if echo "$device" | grep -qiE "VGA|3D controller|Display"; then
                    if echo "$device" | grep -qi "nvidia"; then
                        color="$C_NVIDIA"
                    elif echo "$device" | grep -qi "amd\|radeon"; then
                        color="$C_AMD"
                    elif echo "$device" | grep -qi "intel"; then
                        color="$C_INTEL"
                    else
                        color="$C_HIGHLIGHT"
                    fi
                elif echo "$device" | grep -qi "audio"; then
                    color="$C_INFO"
                fi
                echo -e "${C_HEADER}    â•‘${NC}   ${color}$device${NC}"
            done
        fi
    done
    
    echo -e "${C_HEADER}    â•‘${NC}"
    echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    echo -e "${C_HEADER}    â•‘${NC} ${BOLD}Summary:${NC}"
    echo -e "${C_HEADER}    â•‘${NC}   Total IOMMU Groups: ${SYSTEM_INFO[iommu_groups]}"
    echo -e "${C_HEADER}    â•‘${NC}   Isolated GPUs (good for passthrough): $isolated_gpus"
    
    if [[ $problematic_groups -gt 0 ]]; then
        echo -e "${C_HEADER}    â•‘${NC}   ${C_WARNING}Large groups (may need ACS override): $problematic_groups${NC}"
    fi
    
    echo -e "${C_HEADER}    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    
    SYSTEM_INFO[isolated_gpus]=$isolated_gpus
    return 0
}

#==============================================================================
# INSTALLATION MODULE - ALL PHASES
#==============================================================================
run_installation() {
    local mode="${1:-interactive}"
    
    # Pre-flight checks
    if ! check_root; then
        return 1
    fi
    
    if ! check_network; then
        return 1
    fi
    
    # Update state
    STATE[install_phase]="in_progress"
    STATE[install_mode]="$mode"
    STATE[install_timestamp]="$(date -Iseconds)"
    save_state
    
    # Show installation banner
    print_banner
    echo -e "    ${C_MUTED}Session: $SESSION_ID${NC}"
    echo -e "    ${C_MUTED}Mode: $mode${NC}"
    echo -e "    ${C_MUTED}Log: $LOG_FILE${NC}"
    echo ""
    
    # Run phases
    install_phase_01_detect
    install_phase_02_prompts "$mode"
    install_phase_03_desktop
    install_phase_04_virtualization
    install_phase_05_cockpit
    install_phase_06_containers
    install_phase_07_security
    install_phase_08_kernel
    install_phase_09_nvidia
    install_phase_10_aur
    install_phase_11_extensions
    install_phase_12_flatpak
    install_phase_13_services
    install_phase_14_secureboot
    install_phase_15_user_network
    install_phase_16_looking_glass
    install_phase_17_helpers
    
    # Generate report
    generate_install_report
    
    # Update state
    STATE[install_phase]="completed"
    save_state
    
    return 0
}

# Installation configuration variables
INSTALL_DESKTOP=0
INSTALL_LTS_KERNEL=0
INSTALL_SECUREBOOT=0
INSTALL_TPM=0
INSTALL_LOOKING_GLASS=0

install_phase_01_detect() {
    print_phase "1" "Hardware Detection"
    
    detect_system
    
    # Report findings
    if [[ "${CPU_INFO[vendor]}" == "AuthenticAMD" ]]; then
        msg_success "CPU: AMD (${CPU_INFO[model]})"
    elif [[ "${CPU_INFO[vendor]}" == "GenuineIntel" ]]; then
        msg_success "CPU: Intel (${CPU_INFO[model]})"
    fi
    
    if [[ "${CPU_INFO[virt_ext]}" != "none" ]]; then
        msg_success "Virtualization: ${CPU_INFO[virt_ext]}"
    else
        msg_fail "Virtualization not enabled in BIOS"
    fi
    
    if [[ "${GPU_INFO[has_nvidia]}" == "true" ]]; then
        msg_success "NVIDIA GPU detected"
    fi
    
    if [[ "${SYSTEM_INFO[iommu_enabled]}" == "true" ]]; then
        msg_success "IOMMU: ${SYSTEM_INFO[iommu_groups]} groups"
    else
        msg_skip "IOMMU" "not enabled"
    fi
    
    if [[ "${SYSTEM_INFO[has_tpm]}" == "true" ]]; then
        msg_success "TPM 2.0 detected"
    else
        msg_skip "TPM" "not detected"
    fi
    
    if [[ "${SYSTEM_INFO[is_cachyos]}" == "true" ]]; then
        msg_success "Distribution: CachyOS"
    else
        msg_info "Distribution: ${SYSTEM_INFO[distro_name]}"
    fi
}

install_phase_02_prompts() {
    local mode="$1"
    
    print_phase "2" "Configuration Options"
    echo ""
    
    case "$mode" in
        desktop)
            INSTALL_DESKTOP=1
            msg_info "Mode: Desktop (GNOME) - preset"
            ;;
        headless)
            INSTALL_DESKTOP=0
            msg_info "Mode: Headless server - preset"
            ;;
        minimal)
            INSTALL_DESKTOP=0
            msg_info "Mode: Minimal - preset"
            return
            ;;
        *)
            # Interactive prompts
            if ask_yes_no "Install GNOME Desktop? (No = Headless server)"; then
                INSTALL_DESKTOP=1
                msg_info "Mode: Desktop (GNOME)"
            else
                msg_info "Mode: Headless server"
            fi
            ;;
    esac
    
    if ask_yes_no "Use LTS kernel for ZFS stability?"; then
        INSTALL_LTS_KERNEL=1
        msg_info "Will install LTS kernel"
    fi
    
    if ask_yes_no "Configure Secure Boot (sbctl)?"; then
        INSTALL_SECUREBOOT=1
        msg_info "Will configure Secure Boot"
    fi
    
    if [[ "${SYSTEM_INFO[has_tpm]}" == "true" ]]; then
        if ask_yes_no "Configure host TPM for key storage?"; then
            INSTALL_TPM=1
            msg_info "Will configure TPM"
        fi
    fi
    
    if ask_yes_no "Install Looking Glass for GPU passthrough?"; then
        INSTALL_LOOKING_GLASS=1
        msg_info "Will install Looking Glass"
    fi
    
    echo ""
    msg_info "Starting installation..."
    sleep 2
}

install_phase_03_desktop() {
    print_phase "3" "Desktop Environment"
    
    sync_package_db
    
    if [[ $INSTALL_DESKTOP -eq 0 ]]; then
        msg_skip "GNOME Desktop" "headless mode"
        return 0
    fi
    
    msg_info "Installing GNOME Desktop..."
    install_packages "GNOME Desktop" "${PKGS_DESKTOP[@]}"
    
    msg_info "Installing GNOME Extensions..."
    install_packages "GNOME Extensions" \
        gnome-shell-extension-caffeine \
        gnome-shell-extension-dash-to-dock 2>/dev/null || true
}

install_phase_04_virtualization() {
    print_phase "4" "Virtualization Stack"
    
    msg_info "Installing KVM/QEMU/Libvirt..."
    install_packages "Virtualization" "${PKGS_VIRTUALIZATION[@]}"
    
    msg_info "Installing UEFI & vTPM support..."
    install_packages "UEFI/vTPM" edk2-ovmf swtpm libtpms
}

install_phase_05_cockpit() {
    print_phase "5" "Cockpit & Monitoring"
    
    msg_info "Installing Cockpit..."
    install_packages "Cockpit Suite" "${PKGS_COCKPIT[@]}"
    
    msg_info "Installing Monitoring tools..."
    install_packages "Monitoring" pcp lm_sensors
}

install_phase_06_containers() {
    print_phase "6" "Containers & Network"
    
    msg_info "Installing Podman..."
    install_packages "Podman Stack" "${PKGS_CONTAINERS[@]}"
    
    msg_info "Installing Network & Firewall..."
    install_packages "Network" "${PKGS_NETWORK[@]}"
}

install_phase_07_security() {
    print_phase "7" "Power & Security Tools"
    
    msg_info "Installing TuneD..."
    install_packages "TuneD" tuned
    
    msg_info "Installing Security Tools..."
    install_packages "Security" tpm2-tools sbctl kexec-tools
    
    msg_info "Installing Utilities..."
    install_packages "Utilities" git base-devel flatpak p7zip wget curl htop btop
}

install_phase_08_kernel() {
    print_phase "8" "Kernel & ZFS"
    
    if [[ $INSTALL_LTS_KERNEL -eq 1 ]]; then
        msg_info "Installing LTS kernel..."
        install_packages "LTS Kernel" linux-cachyos-lts linux-cachyos-lts-headers 2>/dev/null || \
        install_packages "LTS Kernel" linux-lts linux-lts-headers
        
        msg_info "Installing ZFS for LTS..."
        install_packages "ZFS (LTS)" linux-cachyos-lts-zfs zfs-utils 2>/dev/null || \
        install_packages "ZFS (DKMS)" zfs-dkms zfs-utils
    else
        msg_info "Using current kernel..."
        
        if pacman -Qs linux-cachyos &>/dev/null; then
            install_packages "ZFS" linux-cachyos-zfs zfs-utils 2>/dev/null || \
            install_packages "ZFS (DKMS)" zfs-dkms zfs-utils
        else
            install_packages "ZFS (DKMS)" zfs-dkms zfs-utils
        fi
    fi
}

install_phase_09_nvidia() {
    if [[ "${GPU_INFO[has_nvidia]}" != "true" ]]; then
        return 0
    fi
    
    print_phase "9" "NVIDIA Configuration"
    
    if pacman -Qs nvidia &>/dev/null; then
        msg_skip "NVIDIA drivers" "already installed"
    else
        msg_info "Installing NVIDIA drivers..."
        install_packages "NVIDIA" nvidia-dkms nvidia-utils nvidia-settings
    fi
    
    msg_info "Configuring Early KMS..."
    local mkinitcpio="/etc/mkinitcpio.conf"
    if [[ -f "$mkinitcpio" ]] && ! grep -q "nvidia" "$mkinitcpio"; then
        cp "$mkinitcpio" "${mkinitcpio}${BACKUP_SUFFIX}"
        sed -i 's/^MODULES=(\(.*\))/MODULES=(\1 nvidia nvidia_modeset nvidia_uvm nvidia_drm)/' "$mkinitcpio"
        mkinitcpio -P >> "$DEBUG_LOG" 2>&1 && msg_success "Initramfs rebuilt" || msg_fail "Initramfs"
    else
        msg_skip "Early KMS" "already configured"
    fi
    
    echo "options nvidia_drm modeset=1 fbdev=1" > /etc/modprobe.d/nvidia.conf
    msg_success "NVIDIA DRM modeset"
}

install_phase_10_aur() {
    print_phase "10" "AUR Packages"
    
    install_yay
    
    msg_info "Installing Cockpit extensions..."
    install_aur "cockpit-sensors"
    install_aur "cockpit-benchmark"
    install_aur "virtio-win"
    
    # Install Cockpit ZFS Manager
    msg_info "Installing Cockpit ZFS Manager..."
    if [[ -d /usr/share/cockpit/zfs ]]; then
        msg_skip "ZFS Manager" "already installed"
    else
        local build_dir="/tmp/cockpit-zfs-$$"
        mkdir -p "$build_dir"
        cd "$build_dir"
        
        if git clone https://github.com/45Drives/cockpit-zfs-manager.git >> "$DEBUG_LOG" 2>&1; then
            if [[ -d cockpit-zfs-manager/zfs ]]; then
                cp -r cockpit-zfs-manager/zfs /usr/share/cockpit/
                msg_success "Cockpit ZFS Manager"
            fi
        else
            msg_fail "Cockpit ZFS Manager"
        fi
        
        cd /
        rm -rf "$build_dir"
    fi
}

install_phase_11_extensions() {
    print_phase "11" "GNOME Extensions"
    
    if [[ $INSTALL_DESKTOP -eq 0 ]]; then
        msg_skip "GNOME Extensions" "headless mode"
        return 0
    fi
    
    local ext_dir="/home/$REAL_USER/.local/share/gnome-shell/extensions"
    mkdir -p "$ext_dir"
    
    # TuneD Profile Switcher
    local tuned_ext="$ext_dir/tuned-switcher@Rea1-ms"
    
    if [[ -d "$tuned_ext" ]]; then
        msg_skip "TuneD Switcher" "already installed"
    else
        msg_info "Installing TuneD Profile Switcher..."
        local build_dir="/tmp/tuned-ext-$$"
        mkdir -p "$build_dir"
        cd "$build_dir"
        
        if git clone https://github.com/Rea1-ms/gnome-extension-tuned-switcher.git >> "$DEBUG_LOG" 2>&1; then
            local src=$(find gnome-extension-tuned-switcher -name "metadata.json" -exec dirname {} \; | head -1)
            if [[ -n "$src" && -d "$src" ]]; then
                cp -r "$src" "$tuned_ext"
                chown -R "$REAL_USER:$REAL_USER" "$ext_dir"
                msg_success "TuneD Switcher"
            else
                msg_fail "TuneD Switcher (no metadata.json)"
            fi
        else
            msg_fail "TuneD Switcher"
        fi
        
        cd /
        rm -rf "$build_dir"
    fi
}

install_phase_12_flatpak() {
    print_phase "12" "Flatpak Applications"
    
    flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo >> "$DEBUG_LOG" 2>&1
    msg_success "Flathub repository"
    
    local apps=(
        "org.gnome.Epiphany:GNOME Web"
        "com.github.tchx84.Flatseal:Flatseal"
        "io.github.kolunmi.Bazaar:Bazaar"
    )
    
    if [[ $INSTALL_DESKTOP -eq 1 ]]; then
        apps+=("com.mattjakeman.ExtensionManager:Extension Manager")
    fi
    
    for entry in "${apps[@]}"; do
        local id="${entry%%:*}"
        local name="${entry##*:}"
        
        if flatpak list 2>/dev/null | grep -q "$id"; then
            msg_skip "$name" "already installed"
        else
            msg_info "Installing $name..."
            if flatpak install -y flathub "$id" >> "$DEBUG_LOG" 2>&1; then
                msg_success "$name"
            else
                msg_fail "$name"
            fi
        fi
    done
}

install_phase_13_services() {
    print_phase "13" "Services Configuration"
    
    if [[ $INSTALL_DESKTOP -eq 1 ]]; then
        systemctl enable gdm >> "$DEBUG_LOG" 2>&1 && msg_success "GDM enabled" || msg_fail "GDM"
    else
        msg_skip "GDM" "headless mode"
    fi
    
    msg_info "Configuring TuneD..."
    systemctl stop power-profiles-daemon 2>/dev/null
    systemctl disable power-profiles-daemon 2>/dev/null
    systemctl mask power-profiles-daemon 2>/dev/null
    systemctl unmask tuned 2>/dev/null
    systemctl enable tuned >> "$DEBUG_LOG" 2>&1
    systemctl start tuned >> "$DEBUG_LOG" 2>&1
    sleep 2
    tuned-adm profile virtual-host >> "$DEBUG_LOG" 2>&1 && \
        msg_success "TuneD: virtual-host" || msg_fail "TuneD profile"
    
    msg_info "Enabling Libvirt (modular)..."
    for sock in virtqemud virtnetworkd virtstoraged virtnodedevd virtproxyd virtsecretd virtinterfaced virtnwfilterd; do
        systemctl enable ${sock}.socket >> "$DEBUG_LOG" 2>&1
    done
    msg_success "Libvirt modular sockets"
    
    systemctl enable cockpit.socket >> "$DEBUG_LOG" 2>&1 && \
        msg_success "Cockpit enabled" || msg_fail "Cockpit"
    
    systemctl enable pmcd pmlogger >> "$DEBUG_LOG" 2>&1 && \
        msg_success "PCP metrics" || msg_fail "PCP"
    
    msg_info "Configuring Firewalld..."
    systemctl enable firewalld >> "$DEBUG_LOG" 2>&1
    systemctl start firewalld >> "$DEBUG_LOG" 2>&1
    firewall-cmd --permanent --add-service=cockpit >> "$DEBUG_LOG" 2>&1
    firewall-cmd --reload >> "$DEBUG_LOG" 2>&1
    msg_success "Firewalld configured"
    
    msg_info "Configuring Samba..."
    mkdir -p /etc/samba
    if [[ ! -f /etc/samba/smb.conf ]]; then
        cat > /etc/samba/smb.conf << 'SMBCONF'
[global]
   workgroup = WORKGROUP
   server string = MiOS-Build
   security = user
   map to guest = Bad User
   load printers = no
   
   shadow: snapdir = .zfs/snapshot
   shadow: sort = desc
   shadow: format = %Y.%m.%d-%H.%M.%S
SMBCONF
        mkdir -p /srv/samba/public
        chmod 775 /srv/samba/public
    fi
    systemctl enable smb nmb wsdd >> "$DEBUG_LOG" 2>&1
    msg_success "Samba configured"
    
    systemctl enable avahi-daemon >> "$DEBUG_LOG" 2>&1
    msg_success "Avahi enabled"
    
    for svc in zfs-import-cache zfs-mount zfs-zed zfs.target; do
        systemctl enable $svc >> "$DEBUG_LOG" 2>&1
    done
    msg_success "ZFS services"
    
    podman system migrate >> "$DEBUG_LOG" 2>&1 || true
}

install_phase_14_secureboot() {
    print_phase "14" "Security Configuration"
    
    if [[ $INSTALL_SECUREBOOT -eq 1 ]]; then
        msg_info "Configuring Secure Boot..."
        
        if sbctl status 2>/dev/null | grep -q "Setup Mode"; then
            sbctl create-keys >> "$DEBUG_LOG" 2>&1 && msg_success "SB keys created" || msg_fail "SB keys"
            sbctl enroll-keys --microsoft >> "$DEBUG_LOG" 2>&1 && msg_success "SB keys enrolled" || msg_fail "SB enroll"
            
            for f in /boot/EFI/systemd/systemd-bootx64.efi /boot/vmlinuz-linux-cachyos /boot/vmlinuz-linux-cachyos-lts /boot/vmlinuz-linux; do
                [[ -f "$f" ]] && sbctl sign -s "$f" >> "$DEBUG_LOG" 2>&1
            done
            msg_success "Boot files signed"
            msg_info "Enable Secure Boot in BIOS after reboot"
        else
            msg_skip "Secure Boot" "not in Setup Mode"
        fi
    fi
    
    if [[ $INSTALL_TPM -eq 1 ]] && [[ "${SYSTEM_INFO[has_tpm]}" == "true" ]]; then
        msg_info "Testing TPM..."
        if tpm2_getcap properties-fixed >> "$DEBUG_LOG" 2>&1; then
            msg_success "TPM 2.0 operational"
        else
            msg_fail "TPM communication"
        fi
    fi
    
    msg_info "Configuring swtpm..."
    if command -v swtpm &>/dev/null; then
        getent group swtpm &>/dev/null || groupadd -r swtpm
        getent passwd swtpm &>/dev/null || useradd -r -g swtpm -d /var/lib/swtpm -s /sbin/nologin swtpm
        mkdir -p /var/lib/swtpm-localca
        chown -R swtpm:swtpm /var/lib/swtpm-localca 2>/dev/null
        msg_success "swtpm ready for Windows 11 VMs"
    fi
}

install_phase_15_user_network() {
    print_phase "15" "User & Network"
    
    msg_info "Adding $REAL_USER to groups..."
    usermod -aG libvirt,kvm,wheel,render,video "$REAL_USER" >> "$DEBUG_LOG" 2>&1 && \
        msg_success "User groups" || msg_fail "User groups"
    
    mkdir -p /etc/polkit-1/rules.d
    cat > /etc/polkit-1/rules.d/50-libvirt.rules << 'POLKIT'
polkit.addRule(function(action, subject) {
    if (action.id == "org.libvirt.unix.manage" && subject.isInGroup("libvirt")) {
        return polkit.Result.YES;
    }
});
POLKIT
    msg_success "Polkit rule"
    
    hostnamectl set-hostname MiOS-Build >> "$DEBUG_LOG" 2>&1
    msg_success "Hostname set: MiOS-Build"
}

install_phase_16_looking_glass() {
    if [[ $INSTALL_LOOKING_GLASS -eq 0 ]]; then
        return 0
    fi
    
    print_phase "16" "Looking Glass"
    
    msg_info "Installing Looking Glass dependencies..."
    install_packages "Looking Glass Dependencies" \
        cmake gcc make pkgconf binutils \
        libx11 nettle libxi libxinerama libxcursor libxpresent \
        libxkbcommon wayland-protocols ttf-dejavu \
        libsamplerate libpulse pipewire-pulse \
        spice-protocol fontconfig freetype2 \
        libxss libxrandr
    
    msg_info "Building Looking Glass from source..."
    
    local lg_version="B7-rc1"
    local build_dir="/tmp/looking-glass-$$"
    
    mkdir -p "$build_dir"
    
    # Build as regular user
    sudo -u "$REAL_USER" bash -c "
        cd '$build_dir'
        git clone --recursive https://github.com/gnif/LookingGlass.git
        cd LookingGlass
        git checkout $lg_version
        git submodule update --init --recursive
        
        mkdir -p client/build
        cd client/build
        cmake ../
        make -j\$(nproc)
    " >> "$DEBUG_LOG" 2>&1
    
    if [[ -f "$build_dir/LookingGlass/client/automation/looking-glass-client" ]]; then
        cp "$build_dir/LookingGlass/client/automation/looking-glass-client" /usr/local/bin/
        chmod +x /usr/local/bin/looking-glass-client
        msg_success "Looking Glass client installed"
        
        STATE[looking_glass_installed]="true"
    else
        msg_fail "Looking Glass build failed"
    fi
    
    # Create shared memory device
    msg_info "Configuring shared memory..."
    cat > /etc/tmpfiles.d/10-looking-glass.conf << TMPFILES
f /dev/shm/looking-glass 0660 $REAL_USER kvm -
TMPFILES
    systemd-tmpfiles --create /etc/tmpfiles.d/10-looking-glass.conf >> "$DEBUG_LOG" 2>&1
    msg_success "Shared memory configured"
    
    rm -rf "$build_dir"
}

install_phase_17_helpers() {
    print_phase "17" "Helper Scripts & Final Setup"
    
    # Create VM helper script
    msg_info "Creating helper scripts..."
    
    cat > /usr/local/bin/create-win11-vm << 'VMHELPER'
#!/bin/bash
echo "Windows 11 VM Creator"
echo "===================="
echo ""
echo "Usage: virt-install --name win11 --memory 16384 --vcpus 12 \\"
echo "  --os-variant win11 --boot uefi \\"
echo "  --tpm backend.type=emulator,backend.version=2.0,model=tpm-tis \\"
echo "  --disk size=100,bus=virtio \\"
echo "  --cdrom /path/to/win11.iso \\"
echo "  --network network=default,model=virtio"
VMHELPER
    chmod +x /usr/local/bin/create-win11-vm
    
    # Create IOMMU groups viewer
    cat > /usr/local/bin/iommu-groups << 'IOMMUHELPER'
#!/bin/bash
shopt -s nullglob
for g in $(find /sys/kernel/iommu_groups/* -maxdepth 0 -type d | sort -V); do
    echo -e "\033[1;34mIOMMU Group ${g##*/}:\033[0m"
    for d in $g/devices/*; do
        echo "  $(lspci -nns ${d##*/})"
    done
done
IOMMUHELPER
    chmod +x /usr/local/bin/iommu-groups
    
    msg_success "Helper scripts created"
    
    # Final sync
    sync
}

generate_install_report() {
    print_section "Installation Complete"
    
    local ip=$(ip -4 addr show scope global | grep inet | head -1 | awk '{print $2}' | cut -d'/' -f1)
    local mode=$([[ $INSTALL_DESKTOP -eq 1 ]] && echo "Desktop (GNOME)" || echo "Headless Server")
    
    # Generate report file
    cat > "$REPORT_FILE" << REPORT
================================================================================
MiOS-Build INSTALLATION REPORT
================================================================================
Date: $(date)
Session: $SESSION_ID
Mode: $mode

SYSTEM INFORMATION
==================
CPU: ${SYSTEM_INFO[cpu_model]}
RAM: ${SYSTEM_INFO[ram_total]}
GPU: ${GPU_INFO[nvidia_model]:-None}
IOMMU Groups: ${SYSTEM_INFO[iommu_groups]}
Kernel: ${SYSTEM_INFO[kernel]}

INSTALLATION SUMMARY
====================
Successful: ${#SUCCESS_TASKS[@]}
Failed: ${#FAILED_TASKS[@]}
Skipped: ${#SKIPPED_TASKS[@]}

SUCCESSFUL TASKS
$(printf ' âœ” %s\n' "${SUCCESS_TASKS[@]}")

FAILED TASKS
$(if [[ ${#FAILED_TASKS[@]} -eq 0 ]]; then echo " None"; else printf ' âœ– %s\n' "${FAILED_TASKS[@]}"; fi)

SKIPPED TASKS
$(if [[ ${#SKIPPED_TASKS[@]} -eq 0 ]]; then echo " None"; else printf ' â—‹ %s\n' "${SKIPPED_TASKS[@]}"; fi)

ACCESS INFORMATION
==================
Cockpit: https://${ip:-localhost}:9090
User: $REAL_USER (added to libvirt, kvm groups)

LOGS
====
Session: $LOG_FILE
Debug: $DEBUG_LOG
Report: $REPORT_FILE
================================================================================
REPORT
    
    # Display summary
    echo ""
    echo -e "${C_HEADER}    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}   ${C_SUCCESS}â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—${NC}        ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}   ${C_SUCCESS}â•šâ•â•â•â•â•â•â•šâ•â•â•â•â•â•â•šâ•â•â•â•â•â•â•šâ•â•â•â•â•â•â•šâ•â•â•â•â•â•â•šâ•â•â•â•â•â•â•šâ•â•â•â•â•â•â•šâ•â•â•â•â•â•â•šâ•â•â•â•â•â•${NC}        ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}              ${WHITE}I N S T A L L A T I O N   C O M P L E T E${NC}                    ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}   ${C_INFO}Mode:${NC}        ${WHITE}$mode${NC}"
    echo -e "${C_HEADER}    â•‘${NC}   ${C_SUCCESS}Successful:${NC}  ${WHITE}${#SUCCESS_TASKS[@]}${NC}"
    echo -e "${C_HEADER}    â•‘${NC}   ${C_ERROR}Failed:${NC}      ${WHITE}${#FAILED_TASKS[@]}${NC}"
    echo -e "${C_HEADER}    â•‘${NC}   ${C_MUTED}Skipped:${NC}     ${WHITE}${#SKIPPED_TASKS[@]}${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}   ${C_INFO}â–¸${NC} Cockpit:  ${WHITE}https://${ip:-localhost}:9090${NC}"
    echo -e "${C_HEADER}    â•‘${NC}   ${C_INFO}â–¸${NC} Report:   ${C_MUTED}$REPORT_FILE${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    echo ""
    echo -e "    ${C_ACCENT}â–¶ REBOOT NOW:${NC} ${WHITE}sudo reboot${NC}"
    echo ""
    
    STATE[reboot_required]="true"
    save_state
}

#==============================================================================
# VFIO CONFIGURATION MODULE
#==============================================================================
configure_vfio() {
    if ! check_root; then
        return 1
    fi
    
    print_small_banner "VFIO GPU Passthrough Configuration"
    
    detect_system
    
    # Check IOMMU
    if [[ "${SYSTEM_INFO[iommu_enabled]}" != "true" ]]; then
        msg_fail "IOMMU is not enabled"
        echo ""
        echo -e "    ${C_MUTED}IOMMU must be enabled in BIOS and kernel parameters.${NC}"
        echo -e "    ${C_MUTED}Add to kernel cmdline: amd_iommu=on iommu=pt${NC}"
        echo -e "    ${C_MUTED}                   or: intel_iommu=on iommu=pt${NC}"
        return 1
    fi
    
    vfio_detect_bootloader
    vfio_detect_devices
    vfio_select_devices
    vfio_show_iommu_analysis
    vfio_configure_modprobe
    vfio_configure_initramfs
    vfio_configure_bootloader
    vfio_create_helpers
    vfio_show_summary
    
    STATE[vfio_configured]="true"
    STATE[reboot_required]="true"
    save_state
}

vfio_detect_bootloader() {
    print_subsection "Bootloader Detection"
    
    if [[ -d /boot/loader/entries ]] && command -v bootctl &>/dev/null; then
        VFIO_BOOTLOADER="systemd-boot"
        VFIO_BOOT_ENTRIES_DIR="/boot/loader/entries"
        msg_success "Detected: systemd-boot"
    elif [[ -f /boot/grub/grub.cfg ]] || [[ -f /boot/grub2/grub.cfg ]]; then
        VFIO_BOOTLOADER="grub"
        VFIO_GRUB_CONF="/etc/default/grub"
        msg_success "Detected: GRUB"
    elif [[ -f /boot/refind_linux.conf ]]; then
        VFIO_BOOTLOADER="refind"
        msg_success "Detected: rEFInd"
    else
        VFIO_BOOTLOADER="manual"
        msg_warn "Bootloader not detected - manual configuration required"
    fi
}

vfio_detect_devices() {
    print_subsection "PCIe Device Discovery"
    
    # Reset arrays
    VFIO_SELECTED_DEVICES=()
    VFIO_SELECTED_IDS=()
    VFIO_SELECTED_DRIVERS=()
    
    local -a all_devices=()
    
    # Find GPUs
    while IFS= read -r line; do
        [[ -n "$line" ]] && all_devices+=("$line")
    done < <(lspci -nn | grep -E "VGA compatible controller|3D controller|Display controller")
    
    # Find GPU audio devices
    while IFS= read -r line; do
        [[ -n "$line" ]] && all_devices+=("$line")
    done < <(lspci -nn | grep -iE "Audio device.*(NVIDIA|AMD|Intel.*Display)")
    
    # Find GPU USB controllers
    while IFS= read -r line; do
        [[ -n "$line" ]] && all_devices+=("$line")
    done < <(lspci -nn | grep -iE "USB.*(NVIDIA|AMD)")
    
    echo ""
    echo -e "${C_HEADER}    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—${NC}"
    echo -e "${C_HEADER}    â•‘${NC} ${BOLD}Available PCIe Devices for VFIO Isolation${NC}"
    echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    
    local counter=1
    for device in "${all_devices[@]}"; do
        local pci_addr=$(echo "$device" | awk '{print $1}')
        local device_id=$(echo "$device" | grep -oP '\[\K[0-9a-f]{4}:[0-9a-f]{4}(?=\])' | tail -1)
        local device_desc=$(echo "$device" | sed 's/^[^ ]* //' | sed 's/ \[[0-9a-f:]*\]//')
        local current_driver=$(lspci -nnk -s "$pci_addr" | grep "Kernel driver in use:" | awk '{print $5}')
        local iommu_group="N/A"
        
        if [[ -L "/sys/bus/pci/devices/0000:$pci_addr/iommu_group" ]]; then
            iommu_group=$(basename $(readlink "/sys/bus/pci/devices/0000:$pci_addr/iommu_group"))
        fi
        
        # Color by vendor
        local color="$NC"
        if echo "$device_desc" | grep -qi "nvidia"; then
            color="$C_NVIDIA"
        elif echo "$device_desc" | grep -qi "amd\|radeon"; then
            color="$C_AMD"
        elif echo "$device_desc" | grep -qi "intel"; then
            color="$C_INTEL"
        fi
        
        echo -e "${C_HEADER}    â•‘${NC} ${BOLD}${counter})${NC} ${color}${device_desc}${NC}"
        echo -e "${C_HEADER}    â•‘${NC}    PCI: ${pci_addr} â”‚ ID: ${device_id} â”‚ IOMMU: ${iommu_group}"
        echo -e "${C_HEADER}    â•‘${NC}    Driver: ${current_driver:-none}"
        echo -e "${C_HEADER}    â•Ÿâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•¢${NC}"
        
        # Store for selection
        VFIO_ALL_DEVICES[$counter]="$device"
        VFIO_ALL_ADDRS[$counter]="$pci_addr"
        VFIO_ALL_IDS[$counter]="$device_id"
        VFIO_ALL_DRIVERS[$counter]="${current_driver:-none}"
        
        counter=$((counter + 1))
    done
    
    VFIO_DEVICE_COUNT=$((counter - 1))
    echo -e "${C_HEADER}    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
}

vfio_select_devices() {
    print_subsection "Device Selection"
    
    echo ""
    echo -e "    ${C_INFO}Select devices for VFIO isolation:${NC}"
    echo -e "    ${C_MUTED}  â€¢ Enter device numbers separated by spaces (e.g., 1 2)${NC}"
    echo -e "    ${C_MUTED}  â€¢ Enter 'a' to select all devices${NC}"
    echo -e "    ${C_MUTED}  â€¢ Enter 'q' to cancel${NC}"
    echo ""
    
    while true; do
        read -rp "      Selection: " selection
        
        if [[ "$selection" == "q" ]]; then
            msg_info "Cancelled"
            return 1
        elif [[ "$selection" == "a" ]]; then
            for ((i=1; i<=VFIO_DEVICE_COUNT; i+=1)); do
                VFIO_SELECTED_DEVICES+=("${VFIO_ALL_ADDRS[$i]}")
                VFIO_SELECTED_IDS+=("${VFIO_ALL_IDS[$i]}")
                VFIO_SELECTED_DRIVERS+=("${VFIO_ALL_DRIVERS[$i]}")
            done
            break
        else
            local valid=true
            for num in $selection; do
                if ! [[ "$num" =~ ^[0-9]+$ ]] || [[ $num -lt 1 ]] || [[ $num -gt $VFIO_DEVICE_COUNT ]]; then
                    msg_warn "Invalid selection: $num"
                    valid=false
                    break
                fi
            done
            
            if [[ "$valid" == "true" ]]; then
                for num in $selection; do
                    VFIO_SELECTED_DEVICES+=("${VFIO_ALL_ADDRS[$num]}")
                    VFIO_SELECTED_IDS+=("${VFIO_ALL_IDS[$num]}")
                    VFIO_SELECTED_DRIVERS+=("${VFIO_ALL_DRIVERS[$num]}")
                done
                break
            fi
        fi
    done
    
    msg_success "Selected ${#VFIO_SELECTED_DEVICES[@]} device(s)"
    
    # Check for related devices in same IOMMU group
    vfio_check_related_devices
}

vfio_check_related_devices() {
    local -a related=()
    
    for addr in "${VFIO_SELECTED_DEVICES[@]}"; do
        local group_path="/sys/bus/pci/devices/0000:$addr/iommu_group/devices"
        
        if [[ -d "$group_path" ]]; then
            for device_path in "$group_path"/*; do
                local related_addr=$(basename "$device_path" | sed 's/0000://')
                
                # Check if not already selected
                local already_selected=false
                for selected in "${VFIO_SELECTED_DEVICES[@]}"; do
                    if [[ "$selected" == "$related_addr" ]]; then
                        already_selected=true
                        break
                    fi
                done
                
                if [[ "$already_selected" == "false" ]]; then
                    local related_info=$(lspci -nns "$related_addr" 2>/dev/null)
                    related+=("$related_addr: $related_info")
                fi
            done
        fi
    done
    
    if [[ ${#related[@]} -gt 0 ]]; then
        echo ""
        msg_warn "Found related devices in same IOMMU group:"
        for r in "${related[@]}"; do
            echo -e "      ${C_MUTED}$r${NC}"
        done
        echo ""
        
        if ask_yes_no "Include related devices? (Recommended)" "y"; then
            for r in "${related[@]}"; do
                local addr=$(echo "$r" | cut -d: -f1)
                local id=$(echo "$r" | grep -oP '\[\K[0-9a-f]{4}:[0-9a-f]{4}(?=\])' | tail -1)
                VFIO_SELECTED_DEVICES+=("$addr")
                VFIO_SELECTED_IDS+=("$id")
            done
            msg_success "Added ${#related[@]} related device(s)"
        fi
    fi
}

vfio_show_iommu_analysis() {
    print_subsection "IOMMU Group Analysis"
    
    local -A group_devices
    
    for addr in "${VFIO_SELECTED_DEVICES[@]}"; do
        if [[ -L "/sys/bus/pci/devices/0000:$addr/iommu_group" ]]; then
            local group=$(basename $(readlink "/sys/bus/pci/devices/0000:$addr/iommu_group"))
            group_devices[$group]+="$addr "
        fi
    done
    
    for group in "${!group_devices[@]}"; do
        local devices=(${group_devices[$group]})
        local group_size=$(ls "/sys/kernel/iommu_groups/$group/devices" 2>/dev/null | wc -l)
        
        echo -e "    ${BOLD}IOMMU Group $group${NC} (${#devices[@]} selected / $group_size total)"
        
        for addr in "${devices[@]}"; do
            echo -e "      ${C_SUCCESS}âœ”${NC} $addr"
        done
        
        if [[ $group_size -gt 5 ]]; then
            msg_warn "Large IOMMU group ($group_size devices) - consider ACS override if issues"
        fi
        echo ""
    done
}

vfio_configure_modprobe() {
    print_subsection "Modprobe Configuration"
    
    local vfio_conf="/etc/modprobe.d/vfio.conf"
    local vfio_ids=$(IFS=,; echo "${VFIO_SELECTED_IDS[*]}")
    
    # Backup existing
    if [[ -f "$vfio_conf" ]]; then
        cp "$vfio_conf" "${vfio_conf}${BACKUP_SUFFIX}"
        msg_info "Backed up existing config"
    fi
    
    # Determine drivers to block
    local has_nvidia=false
    local has_amd=false
    
    for driver in "${VFIO_SELECTED_DRIVERS[@]}"; do
        [[ "$driver" =~ nvidia ]] && has_nvidia=true
        [[ "$driver" =~ amdgpu|radeon ]] && has_amd=true
    done
    
    cat > "$vfio_conf" << VFIOCONF
# VFIO Configuration for PCIe Device Isolation
# Generated by MiOS-Build Unified on $(date)
# Isolated devices: ${#VFIO_SELECTED_DEVICES[@]}

# Bind selected devices to VFIO-PCI driver
options vfio-pci ids=$vfio_ids

VFIOCONF
    
    if [[ "$has_nvidia" == "true" ]]; then
        cat >> "$vfio_conf" << 'NVIDIASOFTDEP'
# NVIDIA driver dependencies
softdep nvidia pre: vfio-pci
softdep nvidia_drm pre: vfio-pci
softdep nvidia_modeset pre: vfio-pci
softdep nvidia_uvm pre: vfio-pci
softdep nouveau pre: vfio-pci

NVIDIASOFTDEP
    fi
    
    if [[ "$has_amd" == "true" ]]; then
        cat >> "$vfio_conf" << 'AMDSOFTDEP'
# AMD driver dependencies
softdep amdgpu pre: vfio-pci
softdep radeon pre: vfio-pci

AMDSOFTDEP
    fi
    
    msg_success "Created $vfio_conf"
}

vfio_configure_initramfs() {
    print_subsection "Initramfs Configuration"
    
    if [[ "${SYSTEM_INFO[initramfs]}" == "mkinitcpio" ]]; then
        local conf="/etc/mkinitcpio.conf"
        
        if [[ -f "$conf" ]]; then
            cp "$conf" "${conf}${BACKUP_SUFFIX}"
            
            # Add VFIO modules
            if ! grep -q "vfio_pci" "$conf"; then
                sed -i 's/^MODULES=(\(.*\))/MODULES=(\1 vfio_pci vfio vfio_iommu_type1)/' "$conf"
                # Clean up double spaces
                sed -i 's/( /(/g' "$conf"
            fi
            
            # Ensure modconf hook is present and before filesystems
            if ! grep -q "modconf" "$conf"; then
                sed -i 's/HOOKS=(\(.*\)filesystems/HOOKS=(\1modconf filesystems/' "$conf"
            fi
            
            msg_info "Regenerating initramfs..."
            mkinitcpio -P >> "$DEBUG_LOG" 2>&1 && msg_success "Initramfs regenerated" || msg_fail "Initramfs"
        fi
    elif [[ "${SYSTEM_INFO[initramfs]}" == "dracut" ]]; then
        local conf="/etc/dracut.conf.d/vfio.conf"
        
        cat > "$conf" << DRACUTCONF
# VFIO modules for GPU passthrough
add_drivers+=" vfio vfio_iommu_type1 vfio_pci "
DRACUTCONF
        
        msg_info "Regenerating initramfs..."
        dracut -f >> "$DEBUG_LOG" 2>&1 && msg_success "Initramfs regenerated" || msg_fail "Initramfs"
    fi
}

vfio_configure_bootloader() {
    print_subsection "Bootloader Configuration"
    
    # Build kernel parameters
    local iommu_param
    if [[ "${CPU_INFO[vendor]}" == "AuthenticAMD" ]]; then
        iommu_param="amd_iommu=on"
    else
        iommu_param="intel_iommu=on"
    fi
    
    local vfio_ids=$(IFS=,; echo "${VFIO_SELECTED_IDS[*]}")
    local kernel_params="$iommu_param iommu=pt vfio-pci.ids=$vfio_ids"
    
    case "$VFIO_BOOTLOADER" in
        systemd-boot)
            msg_info "Configuring systemd-boot..."
            
            for entry in "$VFIO_BOOT_ENTRIES_DIR"/*.conf; do
                [[ -f "$entry" ]] || continue
                
                # Skip fallback entries
                [[ "$entry" == *"fallback"* ]] && continue
                
                # Backup
                cp "$entry" "${entry}${BACKUP_SUFFIX}"
                
                # Check if params already exist
                if ! grep -q "vfio-pci.ids=" "$entry"; then
                    # Append to options line
                    sed -i "/^options/ s/$/ $kernel_params/" "$entry"
                    msg_success "Updated: $(basename "$entry")"
                else
                    msg_skip "$(basename "$entry")" "already configured"
                fi
            done
            ;;
            
        grub)
            msg_info "Configuring GRUB..."
            
            if [[ -f "$VFIO_GRUB_CONF" ]]; then
                cp "$VFIO_GRUB_CONF" "${VFIO_GRUB_CONF}${BACKUP_SUFFIX}"
                
                # Update GRUB_CMDLINE_LINUX_DEFAULT
                if grep -q "GRUB_CMDLINE_LINUX_DEFAULT" "$VFIO_GRUB_CONF"; then
                    if ! grep -q "vfio-pci.ids=" "$VFIO_GRUB_CONF"; then
                        sed -i "s/GRUB_CMDLINE_LINUX_DEFAULT=\"\(.*\)\"/GRUB_CMDLINE_LINUX_DEFAULT=\"\1 $kernel_params\"/" "$VFIO_GRUB_CONF"
                    fi
                fi
                
                msg_info "Regenerating GRUB config..."
                grub-mkconfig -o /boot/grub/grub.cfg >> "$DEBUG_LOG" 2>&1 && \
                    msg_success "GRUB updated" || msg_fail "GRUB update"
            fi
            ;;
            
        *)
            msg_warn "Manual bootloader configuration required"
            echo ""
            echo -e "    ${C_INFO}Add these kernel parameters:${NC}"
            echo -e "    ${C_HIGHLIGHT}$kernel_params${NC}"
            echo ""
            ;;
    esac
}

vfio_create_helpers() {
    print_subsection "Helper Scripts"
    
    local vfio_ids=$(IFS=,; echo "${VFIO_SELECTED_IDS[*]}")
    
    # Create verification script
    cat > /usr/local/bin/vfio-verify << VFIOVERIFY
#!/bin/bash
echo "VFIO Configuration Verification"
echo "================================"
echo ""

echo "Checking VFIO modules..."
for mod in vfio vfio_pci vfio_iommu_type1; do
    if lsmod | grep -q "^\$mod"; then
        echo "  âœ” \$mod loaded"
    else
        echo "  âœ– \$mod NOT loaded"
    fi
done
echo ""

echo "Checking device binding..."
for id in ${vfio_ids//,/ }; do
    echo "Device: \$id"
    lspci -nnk -d "\$id" | grep -E "driver in use|Kernel modules"
    echo ""
done

echo "VFIO device nodes:"
ls -la /dev/vfio/ 2>/dev/null || echo "  No VFIO devices found"
echo ""

echo "Kernel parameters:"
cat /proc/cmdline | tr ' ' '\n' | grep -E "iommu|vfio"
VFIOVERIFY
    
    chmod +x /usr/local/bin/vfio-verify
    msg_success "Created vfio-verify command"
}

vfio_show_summary() {
    print_subsection "Configuration Summary"
    
    local vfio_ids=$(IFS=,; echo "${VFIO_SELECTED_IDS[*]}")
    
    echo -e "    ${BOLD}Isolated Devices (${#VFIO_SELECTED_DEVICES[@]}):${NC}"
    for i in "${!VFIO_SELECTED_DEVICES[@]}"; do
        echo -e "      ${C_SUCCESS}âœ”${NC} ${VFIO_SELECTED_DEVICES[$i]} [${VFIO_SELECTED_IDS[$i]}]"
    done
    echo ""
    
    echo -e "    ${BOLD}Files Modified:${NC}"
    echo -e "      â€¢ /etc/modprobe.d/vfio.conf"
    echo -e "      â€¢ /etc/mkinitcpio.conf (or dracut)"
    echo -e "      â€¢ Bootloader entries"
    echo ""
    
    echo -e "    ${BOLD}After Reboot:${NC}"
    echo -e "      â€¢ Run ${C_HIGHLIGHT}vfio-verify${NC} to confirm configuration"
    echo -e "      â€¢ Run ${C_HIGHLIGHT}iommu-groups${NC} to view IOMMU topology"
    echo ""
    
    msg_warn "Reboot required to apply VFIO configuration"
}

#==============================================================================
# CPU ISOLATION MODULE
#==============================================================================
configure_cpu_isolation() {
    if ! check_root; then
        return 1
    fi
    
    print_small_banner "CPU Core Isolation Configuration"
    
    detect_system
    
    cpu_show_topology
    cpu_select_isolation_mode
    cpu_apply_configuration
    cpu_show_summary
    
    STATE[cpu_isolated]="true"
    STATE[reboot_required]="true"
    save_state
}

cpu_show_topology() {
    show_cpu_topology
}

cpu_select_isolation_mode() {
    print_subsection "Isolation Mode Selection"
    
    local total_threads=${CPU_INFO[threads]:-0}
    
    echo ""
    echo -e "    ${BOLD}Available Isolation Presets:${NC}"
    echo ""
    
    # Calculate presets based on CPU
    local host_threads=4
    local vm_threads=$((total_threads - host_threads))
    
    if [[ "${CPU_INFO[is_x3d]}" == "true" ]]; then
        # X3D optimized presets
        local half=$((total_threads / 2))
        
        echo -e "    ${C_HIGHLIGHT}1)${NC} ${BOLD}Gaming Optimized (X3D)${NC}"
        echo -e "       Host: First 2 cores of CCD1 (high frequency)"
        echo -e "       VM: All of CCD0 (V-Cache) for gaming VM"
        echo -e "       ${C_MUTED}Best for: Single gaming VM with maximum cache benefit${NC}"
        echo ""
        
        echo -e "    ${C_HIGHLIGHT}2)${NC} ${BOLD}Multi-VM Balanced${NC}"
        echo -e "       Host: 4 threads spread across CCDs"
        echo -e "       VM: Remaining $((total_threads - 4)) threads"
        echo -e "       ${C_MUTED}Best for: Multiple VMs or mixed workloads${NC}"
        echo ""
        
        echo -e "    ${C_HIGHLIGHT}3)${NC} ${BOLD}Host Priority${NC}"
        echo -e "       Host: 8 threads (CCD1)"
        echo -e "       VM: $half threads (CCD0)"
        echo -e "       ${C_MUTED}Best for: Heavy host workloads + VM${NC}"
        echo ""
    else
        echo -e "    ${C_HIGHLIGHT}1)${NC} ${BOLD}VM Priority${NC}"
        echo -e "       Host: 4 threads (cores 0-1)"
        echo -e "       VM: $vm_threads threads (cores 2+)"
        echo -e "       ${C_MUTED}Best for: Dedicated VM workloads${NC}"
        echo ""
        
        echo -e "    ${C_HIGHLIGHT}2)${NC} ${BOLD}Balanced${NC}"
        echo -e "       Host: $((total_threads / 4)) threads"
        echo -e "       VM: $((total_threads * 3 / 4)) threads"
        echo -e "       ${C_MUTED}Best for: Mixed host and VM usage${NC}"
        echo ""
        
        echo -e "    ${C_HIGHLIGHT}3)${NC} ${BOLD}Host Priority${NC}"
        echo -e "       Host: $((total_threads / 2)) threads"
        echo -e "       VM: $((total_threads / 2)) threads"
        echo -e "       ${C_MUTED}Best for: Heavy host workloads${NC}"
        echo ""
    fi
    
    echo -e "    ${C_HIGHLIGHT}4)${NC} ${BOLD}Custom${NC}"
    echo -e "       Manually specify cores for isolation"
    echo ""
    
    echo -e "    ${C_HIGHLIGHT}5)${NC} ${BOLD}View Current State${NC}"
    echo -e "       Show current CPU isolation status"
    echo ""
    
    read -rp "      Select preset [1-5]: " preset_choice
    
    case "$preset_choice" in
        1)
            if [[ "${CPU_INFO[is_x3d]}" == "true" ]]; then
                cpu_preset_x3d_gaming
            else
                cpu_preset_vm_priority
            fi
            ;;
        2)
            cpu_preset_balanced
            ;;
        3)
            cpu_preset_host_priority
            ;;
        4)
            cpu_preset_custom
            ;;
        5)
            cpu_show_current_state
            cpu_select_isolation_mode
            return
            ;;
        *)
            msg_warn "Invalid selection"
            cpu_select_isolation_mode
            return
            ;;
    esac
}

cpu_preset_x3d_gaming() {
    msg_info "Applying X3D Gaming Optimized preset..."
    
    local total=${CPU_INFO[threads]}
    local half=$((total / 2))
    
    # Host gets last 4 threads of CCD1
    HOST_CPUS=()
    for ((i=total-4; i<total; i+=1)); do
        HOST_CPUS+=($i)
    done
    
    # VM gets all of CCD0 (V-Cache)
    ISOLATED_CPUS=()
    for ((i=0; i<half; i+=1)); do
        ISOLATED_CPUS+=($i)
    done
    
    msg_success "Host CPUs: ${HOST_CPUS[*]}"
    msg_success "VM CPUs (V-Cache): ${ISOLATED_CPUS[*]}"
}

cpu_preset_vm_priority() {
    msg_info "Applying VM Priority preset..."
    
    local total=${CPU_INFO[threads]}
    
    # Host gets first 4 threads
    HOST_CPUS=(0 1)
    if [[ ${CPU_INFO[threads_per_core]} -eq 2 ]]; then
        # Add SMT siblings
        local cores=${CPU_INFO[cores]}
        HOST_CPUS+=(${cores} $((cores + 1)))
    else
        HOST_CPUS+=(2 3)
    fi
    
    # VM gets the rest
    ISOLATED_CPUS=()
    for ((i=0; i<total; i+=1)); do
        local is_host=false
        for h in "${HOST_CPUS[@]}"; do
            [[ $i -eq $h ]] && is_host=true
        done
        [[ "$is_host" == "false" ]] && ISOLATED_CPUS+=($i)
    done
    
    msg_success "Host CPUs: ${HOST_CPUS[*]}"
    msg_success "VM CPUs: ${ISOLATED_CPUS[*]}"
}

cpu_preset_balanced() {
    msg_info "Applying Balanced preset..."
    
    local total=${CPU_INFO[threads]}
    local host_count=$((total / 4))
    [[ $host_count -lt 4 ]] && host_count=4
    
    HOST_CPUS=()
    ISOLATED_CPUS=()
    
    for ((i=0; i<total; i+=1)); do
        if [[ $i -lt $host_count ]]; then
            HOST_CPUS+=($i)
        else
            ISOLATED_CPUS+=($i)
        fi
    done
    
    msg_success "Host CPUs: ${HOST_CPUS[*]}"
    msg_success "VM CPUs: ${ISOLATED_CPUS[*]}"
}

cpu_preset_host_priority() {
    msg_info "Applying Host Priority preset..."
    
    local total=${CPU_INFO[threads]}
    local host_count=$((total / 2))
    
    HOST_CPUS=()
    ISOLATED_CPUS=()
    
    for ((i=0; i<total; i+=1)); do
        if [[ $i -lt $host_count ]]; then
            HOST_CPUS+=($i)
        else
            ISOLATED_CPUS+=($i)
        fi
    done
    
    msg_success "Host CPUs: ${HOST_CPUS[*]}"
    msg_success "VM CPUs: ${ISOLATED_CPUS[*]}"
}

cpu_preset_custom() {
    msg_info "Custom CPU isolation"
    
    local total=${CPU_INFO[threads]}
    
    echo ""
    echo -e "    ${C_INFO}Available CPUs: 0-$((total-1))${NC}"
    echo ""
    
    read -rp "      Enter CPUs to ISOLATE for VMs (e.g., 2-15,18-31): " isolated_input
    
    ISOLATED_CPUS=()
    HOST_CPUS=()
    
    # Parse CPU list
    IFS=',' read -ra ranges <<< "$isolated_input"
    for range in "${ranges[@]}"; do
        if [[ "$range" =~ ^([0-9]+)-([0-9]+)$ ]]; then
            for ((i=${BASH_REMATCH[1]}; i<=${BASH_REMATCH[2]}; i+=1)); do
                ISOLATED_CPUS+=($i)
            done
        elif [[ "$range" =~ ^[0-9]+$ ]]; then
            ISOLATED_CPUS+=($range)
        fi
    done
    
    # Calculate host CPUs
    for ((i=0; i<total; i+=1)); do
        local is_isolated=false
        for iso in "${ISOLATED_CPUS[@]}"; do
            [[ $i -eq $iso ]] && is_isolated=true
        done
        [[ "$is_isolated" == "false" ]] && HOST_CPUS+=($i)
    done
    
    msg_success "Host CPUs: ${HOST_CPUS[*]}"
    msg_success "VM CPUs: ${ISOLATED_CPUS[*]}"
}

cpu_show_current_state() {
    print_subsection "Current CPU Isolation State"
    
    # Check kernel cmdline
    local cmdline=$(cat /proc/cmdline)
    
    if echo "$cmdline" | grep -q "isolcpus="; then
        local isolated=$(echo "$cmdline" | grep -oP 'isolcpus=\K[^ ]+')
        msg_info "Kernel isolcpus: $isolated"
    else
        msg_info "Kernel isolcpus: Not configured"
    fi
    
    # Check systemd affinity
    if grep -q "^CPUAffinity=" /etc/systemd/system.conf 2>/dev/null; then
        local affinity=$(grep "^CPUAffinity=" /etc/systemd/system.conf | cut -d'=' -f2)
        msg_info "systemd CPUAffinity: $affinity"
    else
        msg_info "systemd CPUAffinity: Not configured"
    fi
    
    echo ""
}

cpu_apply_configuration() {
    print_subsection "Applying Configuration"
    
    if [[ ${#ISOLATED_CPUS[@]} -eq 0 ]]; then
        msg_warn "No CPUs selected for isolation"
        return 1
    fi
    
    local isolated_list=$(IFS=,; echo "${ISOLATED_CPUS[*]}")
    local host_list=$(IFS=,; echo "${HOST_CPUS[*]}")
    
    # Configure kernel parameters
    cpu_configure_kernel_params "$isolated_list"
    
    # Configure systemd affinity
    cpu_configure_systemd "$host_list"
    
    # Create helper scripts
    cpu_create_helpers "$host_list" "$isolated_list"
    
    # Apply immediate changes (for processes that can be moved)
    cpu_apply_immediate "$host_list"
}

cpu_configure_kernel_params() {
    local isolated="$1"
    
    msg_info "Configuring kernel parameters..."
    
    local kernel_params="isolcpus=$isolated nohz_full=$isolated rcu_nocbs=$isolated"
    
    case "${SYSTEM_INFO[bootloader]}" in
        systemd-boot)
            for entry in /boot/loader/entries/*.conf; do
                [[ -f "$entry" ]] || continue
                [[ "$entry" == *"fallback"* ]] && continue
                
                cp "$entry" "${entry}${BACKUP_SUFFIX}"
                
                if ! grep -q "isolcpus=" "$entry"; then
                    sed -i "/^options/ s/$/ $kernel_params/" "$entry"
                    msg_success "Updated: $(basename "$entry")"
                else
                    # Update existing isolcpus
                    sed -i "s/isolcpus=[^ ]*/isolcpus=$isolated/" "$entry"
                    msg_success "Updated isolcpus in: $(basename "$entry")"
                fi
            done
            ;;
            
        grub)
            if [[ -f /etc/default/grub ]]; then
                cp /etc/default/grub "/etc/default/grub${BACKUP_SUFFIX}"
                
                if ! grep -q "isolcpus=" /etc/default/grub; then
                    sed -i "s/GRUB_CMDLINE_LINUX_DEFAULT=\"\(.*\)\"/GRUB_CMDLINE_LINUX_DEFAULT=\"\1 $kernel_params\"/" /etc/default/grub
                else
                    sed -i "s/isolcpus=[^ \"]*/isolcpus=$isolated/" /etc/default/grub
                fi
                
                grub-mkconfig -o /boot/grub/grub.cfg >> "$DEBUG_LOG" 2>&1
                msg_success "GRUB updated"
            fi
            ;;
            
        *)
            msg_warn "Manual kernel parameter update required"
            echo -e "    ${C_INFO}Add: $kernel_params${NC}"
            ;;
    esac
}

cpu_configure_systemd() {
    local host_cpus="$1"
    
    msg_info "Configuring systemd CPU affinity..."
    
    local conf="/etc/systemd/system.conf"
    
    if [[ -f "$conf" ]]; then
        cp "$conf" "${conf}${BACKUP_SUFFIX}"
        
        # Convert comma-separated to space-separated for systemd
        local host_spaces="${host_cpus//,/ }"
        
        if grep -q "^CPUAffinity=" "$conf"; then
            sed -i "s/^CPUAffinity=.*/CPUAffinity=$host_spaces/" "$conf"
        elif grep -q "^#CPUAffinity=" "$conf"; then
            sed -i "s/^#CPUAffinity=.*/CPUAffinity=$host_spaces/" "$conf"
        else
            echo "CPUAffinity=$host_spaces" >> "$conf"
        fi
        
        msg_success "systemd CPU affinity configured"
    fi
}

cpu_create_helpers() {
    local host_cpus="$1"
    local isolated_cpus="$2"
    
    # Create cpu-isolate helper
    cat > /usr/local/bin/cpu-isolate << CPUHELPER
#!/bin/bash
HOST_CPUS="$host_cpus"
ISOLATED_CPUS="$isolated_cpus"

case "\$1" in
    on)
        echo "Enabling CPU isolation..."
        for pid in \$(ps -eo pid --no-headers); do
            taskset -cp "\$HOST_CPUS" \$pid 2>/dev/null
        done
        echo "Isolation enabled - processes moved to host cores"
        ;;
    off)
        echo "Disabling CPU isolation..."
        for pid in \$(ps -eo pid --no-headers); do
            taskset -cp "0-\$(($(nproc)-1))" \$pid 2>/dev/null
        done
        echo "Isolation disabled - all cores available"
        ;;
    status)
        echo "CPU Isolation Status"
        echo "===================="
        echo "Host CPUs: \$HOST_CPUS"
        echo "Isolated CPUs: \$ISOLATED_CPUS"
        echo ""
        echo "Kernel isolcpus:"
        cat /proc/cmdline | tr ' ' '\n' | grep isolcpus
        echo ""
        echo "systemd affinity:"
        grep "^CPUAffinity" /etc/systemd/system.conf 2>/dev/null || echo "Not set"
        ;;
    *)
        echo "Usage: cpu-isolate {on|off|status}"
        ;;
esac
CPUHELPER
    
    chmod +x /usr/local/bin/cpu-isolate
    msg_success "Created cpu-isolate command"
    
    # Create cpu-verify helper
    cat > /usr/local/bin/cpu-verify << 'CPUVERIFY'
#!/bin/bash
echo "CPU Isolation Verification"
echo "=========================="
echo ""

echo "Kernel parameters:"
cat /proc/cmdline | tr ' ' '\n' | grep -E "isolcpus|nohz_full|rcu_nocbs"
echo ""

echo "systemd affinity:"
grep "CPUAffinity" /etc/systemd/system.conf 2>/dev/null
echo ""

echo "Current process distribution:"
for cpu in $(seq 0 $(($(nproc)-1))); do
    count=$(ps -eo psr | grep -c "^ *$cpu$" 2>/dev/null || echo 0)
    printf "CPU %2d: %4d processes\n" $cpu $count
done
CPUVERIFY
    
    chmod +x /usr/local/bin/cpu-verify
    msg_success "Created cpu-verify command"
}

cpu_apply_immediate() {
    local host_cpus="$1"
    
    msg_info "Applying immediate CPU affinity changes..."
    
    # Reload systemd
    systemctl daemon-reexec >> "$DEBUG_LOG" 2>&1
    
    # Move existing processes
    local moved=0
    local failed=0
    
    for pid in $(ps -eo pid --no-headers 2>/dev/null); do
        if taskset -cp "$host_cpus" "$pid" 2>/dev/null; then
            moved=$((moved + 1))
        else
            failed=$((failed + 1))
        fi
    done
    
    msg_success "Moved $moved processes (${failed} failed - expected for kernel threads)"
}

cpu_show_summary() {
    print_subsection "CPU Isolation Summary"
    
    echo -e "    ${BOLD}Configuration Applied:${NC}"
    echo -e "      Host CPUs: ${HOST_CPUS[*]}"
    echo -e "      Isolated CPUs: ${ISOLATED_CPUS[*]}"
    echo ""
    
    echo -e "    ${BOLD}Helper Commands:${NC}"
    echo -e "      ${C_HIGHLIGHT}cpu-isolate status${NC} - Show current isolation state"
    echo -e "      ${C_HIGHLIGHT}cpu-verify${NC}         - Verify configuration"
    echo ""
    
    echo -e "    ${BOLD}VM CPU Pinning Example (libvirt XML):${NC}"
    echo -e "      <vcpu placement='static'>${#ISOLATED_CPUS[@]}</vcpu>"
    echo -e "      <cputune>"
    local idx=0
    for cpu in "${ISOLATED_CPUS[@]:0:4}"; do
        echo -e "        <vcpupin vcpu='$idx' cpuset='$cpu'/>"
        idx=$((idx + 1))
    done
    [[ ${#ISOLATED_CPUS[@]} -gt 4 ]] && echo -e "        <!-- ... more pins ... -->"
    echo -e "      </cputune>"
    echo ""
    
    msg_warn "Reboot required for kernel-level isolation (isolcpus)"
    msg_info "Immediate systemd affinity changes are active now"
}

#==============================================================================
# VERIFICATION MODULE
#==============================================================================
run_verification() {
    print_small_banner "System Verification"
    
    detect_system
    
    local passed=0
    local failed=0
    local warned=0
    
    print_subsection "Service Status"
    
    local services=("libvirtd" "virtqemud" "cockpit.socket" "firewalld" "tuned")
    for svc in "${services[@]}"; do
        if systemctl is-active --quiet "$svc" 2>/dev/null; then
            msg_success "$svc is running"
            passed=$((passed + 1))
        elif systemctl is-enabled --quiet "$svc" 2>/dev/null; then
            msg_warn "$svc is enabled but not running"
            warned=$((warned + 1))
        else
            msg_skip "$svc" "not configured"
        fi
    done
    
    print_subsection "Virtualization"
    
    if [[ -e /dev/kvm ]]; then
        msg_success "KVM available"
        passed=$((passed + 1))
    else
        msg_fail "KVM not available"
        failed=$((failed + 1))
    fi
    
    if [[ "${SYSTEM_INFO[iommu_enabled]}" == "true" ]]; then
        msg_success "IOMMU enabled (${SYSTEM_INFO[iommu_groups]} groups)"
        passed=$((passed + 1))
    else
        msg_warn "IOMMU not enabled"
        warned=$((warned + 1))
    fi
    
    print_subsection "VFIO Status"
    
    local vfio_modules=("vfio" "vfio_pci" "vfio_iommu_type1")
    for mod in "${vfio_modules[@]}"; do
        if lsmod | grep -q "^$mod"; then
            msg_success "$mod module loaded"
            passed=$((passed + 1))
        else
            msg_info "$mod not loaded (normal if not configured)"
        fi
    done
    
    if [[ -d /dev/vfio ]]; then
        local vfio_count=$(ls /dev/vfio/ 2>/dev/null | wc -l)
        msg_success "VFIO devices: $vfio_count"
    fi
    
    print_subsection "CPU Isolation"
    
    local cmdline=$(cat /proc/cmdline)
    
    if echo "$cmdline" | grep -q "isolcpus="; then
        local isolated=$(echo "$cmdline" | grep -oP 'isolcpus=\K[^ ]+')
        msg_success "CPU isolation configured: $isolated"
        passed=$((passed + 1))
    else
        msg_info "No kernel CPU isolation configured"
    fi
    
    if grep -q "^CPUAffinity=" /etc/systemd/system.conf 2>/dev/null; then
        local affinity=$(grep "^CPUAffinity=" /etc/systemd/system.conf | cut -d'=' -f2)
        msg_success "systemd affinity: $affinity"
        passed=$((passed + 1))
    else
        msg_info "No systemd CPU affinity configured"
    fi
    
    print_subsection "User Permissions"
    
    if groups "$REAL_USER" | grep -q "libvirt"; then
        msg_success "$REAL_USER in libvirt group"
        passed=$((passed + 1))
    else
        msg_warn "$REAL_USER not in libvirt group"
        warned=$((warned + 1))
    fi
    
    if groups "$REAL_USER" | grep -q "kvm"; then
        msg_success "$REAL_USER in kvm group"
        passed=$((passed + 1))
    else
        msg_warn "$REAL_USER not in kvm group"
        warned=$((warned + 1))
    fi
    
    print_subsection "Verification Summary"
    
    echo ""
    echo -e "    ${C_SUCCESS}Passed:${NC}  $passed"
    echo -e "    ${C_WARNING}Warnings:${NC} $warned"
    echo -e "    ${C_ERROR}Failed:${NC}  $failed"
    echo ""
    
    if [[ $failed -eq 0 ]]; then
        msg_success "System verification passed"
    else
        msg_warn "Some checks failed - review above"
    fi
    
    press_enter
}

#==============================================================================
# DIAGNOSTICS MODULE
#==============================================================================
run_diagnostics() {
    print_small_banner "Troubleshooting & Diagnostics"
    
    echo -e "${C_HEADER}    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                    ${WHITE}DIAGNOSTIC OPTIONS${NC}                                    ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}  ${C_HIGHLIGHT}Common Issues${NC}                                                            ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}1)${NC} GPU Passthrough Not Working                                        ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}2)${NC} VM Won't Start                                                     ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}3)${NC} Poor VM Performance                                                ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}4)${NC} Secure Boot / TPM Issues                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}  ${C_HIGHLIGHT}Diagnostic Tools${NC}                                                        ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}5)${NC} Generate Full Diagnostic Report                                    ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}6)${NC} Check System Logs                                                  ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}7)${NC} View IOMMU Groups                                                  ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}  ${C_HIGHLIGHT}Recovery${NC}                                                                ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}8)${NC} Reset VFIO Configuration                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}9)${NC} Reset CPU Isolation                                                ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}b)${NC} Back                                                                ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    echo ""
    
    read -rp "      Select option: " choice
    
    case "$choice" in
        1) diagnose_gpu_passthrough ;;
        2) diagnose_vm_start ;;
        3) diagnose_performance ;;
        4) diagnose_secureboot ;;
        5) generate_diagnostic_report ;;
        6) view_logs ;;
        7) analyze_iommu_groups; press_enter ;;
        8) reset_vfio ;;
        9) reset_cpu_isolation ;;
        b|B) return ;;
        *) msg_warn "Invalid option"; sleep 1 ;;
    esac
    
    run_diagnostics
}

diagnose_gpu_passthrough() {
    print_subsection "GPU Passthrough Diagnostics"
    
    detect_system
    
    echo -e "    ${BOLD}Common Causes:${NC}"
    echo "      1. GPU not bound to vfio-pci driver"
    echo "      2. IOMMU group contains other devices"
    echo "      3. GPU ROM/VBIOS issues"
    echo "      4. Missing kernel parameters"
    echo "      5. Driver conflicts"
    echo ""
    
    # Check IOMMU
    if [[ "${SYSTEM_INFO[iommu_enabled]}" != "true" ]]; then
        msg_fail "IOMMU not enabled - enable in BIOS and add kernel parameter"
    else
        msg_success "IOMMU enabled"
    fi
    
    # Check VFIO
    if lsmod | grep -q "vfio_pci"; then
        msg_success "vfio_pci module loaded"
    else
        msg_warn "vfio_pci not loaded"
    fi
    
    # Check for conflicting drivers
    if lsmod | grep -q "^nvidia"; then
        msg_warn "NVIDIA driver loaded - may conflict with VFIO passthrough"
    fi
    
    if lsmod | grep -q "^nouveau"; then
        msg_warn "Nouveau driver loaded - may conflict with VFIO"
    fi
    
    # Show GPU binding
    echo ""
    msg_info "Current GPU driver binding:"
    lspci -nnk | grep -A3 "VGA\|3D controller" | head -20
    
    press_enter
}

diagnose_vm_start() {
    print_subsection "VM Start Failure Diagnostics"
    
    echo -e "    ${BOLD}Common Causes:${NC}"
    echo "      1. Insufficient permissions"
    echo "      2. Missing UEFI firmware"
    echo "      3. Storage path issues"
    echo "      4. Network configuration"
    echo "      5. TPM/Secure Boot requirements"
    echo ""
    
    # Check libvirt
    if command -v virsh &>/dev/null; then
        if virsh list &>/dev/null 2>&1; then
            msg_success "libvirt connection OK"
        else
            msg_fail "Cannot connect to libvirt"
        fi
    fi
    
    # Show recent errors
    echo ""
    msg_info "Recent VM-related errors:"
    journalctl -u libvirtd --no-pager -n 20 --priority=err 2>/dev/null | tail -10
    
    press_enter
}

diagnose_performance() {
    print_subsection "Performance Diagnostics"
    
    detect_system
    
    # CPU isolation check
    if grep -q "isolcpus=" /proc/cmdline; then
        msg_success "CPU isolation configured"
    else
        msg_warn "No CPU isolation - consider configuring for better VM performance"
    fi
    
    # Hugepages
    local hugepages=$(grep HugePages_Total /proc/meminfo | awk '{print $2}')
    if [[ $hugepages -gt 0 ]]; then
        msg_success "Hugepages configured: $hugepages"
    else
        msg_info "Hugepages not configured - can improve large VM performance"
    fi
    
    # TuneD profile
    if command -v tuned-adm &>/dev/null; then
        local profile=$(tuned-adm active 2>/dev/null | awk '{print $NF}')
        if [[ "$profile" == "virtual-host" ]]; then
            msg_success "TuneD profile: virtual-host"
        else
            msg_info "TuneD profile: $profile (consider virtual-host)"
        fi
    fi
    
    echo ""
    msg_info "Recommendations:"
    echo "      â€¢ Use CPU pinning for dedicated VM cores"
    echo "      â€¢ Enable hugepages for large VMs"
    echo "      â€¢ Use virtio drivers in guest"
    echo "      â€¢ Consider Looking Glass for GPU passthrough"
    
    press_enter
}

diagnose_secureboot() {
    print_subsection "Secure Boot Diagnostics"
    
    detect_system
    
    echo -e "    ${BOLD}Secure Boot Status:${NC}"
    echo ""
    
    if [[ "${SYSTEM_INFO[secureboot]}" == "enabled" ]]; then
        msg_success "Secure Boot: Enabled"
    else
        msg_info "Secure Boot: ${SYSTEM_INFO[secureboot]}"
    fi
    
    if [[ "${SYSTEM_INFO[has_sbctl]}" == "true" ]]; then
        msg_success "sbctl installed"
        
        echo ""
        msg_info "sbctl status:"
        sbctl status 2>/dev/null
    else
        msg_info "sbctl not installed"
    fi
    
    echo ""
    msg_info "TPM Status:"
    if [[ "${SYSTEM_INFO[has_tpm]}" == "true" ]]; then
        msg_success "TPM detected"
    else
        msg_info "TPM not detected"
    fi
    
    press_enter
}

generate_diagnostic_report() {
    print_subsection "Generating Diagnostic Report"
    
    local report="$REAL_HOME/mios-diagnostic-$TIMESTAMP.txt"
    
    msg_info "Collecting system information..."
    
    {
        echo "================================================================================"
        echo " MiOS-Build DIAGNOSTIC REPORT"
        echo " Generated: $(date)"
        echo " Session: $SESSION_ID"
        echo "================================================================================"
        echo ""
        
        echo "=== System Info ==="
        uname -a
        echo ""
        cat /etc/os-release 2>/dev/null
        echo ""
        
        echo "=== CPU ==="
        lscpu | head -20
        echo ""
        
        echo "=== Memory ==="
        free -h
        echo ""
        
        echo "=== GPU ==="
        lspci | grep -iE "VGA|3D|Display"
        echo ""
        
        echo "=== Kernel Parameters ==="
        cat /proc/cmdline
        echo ""
        
        echo "=== IOMMU Groups ==="
        for g in $(find /sys/kernel/iommu_groups/* -maxdepth 0 -type d 2>/dev/null | sort -V); do
            echo "Group ${g##*/}:"
            for d in "$g"/devices/*; do
                echo "  $(lspci -nns ${d##*/} 2>/dev/null)"
            done
        done
        echo ""
        
        echo "=== Loaded Modules ==="
        lsmod | grep -E "vfio|kvm|nvidia|nouveau|amdgpu"
        echo ""
        
        echo "=== Services ==="
        systemctl status libvirtd virtqemud cockpit firewalld 2>/dev/null | head -50
        echo ""
        
        echo "=== Recent Errors ==="
        journalctl -p err -n 50 --no-pager 2>/dev/null
        
    } > "$report"
    
    # Fix ownership
    chown "$REAL_USER:$(id -gn "$REAL_USER")" "$report" 2>/dev/null
    
    msg_success "Report saved: $report"
    press_enter
}

view_logs() {
    print_subsection "Log Viewer"
    
    echo "      1) MiOS-Build session logs"
    echo "      2) libvirt logs"
    echo "      3) System journal (errors)"
    echo "      4) QEMU logs"
    echo ""
    
    read -rp "      Select [1-4]: " choice
    
    case "$choice" in
        1)
            if [[ -d "$MIOS_LOG_DIR" ]]; then
                ls -lt "$MIOS_LOG_DIR"/*.log 2>/dev/null | head -10
                echo ""
                read -rp "      View latest? [y/N]: " view
                if [[ "$view" =~ ^[Yy] ]]; then
                    local latest=$(ls -t "$MIOS_LOG_DIR"/*.log 2>/dev/null | head -1)
                    [[ -f "$latest" ]] && less "$latest"
                fi
            else
                msg_info "No MiOS-Build logs yet"
            fi
            ;;
        2)
            [[ -f /var/log/libvirt/libvirtd.log ]] && less /var/log/libvirt/libvirtd.log || msg_info "No libvirt log"
            ;;
        3)
            journalctl -p err -n 100 --no-pager | less
            ;;
        4)
            ls -la /var/log/libvirt/qemu/ 2>/dev/null || msg_info "No QEMU logs"
            ;;
    esac
    
    press_enter
}

reset_vfio() {
    print_subsection "Reset VFIO Configuration"
    
    msg_warn "This will remove VFIO configuration"
    
    if ! ask_yes_no "Proceed?"; then
        return
    fi
    
    if [[ -f /etc/modprobe.d/vfio.conf ]]; then
        mv /etc/modprobe.d/vfio.conf "/etc/modprobe.d/vfio.conf.disabled-$TIMESTAMP"
        msg_success "Disabled vfio.conf"
    fi
    
    STATE[vfio_configured]="false"
    STATE[reboot_required]="true"
    save_state
    
    msg_warn "Reboot required to complete reset"
    press_enter
}

reset_cpu_isolation() {
    print_subsection "Reset CPU Isolation"
    
    msg_warn "This will remove CPU isolation settings"
    
    if ! ask_yes_no "Proceed?"; then
        return
    fi
    
    # Disable systemd affinity
    if grep -q "^CPUAffinity=" /etc/systemd/system.conf 2>/dev/null; then
        sed -i 's/^CPUAffinity=/#CPUAffinity=/' /etc/systemd/system.conf
        msg_success "Disabled systemd CPU affinity"
    fi
    
    STATE[cpu_isolated]="false"
    STATE[reboot_required]="true"
    save_state
    
    msg_warn "Remove isolcpus from kernel parameters manually"
    msg_warn "Then reboot to complete reset"
    press_enter
}

#==============================================================================
# VM CPU PIN MANAGER MODULE
#==============================================================================
manage_vm_cpu_pins() {
    if ! check_root; then
        return 1
    fi
    
    print_small_banner "VM CPU Pin Manager"
    
    detect_system
    
    # Check for libvirt
    if ! command -v virsh &>/dev/null; then
        msg_fail "virsh not found - install libvirt first"
        return 1
    fi
    
    while true; do
        vm_pin_show_menu
        read -rp "      Select option: " choice
        
        case "$choice" in
            1) vm_pin_list_vms ;;
            2) vm_pin_configure_vm ;;
            3) vm_pin_show_topology ;;
            4) vm_pin_install_hooks ;;
            5) vm_pin_show_current ;;
            6) vm_pin_generate_xml ;;
            b|B) return ;;
            *) msg_warn "Invalid option" ;;
        esac
    done
}

vm_pin_show_menu() {
    echo ""
    echo -e "${C_HEADER}    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                    ${WHITE}VM CPU PIN MANAGER${NC}                                    ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}1)${NC} List VMs and Current Pinning                                      ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}2)${NC} Configure VM CPU Pinning                                          ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}3)${NC} Show CPU Topology                                                 ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}4)${NC} Install Libvirt Hooks                                             ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}5)${NC} Show Current Hook Configuration                                   ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}6)${NC} Generate XML Snippet                                              ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}b)${NC} Back                                                               ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
}

vm_pin_list_vms() {
    print_subsection "Virtual Machines"
    
    local vms=$(virsh list --all --name 2>/dev/null | grep -v "^$")
    
    if [[ -z "$vms" ]]; then
        msg_info "No VMs defined"
        press_enter
        return
    fi
    
    echo -e "${C_HEADER}    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—${NC}"
    printf "${C_HEADER}    â•‘${NC} %-20s â”‚ %-10s â”‚ %-8s â”‚ %-20s ${C_HEADER}â•‘${NC}\n" "VM Name" "State" "vCPUs" "CPU Pinning"
    echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    
    while IFS= read -r vm; do
        [[ -z "$vm" ]] && continue
        
        local state=$(virsh domstate "$vm" 2>/dev/null | head -1)
        local vcpus=$(virsh vcpucount "$vm" --current 2>/dev/null || echo "?")
        local pinning=$(virsh vcpupin "$vm" 2>/dev/null | grep "^ *[0-9]" | head -1 | awk '{print $2}' || echo "none")
        
        [[ "$pinning" == "0-"* ]] && pinning="all cores"
        
        local state_color="$C_MUTED"
        [[ "$state" == "running" ]] && state_color="$C_SUCCESS"
        [[ "$state" == "shut off" ]] && state_color="$C_WARNING"
        
        printf "${C_HEADER}    â•‘${NC} %-20s â”‚ ${state_color}%-10s${NC} â”‚ %-8s â”‚ %-20s ${C_HEADER}â•‘${NC}\n" \
            "$vm" "$state" "$vcpus" "$pinning"
    done <<< "$vms"
    
    echo -e "${C_HEADER}    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    
    press_enter
}

vm_pin_configure_vm() {
    print_subsection "Configure VM CPU Pinning"
    
    local vms=$(virsh list --all --name 2>/dev/null | grep -v "^$")
    
    if [[ -z "$vms" ]]; then
        msg_info "No VMs defined"
        press_enter
        return
    fi
    
    echo ""
    echo -e "    ${BOLD}Available VMs:${NC}"
    local i=1
    local vm_array=()
    while IFS= read -r vm; do
        [[ -z "$vm" ]] && continue
        vm_array+=("$vm")
        local state=$(virsh domstate "$vm" 2>/dev/null | head -1)
        echo -e "      ${C_HIGHLIGHT}$i)${NC} $vm ${C_MUTED}($state)${NC}"
        i=$((i + 1))
    done <<< "$vms"
    
    echo ""
    read -rp "      Select VM [1-$((i-1))]: " vm_choice
    
    if ! [[ "$vm_choice" =~ ^[0-9]+$ ]] || [[ $vm_choice -lt 1 ]] || [[ $vm_choice -gt $((i-1)) ]]; then
        msg_warn "Invalid selection"
        return
    fi
    
    local selected_vm="${vm_array[$((vm_choice-1))]}"
    local vcpu_count=$(virsh vcpucount "$selected_vm" --current 2>/dev/null || echo "0")
    
    msg_info "Configuring: $selected_vm ($vcpu_count vCPUs)"
    echo ""
    
    # Show CPU topology
    show_cpu_topology
    
    echo ""
    echo -e "    ${BOLD}Pinning Options:${NC}"
    echo -e "      ${C_HIGHLIGHT}1)${NC} Auto-pin (sequential from isolated cores)"
    echo -e "      ${C_HIGHLIGHT}2)${NC} X3D Gaming (V-Cache CCD0)"
    echo -e "      ${C_HIGHLIGHT}3)${NC} Manual specification"
    echo ""
    
    read -rp "      Select option [1-3]: " pin_option
    
    local pin_cpus=()
    
    case "$pin_option" in
        1)
            # Use isolated CPUs if configured
            if [[ ${#ISOLATED_CPUS[@]} -gt 0 ]]; then
                for ((i=0; i<vcpu_count && i<${#ISOLATED_CPUS[@]}; i+=1)); do
                    pin_cpus+=("${ISOLATED_CPUS[$i]}")
                done
            else
                # Default: start from CPU 2
                for ((i=0; i<vcpu_count; i+=1)); do
                    pin_cpus+=($((i + 2)))
                done
            fi
            ;;
        2)
            # X3D: Use CCD0 (first half of CPUs)
            local half=$((${CPU_INFO[threads]:-32} / 2))
            for ((i=0; i<vcpu_count && i<half; i+=1)); do
                pin_cpus+=($i)
            done
            ;;
        3)
            echo ""
            read -rp "      Enter CPU list for $vcpu_count vCPUs (e.g., 2,3,4,5): " manual_cpus
            IFS=',' read -ra pin_cpus <<< "$manual_cpus"
            ;;
        *)
            msg_warn "Invalid option"
            return
            ;;
    esac
    
    if [[ ${#pin_cpus[@]} -lt $vcpu_count ]]; then
        msg_warn "Not enough CPUs specified (${#pin_cpus[@]} < $vcpu_count)"
        return
    fi
    
    # Apply pinning
    msg_info "Applying CPU pinning..."
    
    for ((i=0; i<vcpu_count; i+=1)); do
        if virsh vcpupin "$selected_vm" $i ${pin_cpus[$i]} --config >> "$DEBUG_LOG" 2>&1; then
            msg_success "vCPU $i â†’ CPU ${pin_cpus[$i]}"
        else
            msg_fail "Failed to pin vCPU $i"
        fi
    done
    
    # Configure emulator pinning (use host CPUs)
    if [[ ${#HOST_CPUS[@]} -gt 0 ]]; then
        local emulator_cpus=$(IFS=,; echo "${HOST_CPUS[*]}")
        virsh emulatorpin "$selected_vm" "$emulator_cpus" --config >> "$DEBUG_LOG" 2>&1
        msg_success "Emulator pinned to host CPUs: $emulator_cpus"
    fi
    
    msg_success "CPU pinning configured for $selected_vm"
    press_enter
}

vm_pin_show_topology() {
    show_cpu_topology
    press_enter
}

vm_pin_install_hooks() {
    print_subsection "Install Libvirt Hooks"
    
    local hooks_dir="/etc/libvirt/hooks"
    mkdir -p "$hooks_dir"
    
    # Create QEMU hook
    cat > "$hooks_dir/qemu" << 'QEMUHOOK'
#!/bin/bash
#
# MiOS-Build QEMU Hook
# Manages CPU isolation when VMs start/stop
#

VM_NAME="$1"
OPERATION="$2"
SUBOPERATION="$3"

LOG_FILE="/var/log/mios/hook-$VM_NAME.log"
mkdir -p /var/log/mios

log() {
    echo "[$(date '+%H:%M:%S')] $*" >> "$LOG_FILE"
}

# Read VM-specific config if exists
VM_CONFIG="/etc/libvirt/hooks/qemu.d/$VM_NAME.conf"
if [[ -f "$VM_CONFIG" ]]; then
    source "$VM_CONFIG"
fi

# Default CPU sets (can be overridden in VM config)
HOST_CPUS="${HOST_CPUS:-0,1}"
VM_CPUS="${VM_CPUS:-2-31}"

case "$OPERATION" in
    prepare)
        if [[ "$SUBOPERATION" == "begin" ]]; then
            log "Preparing for VM start: $VM_NAME"
            
            # Move system processes to host CPUs
            if command -v systemctl &>/dev/null; then
                systemctl set-property --runtime -- system.slice AllowedCPUs="$HOST_CPUS"
                systemctl set-property --runtime -- user.slice AllowedCPUs="$HOST_CPUS"
                systemctl set-property --runtime -- init.scope AllowedCPUs="$HOST_CPUS"
            fi
            
            log "Isolated CPUs for VM: $VM_CPUS"
        fi
        ;;
        
    started)
        log "VM started: $VM_NAME"
        ;;
        
    release)
        if [[ "$SUBOPERATION" == "end" ]]; then
            log "VM stopped: $VM_NAME"
            
            # Check if other VMs are running
            RUNNING_VMS=$(virsh list --state-running --name 2>/dev/null | grep -v "^$" | wc -l)
            
            if [[ $RUNNING_VMS -eq 0 ]]; then
                log "No VMs running, restoring full CPU access"
                
                # Restore full CPU access
                TOTAL_CPUS=$(($(nproc) - 1))
                if command -v systemctl &>/dev/null; then
                    systemctl set-property --runtime -- system.slice AllowedCPUs="0-$TOTAL_CPUS"
                    systemctl set-property --runtime -- user.slice AllowedCPUs="0-$TOTAL_CPUS"
                    systemctl set-property --runtime -- init.scope AllowedCPUs="0-$TOTAL_CPUS"
                fi
            else
                log "Other VMs still running ($RUNNING_VMS), keeping isolation"
            fi
        fi
        ;;
esac

exit 0
QEMUHOOK
    
    chmod +x "$hooks_dir/qemu"
    msg_success "Created QEMU hook"
    
    # Create hooks.d directory
    mkdir -p "$hooks_dir/qemu.d"
    
    # Create example VM config
    cat > "$hooks_dir/qemu.d/example.conf.template" << 'VMCONF'
# VM-specific CPU configuration
# Copy this file to <vmname>.conf to customize

# CPUs reserved for host (comma-separated or range)
HOST_CPUS="0,1,16,17"

# CPUs for this VM (comma-separated or range)
VM_CPUS="2-15,18-31"

# Enable hugepages (requires setup)
# USE_HUGEPAGES=1

# Governor to set when VM starts
# CPU_GOVERNOR="performance"
VMCONF
    
    msg_success "Created hook configuration template"
    
    # Restart libvirtd to load hooks
    if systemctl is-active --quiet libvirtd; then
        systemctl restart libvirtd >> "$DEBUG_LOG" 2>&1
        msg_success "Restarted libvirtd"
    fi
    
    STATE[vm_hooks_configured]="true"
    save_state
    
    echo ""
    msg_info "Hook location: $hooks_dir/qemu"
    msg_info "VM configs: $hooks_dir/qemu.d/<vmname>.conf"
    
    press_enter
}

vm_pin_show_current() {
    print_subsection "Current Hook Configuration"
    
    local hooks_dir="/etc/libvirt/hooks"
    
    if [[ -f "$hooks_dir/qemu" ]]; then
        msg_success "QEMU hook installed"
        echo ""
        msg_info "VM-specific configs:"
        
        if [[ -d "$hooks_dir/qemu.d" ]]; then
            local configs=$(ls "$hooks_dir/qemu.d"/*.conf 2>/dev/null | grep -v template)
            if [[ -n "$configs" ]]; then
                for conf in $configs; do
                    echo -e "      â€¢ $(basename "$conf" .conf)"
                done
            else
                echo -e "      ${C_MUTED}No VM-specific configs${NC}"
            fi
        fi
    else
        msg_info "QEMU hook not installed"
    fi
    
    press_enter
}

vm_pin_generate_xml() {
    print_subsection "Generate CPU Pinning XML"
    
    echo ""
    read -rp "      Number of vCPUs: " vcpu_count
    read -rp "      Starting CPU (e.g., 2): " start_cpu
    
    if ! [[ "$vcpu_count" =~ ^[0-9]+$ ]] || ! [[ "$start_cpu" =~ ^[0-9]+$ ]]; then
        msg_warn "Invalid input"
        return
    fi
    
    echo ""
    echo -e "    ${BOLD}XML Snippet:${NC}"
    echo ""
    echo "    <!-- Add to <domain> section -->"
    echo "    <vcpu placement='static'>$vcpu_count</vcpu>"
    echo "    <cputune>"
    
    for ((i=0; i<vcpu_count; i+=1)); do
        echo "      <vcpupin vcpu='$i' cpuset='$((start_cpu + i))'/>"
    done
    
    # Emulator pin (first 2 host CPUs)
    echo "      <emulatorpin cpuset='0,1'/>"
    echo "    </cputune>"
    echo ""
    echo "    <!-- Optional: CPU topology for better guest scheduling -->"
    echo "    <cpu mode='host-passthrough' check='none' migratable='on'>"
    
    if [[ $vcpu_count -ge 4 ]]; then
        local cores=$((vcpu_count / 2))
        echo "      <topology sockets='1' dies='1' cores='$cores' threads='2'/>"
    else
        echo "      <topology sockets='1' dies='1' cores='$vcpu_count' threads='1'/>"
    fi
    
    echo "    </cpu>"
    echo ""
    
    press_enter
}

#==============================================================================
# QUICK ASSESSMENT MODULE (Built-in)
#==============================================================================
run_quick_assessment() {
    print_small_banner "Quick System Assessment"
    
    detect_system
    
    print_subsection "System Overview"
    show_system_summary
    
    print_subsection "Virtualization Readiness"
    
    local score=0
    local max_score=10
    
    # CPU virtualization
    if [[ "${CPU_INFO[virt_ext]}" != "none" ]]; then
        msg_success "CPU virtualization extensions (${CPU_INFO[virt_ext]})"
        ((score+=2))
    else
        msg_fail "No CPU virtualization extensions"
    fi
    
    # KVM
    if [[ "${SYSTEM_INFO[kvm_available]}" == "true" ]]; then
        msg_success "KVM available"
        ((score+=2))
    else
        msg_fail "KVM not available"
    fi
    
    # IOMMU
    if [[ "${SYSTEM_INFO[iommu_enabled]}" == "true" ]]; then
        msg_success "IOMMU enabled (${SYSTEM_INFO[iommu_groups]} groups)"
        ((score+=2))
    else
        msg_warn "IOMMU not enabled"
    fi
    
    # GPU for passthrough
    if [[ "${GPU_INFO[gpu_count]}" -gt 1 ]]; then
        msg_success "Multiple GPUs (${GPU_INFO[gpu_count]}) - passthrough possible"
        ((score+=2))
    elif [[ "${GPU_INFO[gpu_count]}" -eq 1 ]]; then
        msg_info "Single GPU - passthrough requires careful config"
        ((score+=1))
    fi
    
    # TPM
    if [[ "${SYSTEM_INFO[has_tpm]}" == "true" ]]; then
        msg_success "TPM 2.0 available for Windows 11 VMs"
        ((score+=1))
    else
        msg_info "No TPM (Windows 11 needs vTPM)"
    fi
    
    # Memory
    if [[ ${SYSTEM_INFO[ram_gb]:-0} -ge 32 ]]; then
        msg_success "RAM: ${SYSTEM_INFO[ram_total]} (excellent for VMs)"
        ((score+=1))
    elif [[ ${SYSTEM_INFO[ram_gb]:-0} -ge 16 ]]; then
        msg_success "RAM: ${SYSTEM_INFO[ram_total]} (good for VMs)"
        ((score+=1))
    else
        msg_warn "RAM: ${SYSTEM_INFO[ram_total]} (may limit VM size)"
    fi
    
    print_subsection "Assessment Score"
    
    local percent=$((score * 100 / max_score))
    local rating="Poor"
    local rating_color="$C_ERROR"
    
    if [[ $percent -ge 90 ]]; then
        rating="Excellent"
        rating_color="$C_SUCCESS"
    elif [[ $percent -ge 70 ]]; then
        rating="Good"
        rating_color="$C_SUCCESS"
    elif [[ $percent -ge 50 ]]; then
        rating="Fair"
        rating_color="$C_WARNING"
    fi
    
    echo ""
    echo -e "    ${BOLD}Score: ${rating_color}$score/$max_score ($percent%)${NC}"
    echo -e "    ${BOLD}Rating: ${rating_color}$rating${NC}"
    echo ""
    
    if [[ $percent -lt 70 ]]; then
        print_subsection "Recommendations"
        
        if [[ "${SYSTEM_INFO[iommu_enabled]}" != "true" ]]; then
            echo "      â€¢ Enable IOMMU in BIOS (AMD-Vi or Intel VT-d)"
            echo "        Add kernel parameter: amd_iommu=on or intel_iommu=on"
        fi
        
        if [[ "${SYSTEM_INFO[kvm_available]}" != "true" ]]; then
            echo "      â€¢ Enable virtualization in BIOS (AMD-V or Intel VT-x)"
        fi
    fi
    
    press_enter
}

#==============================================================================
# MAIN MENU SYSTEM
#==============================================================================
show_main_menu() {
    print_banner
    
    # Status line
    echo -e "    ${C_MUTED}Session: $SESSION_ID${NC}"
    echo -e "    ${C_MUTED}State: ${STATE[install_phase]} | VFIO: ${STATE[vfio_configured]} | CPU: ${STATE[cpu_isolated]}${NC}"
    echo ""
    
    echo -e "${C_HEADER}    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                          ${WHITE}MAIN MENU${NC}                                       ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    
    # Assessment
    if [[ "${STATE[assessment_done]}" == "true" ]]; then
        echo -e "${C_HEADER}    â•‘${NC}   ${C_SUCCESS}âœ”${NC} ${WHITE}1)${NC} System Assessment              ${C_MUTED}[Completed]${NC}                  ${C_HEADER}â•‘${NC}"
    else
        echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}1)${NC} System Assessment              ${C_WARNING}[Recommended]${NC}                ${C_HEADER}â•‘${NC}"
    fi
    
    # Installation
    case "${STATE[install_phase]}" in
        completed)
            echo -e "${C_HEADER}    â•‘${NC}   ${C_SUCCESS}âœ”${NC} ${WHITE}2)${NC} MiOS-Build Installation          ${C_MUTED}[Completed]${NC}                  ${C_HEADER}â•‘${NC}"
            ;;
        in_progress)
            echo -e "${C_HEADER}    â•‘${NC}   ${C_WARNING}â—${NC} ${WHITE}2)${NC} MiOS-Build Installation          ${C_WARNING}[In Progress]${NC}                ${C_HEADER}â•‘${NC}"
            ;;
        *)
            echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}2)${NC} MiOS-Build Installation          ${C_INFO}[~20 minutes]${NC}                ${C_HEADER}â•‘${NC}"
            ;;
    esac
    
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    echo -e "${C_HEADER}    â•‘${NC}  ${BOLD}Post-Install Configuration${NC}                                               ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•Ÿâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•¢${NC}"
    
    # VFIO
    if [[ "${STATE[vfio_configured]}" == "true" ]]; then
        echo -e "${C_HEADER}    â•‘${NC}   ${C_SUCCESS}âœ”${NC} ${WHITE}3)${NC} VFIO GPU Passthrough           ${C_MUTED}[Configured]${NC}                 ${C_HEADER}â•‘${NC}"
    else
        echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}3)${NC} VFIO GPU Passthrough           ${C_INFO}[GPU isolation]${NC}               ${C_HEADER}â•‘${NC}"
    fi
    
    # CPU Isolation
    if [[ "${STATE[cpu_isolated]}" == "true" ]]; then
        echo -e "${C_HEADER}    â•‘${NC}   ${C_SUCCESS}âœ”${NC} ${WHITE}4)${NC} CPU Core Isolation             ${C_MUTED}[Configured]${NC}                 ${C_HEADER}â•‘${NC}"
    else
        echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}4)${NC} CPU Core Isolation             ${C_INFO}[Performance]${NC}                ${C_HEADER}â•‘${NC}"
    fi
    
    # VM CPU Pinning
    if [[ "${STATE[vm_hooks_configured]}" == "true" ]]; then
        echo -e "${C_HEADER}    â•‘${NC}   ${C_SUCCESS}âœ”${NC} ${WHITE}5)${NC} VM CPU Pin Manager             ${C_MUTED}[Hooks installed]${NC}            ${C_HEADER}â•‘${NC}"
    else
        echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}5)${NC} VM CPU Pin Manager             ${C_INFO}[Per-VM config]${NC}              ${C_HEADER}â•‘${NC}"
    fi
    
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    echo -e "${C_HEADER}    â•‘${NC}  ${BOLD}Tools & Diagnostics${NC}                                                      ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•Ÿâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â•¢${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}6)${NC} Verify Installation            ${C_MUTED}[Health check]${NC}               ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}7)${NC} Troubleshoot & Diagnose        ${C_MUTED}[Fix issues]${NC}                 ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}8)${NC} IOMMU Group Viewer             ${C_MUTED}[GPU analysis]${NC}               ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}s)${NC} System Status                  ${C_MUTED}[Quick view]${NC}                 ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}l)${NC} View Logs                      ${C_MUTED}[Session logs]${NC}               ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}h)${NC} Help & Documentation                                              ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}q)${NC} Quit                                                               ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
    echo -e "${C_HEADER}    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    
    if [[ "${STATE[reboot_required]}" == "true" ]]; then
        echo ""
        echo -e "    ${C_WARNING}âš  Reboot required to apply changes${NC}"
    fi
    
    echo ""
}

menu_assessment() {
    while true; do
        print_small_banner "System Assessment"
        
        echo -e "${C_HEADER}    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—${NC}"
        echo -e "${C_HEADER}    â•‘${NC}                    ${WHITE}ASSESSMENT OPTIONS${NC}                                    ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
        echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}1)${NC} Quick Assessment              ${C_INFO}[30 seconds]${NC}                 ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}        Fast virtualization readiness check                               ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}2)${NC} IOMMU Group Analysis          ${C_INFO}[1-2 minutes]${NC}                ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}        GPU passthrough compatibility                                      ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}3)${NC} CPU Topology Analysis         ${C_INFO}[30 seconds]${NC}                 ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}        Core layout, NUMA, CCD mapping                                     ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}4)${NC} Full System Profile           ${C_INFO}[2-3 minutes]${NC}                ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}        Complete hardware documentation                                    ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}b)${NC} Back to Main Menu                                                 ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
        echo ""
        
        read -rp "      Select option: " choice
        
        case "$choice" in
            1) run_quick_assessment ;;
            2) analyze_iommu_groups; press_enter ;;
            3) detect_system; show_cpu_topology; press_enter ;;
            4) run_full_profile ;;
            b|B) return ;;
            *) msg_warn "Invalid option"; sleep 1 ;;
        esac
    done
}

menu_installation() {
    while true; do
        print_small_banner "MiOS-Build Installation"
        
        # Prerequisites
        local root_ok=$([[ $EUID -eq 0 ]] && echo "true" || echo "false")
        local net_ok="false"
        ping -c1 -W2 archlinux.org &>/dev/null && net_ok="true"
        
        echo -e "${C_HEADER}    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—${NC}"
        echo -e "${C_HEADER}    â•‘${NC}                  ${WHITE}INSTALLATION OPTIONS${NC}                                    ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
        echo -e "${C_HEADER}    â•‘${NC}  ${C_MUTED}Prerequisites:${NC}                                                          ${C_HEADER}â•‘${NC}"
        
        if [[ "$root_ok" == "true" ]]; then
            echo -e "${C_HEADER}    â•‘${NC}    ${C_SUCCESS}âœ”${NC} Running as root                                               ${C_HEADER}â•‘${NC}"
        else
            echo -e "${C_HEADER}    â•‘${NC}    ${C_ERROR}âœ–${NC} Not running as root ${C_WARNING}(required)${NC}                             ${C_HEADER}â•‘${NC}"
        fi
        
        if [[ "$net_ok" == "true" ]]; then
            echo -e "${C_HEADER}    â•‘${NC}    ${C_SUCCESS}âœ”${NC} Network available                                              ${C_HEADER}â•‘${NC}"
        else
            echo -e "${C_HEADER}    â•‘${NC}    ${C_ERROR}âœ–${NC} No network ${C_WARNING}(required)${NC}                                       ${C_HEADER}â•‘${NC}"
        fi
        
        echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
        echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}1)${NC} Full Installation (Interactive)                                    ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}        All options with prompts                                           ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}2)${NC} Desktop Mode (GNOME + Virtualization)                               ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}        Full desktop with GUI tools                                        ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}3)${NC} Headless Mode (Server)                                              ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}        Cockpit + CLI tools only                                           ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}4)${NC} Minimal (Virtualization Only)                                       ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}        Just libvirt/QEMU                                                   ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}                                                                           ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}v)${NC} View Installation Phases                                            ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•‘${NC}     ${WHITE}b)${NC} Back to Main Menu                                                  ${C_HEADER}â•‘${NC}"
        echo -e "${C_HEADER}    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
        echo ""
        
        read -rp "      Select option: " choice
        
        case "$choice" in
            1)
                if [[ "$root_ok" == "true" && "$net_ok" == "true" ]]; then
                    run_installation "interactive"
                    return
                else
                    msg_warn "Prerequisites not met"
                    press_enter
                fi
                ;;
            2)
                if [[ "$root_ok" == "true" && "$net_ok" == "true" ]]; then
                    run_installation "desktop"
                    return
                else
                    msg_warn "Prerequisites not met"
                    press_enter
                fi
                ;;
            3)
                if [[ "$root_ok" == "true" && "$net_ok" == "true" ]]; then
                    run_installation "headless"
                    return
                else
                    msg_warn "Prerequisites not met"
                    press_enter
                fi
                ;;
            4)
                if [[ "$root_ok" == "true" && "$net_ok" == "true" ]]; then
                    run_installation "minimal"
                    return
                else
                    msg_warn "Prerequisites not met"
                    press_enter
                fi
                ;;
            v|V)
                show_installation_phases
                ;;
            b|B)
                return
                ;;
            *)
                msg_warn "Invalid option"
                sleep 1
                ;;
        esac
    done
}

show_installation_phases() {
    print_small_banner "Installation Phases"
    
    cat << 'PHASES'

    MiOS-Build Installation Phases
    â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    â”Œâ”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    â”‚Phase â”‚ Description                  â”‚ Key Packages                  â”‚
    â”œâ”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤
    â”‚  1   â”‚ Hardware Detection           â”‚ CPU, GPU, IOMMU, TPM          â”‚
    â”‚  2   â”‚ Configuration Prompts        â”‚ Mode selection                â”‚
    â”‚  3   â”‚ Desktop Environment          â”‚ GNOME, GDM (optional)         â”‚
    â”‚  4   â”‚ Virtualization Stack         â”‚ qemu, libvirt, virt-manager   â”‚
    â”‚  5   â”‚ Cockpit & Monitoring         â”‚ cockpit, pcp, sensors         â”‚
    â”‚  6   â”‚ Containers & Network         â”‚ podman, firewalld, samba      â”‚
    â”‚  7   â”‚ Power & Security             â”‚ tuned, tpm2-tools, sbctl      â”‚
    â”‚  8   â”‚ Kernel & ZFS                 â”‚ linux-lts, zfs-dkms           â”‚
    â”‚  9   â”‚ NVIDIA (if detected)         â”‚ nvidia-dkms                   â”‚
    â”‚ 10   â”‚ AUR Packages                 â”‚ yay, cockpit-zfs, virtio-win  â”‚
    â”‚ 11   â”‚ GNOME Extensions             â”‚ TuneD switcher                â”‚
    â”‚ 12   â”‚ Flatpak Applications         â”‚ Flathub setup                 â”‚
    â”‚ 13   â”‚ Service Configuration        â”‚ Enable libvirt, cockpit       â”‚
    â”‚ 14   â”‚ Secure Boot (optional)       â”‚ sbctl key enrollment          â”‚
    â”‚ 15   â”‚ User & Network               â”‚ Group membership, polkit      â”‚
    â”‚ 16   â”‚ Looking Glass (optional)     â”‚ Build from source             â”‚
    â”‚ 17   â”‚ Helper Scripts               â”‚ create-win11-vm, iommu-groups â”‚
    â””â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜

    Estimated Time: 15-30 minutes (depends on network speed)

PHASES
    
    press_enter
}

run_full_profile() {
    print_subsection "Full System Profile"
    
    detect_system
    
    local profile_file="$REAL_HOME/mios-profile-$TIMESTAMP.txt"
    
    msg_info "Generating comprehensive system profile..."
    
    {
        echo "================================================================================"
        echo " MiOS-Build SYSTEM PROFILE"
        echo " Generated: $(date)"
        echo "================================================================================"
        echo ""
        
        echo "=== CPU ==="
        lscpu
        echo ""
        
        echo "=== Memory ==="
        free -h
        cat /proc/meminfo | head -20
        echo ""
        
        echo "=== GPU ==="
        lspci -vnn | grep -A20 "VGA\|3D\|Display"
        echo ""
        
        echo "=== Storage ==="
        lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT
        df -h
        echo ""
        
        echo "=== IOMMU Groups ==="
        for g in $(find /sys/kernel/iommu_groups/* -maxdepth 0 -type d 2>/dev/null | sort -V); do
            echo "Group ${g##*/}:"
            for d in "$g"/devices/*; do
                echo "  $(lspci -nns ${d##*/} 2>/dev/null)"
            done
        done
        echo ""
        
        echo "=== Kernel ==="
        uname -a
        cat /proc/cmdline
        echo ""
        
        echo "=== Modules ==="
        lsmod | sort
        echo ""
        
        echo "=== Services ==="
        systemctl list-units --type=service --state=running --no-pager
        echo ""
        
    } > "$profile_file"
    
    chown "$REAL_USER:$(id -gn "$REAL_USER")" "$profile_file" 2>/dev/null
    
    msg_success "Profile saved: $profile_file"
    
    STATE[assessment_done]="true"
    save_state
    
    press_enter
}

show_system_status() {
    print_small_banner "System Status"
    
    detect_system
    show_system_summary
    
    print_subsection "Service Status"
    
    local services=("libvirtd" "virtqemud" "cockpit.socket" "firewalld" "tuned")
    for svc in "${services[@]}"; do
        if systemctl is-active --quiet "$svc" 2>/dev/null; then
            msg_success "$svc running"
        elif systemctl is-enabled --quiet "$svc" 2>/dev/null; then
            msg_warn "$svc enabled but not running"
        else
            msg_info "$svc not configured"
        fi
    done
    
    print_subsection "MiOS-Build State"
    
    echo -e "      Installation:     ${STATE[install_phase]}"
    echo -e "      VFIO:             ${STATE[vfio_configured]}"
    echo -e "      CPU Isolation:    ${STATE[cpu_isolated]}"
    echo -e "      VM Hooks:         ${STATE[vm_hooks_configured]}"
    echo -e "      Looking Glass:    ${STATE[looking_glass_installed]}"
    echo -e "      Reboot Required:  ${STATE[reboot_required]}"
    
    press_enter
}

show_help() {
    print_small_banner "Help & Documentation"
    
    cat << 'HELP'

    MiOS-Build Unified Management System
    â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•

    This tool provides a single interface for:
    
    â€¢ Pre-install assessment (hardware compatibility check)
    â€¢ Full MiOS-Build installation (virtualization host setup)
    â€¢ VFIO configuration (GPU passthrough)
    â€¢ CPU isolation (performance optimization)
    â€¢ VM CPU pinning (per-VM configuration)
    â€¢ Verification and troubleshooting

    COMMAND LINE USAGE
    â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    sudo ./mios-full.sh                 Interactive menu
    sudo ./mios-full.sh assess          System assessment
    sudo ./mios-full.sh install         Run installation
    sudo ./mios-full.sh vfio            Configure VFIO
    sudo ./mios-full.sh cpu             Configure CPU isolation
    sudo ./mios-full.sh verify          Verify installation
    sudo ./mios-full.sh diagnose        Troubleshooting
    sudo ./mios-full.sh status          Show status
    sudo ./mios-full.sh help            Show this help

    TYPICAL WORKFLOW
    â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    1. Run Assessment â†’ Check hardware compatibility
    2. Run Installation â†’ Install MiOS-Build
    3. Configure VFIO â†’ Set up GPU passthrough
    4. Configure CPU â†’ Optimize for VM performance
    5. Verify â†’ Confirm everything works
    
    FILES
    â”€â”€â”€â”€â”€
    Logs:   /var/log/mios/
    State:  /var/lib/mios/state.json
    Hooks:  /etc/libvirt/hooks/

    For more information, visit:
    https://github.com/your-repo/mios-build

HELP
    
    press_enter
}

view_session_logs() {
    print_small_banner "Session Logs"
    
    if [[ -d "$MIOS_LOG_DIR" ]]; then
        echo ""
        msg_info "Recent log files:"
        ls -lt "$MIOS_LOG_DIR"/*.log 2>/dev/null | head -10 | while read -r line; do
            echo "      $line"
        done
        
        echo ""
        echo "      1) View current session log"
        echo "      2) View current debug log"
        echo "      3) Export all logs"
        echo "      b) Back"
        echo ""
        
        read -rp "      Select option: " choice
        
        case "$choice" in
            1)
                [[ -f "$LOG_FILE" ]] && less "$LOG_FILE" || msg_info "No current session log"
                ;;
            2)
                [[ -f "$DEBUG_LOG" ]] && less "$DEBUG_LOG" || msg_info "No debug log"
                ;;
            3)
                local archive="$REAL_HOME/mios-logs-$TIMESTAMP.tar.gz"
                tar -czf "$archive" -C "$MIOS_LOG_DIR" . 2>/dev/null
                chown "$REAL_USER:$(id -gn "$REAL_USER")" "$archive" 2>/dev/null
                msg_success "Logs exported: $archive"
                press_enter
                ;;
        esac
    else
        msg_info "No logs yet"
        press_enter
    fi
}

#==============================================================================
# MAIN MENU LOOP
#==============================================================================
main_menu_loop() {
    while true; do
        show_main_menu
        
        read -rp "      Select option: " choice
        
        case "$choice" in
            1) menu_assessment ;;
            2) menu_installation ;;
            3) configure_vfio ;;
            4) configure_cpu_isolation ;;
            5) manage_vm_cpu_pins ;;
            6) run_verification ;;
            7) run_diagnostics ;;
            8) analyze_iommu_groups; press_enter ;;
            s|S) show_system_status ;;
            l|L) view_session_logs ;;
            h|H|'?') show_help ;;
            q|Q)
                echo ""
                msg_info "Saving state..."
                save_state
                echo ""
                echo -e "    ${C_SUCCESS}Thank you for using MiOS-Build!${NC}"
                echo ""
                exit 0
                ;;
            *)
                msg_warn "Invalid option: $choice"
                sleep 1
                ;;
        esac
    done
}

#==============================================================================
# COMMAND LINE INTERFACE
#==============================================================================
handle_cli_args() {
    case "${1:-}" in
        assess|assessment)
            init_logging
            load_state
            menu_assessment
            ;;
        install|installation)
            init_logging
            load_state
            menu_installation
            ;;
        vfio)
            init_logging
            load_state
            configure_vfio
            ;;
        cpu|cpu-isolate|isolate)
            init_logging
            load_state
            configure_cpu_isolation
            ;;
        vm|vm-pin|pin)
            init_logging
            load_state
            manage_vm_cpu_pins
            ;;
        verify|verification)
            init_logging
            load_state
            run_verification
            ;;
        diagnose|diagnostic|diagnostics|troubleshoot)
            init_logging
            load_state
            run_diagnostics
            ;;
        status)
            init_logging
            load_state
            detect_system
            show_system_status
            ;;
        iommu)
            init_logging
            load_state
            detect_system
            analyze_iommu_groups
            press_enter
            ;;
        quick)
            init_logging
            load_state
            run_quick_assessment
            ;;
        logs|log)
            init_logging
            view_session_logs
            ;;
        help|-h|--help)
            print_banner
            show_help
            ;;
        version|-v|--version)
            echo "MiOS-Build Unified Management System v$MIOS_VERSION"
            echo "$MIOS_CODENAME"
            ;;
        "")
            # Interactive mode
            init_logging
            load_state
            main_menu_loop
            ;;
        *)
            echo "Unknown command: $1"
            echo ""
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  assess      System assessment"
            echo "  install     MiOS-Build installation"
            echo "  vfio        VFIO GPU passthrough configuration"
            echo "  cpu         CPU core isolation"
            echo "  vm          VM CPU pin manager"
            echo "  verify      Verify installation"
            echo "  diagnose    Troubleshooting"
            echo "  status      Show system status"
            echo "  iommu       View IOMMU groups"
            echo "  quick       Quick assessment"
            echo "  logs        View session logs"
            echo "  help        Show help"
            echo "  version     Show version"
            echo ""
            echo "Run without arguments for interactive menu."
            exit 1
            ;;
    esac
}

#==============================================================================
# ENTRY POINT
#==============================================================================
main() {
    # Handle CLI arguments
    handle_cli_args "$@"
}

# Run main
main "$@"
in
main "$@"

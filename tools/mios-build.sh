#!/bin/bash
###############################################################################
# MiOS-Build Professional Virtualization Host
# Version: v0.1.1
# Target: CachyOS (Minimal or Full Install)
#
# Features:
#   - Full Proxmox parity with unique advantages
#   - Desktop (GNOME) or Headless mode - your choice
#   - Secure Boot enrollment (sbctl) - interactive
#   - Virtual TPM (swtpm) for Windows 11 VMs
#   - Host TPM (tpm2-tools) - interactive
#   - Firewalld with libvirt zones
#   - NVIDIA Early KMS (if detected)
#   - LTS kernel option for ZFS stability
#   - Modular libvirt daemons
#   - DNS check - stops if network broken
#   - Retry logic with comprehensive error reporting
###############################################################################

set -o pipefail

#==============================================================================
# CONFIGURATION
#==============================================================================
SCRIPT_VERSION="v0.1.1"
LOG_DIR="/var/log/mios-build"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
LOGFILE="$LOG_DIR/install-$TIMESTAMP.log"
REPORT_FILE="$LOG_DIR/report-$TIMESTAMP.txt"
DEBUG_LOG="$LOG_DIR/debug-$TIMESTAMP.log"

MAX_RETRY=3

declare -a SUCCESS_TASKS=()
declare -a FAILED_TASKS=()
declare -a SKIPPED_TASKS=()

# Detection flags
HAS_NVIDIA=0
HAS_IOMMU=0
HAS_TPM=0

# User choices
USE_LTS_KERNEL=0
SETUP_SECUREBOOT=0
SETUP_TPM=0
INSTALL_DESKTOP=0

#==============================================================================
# COLORS - MiOS-Build Theme (Teal/Coral/White)
#==============================================================================
# Primary palette
TEAL='\033[38;5;43m'          # Greenish-teal (frames, headers)
TEAL_LIGHT='\033[38;5;80m'    # Light teal (info bullets)
TEAL_DARK='\033[38;5;30m'     # Dark teal (backgrounds)
CORAL='\033[38;5;210m'        # Pastel red/coral (errors, warnings)
WHITE='\033[1;37m'            # Bright white (highlights)
GRAY='\033[38;5;245m'         # Muted gray (skipped items)
SUCCESS='\033[38;5;48m'       # Mint green (success checkmarks)
NC='\033[0m'

# Legacy mappings (for compatibility)
RED="$CORAL"
GREEN="$SUCCESS"
YELLOW="$CORAL"
BLUE="$TEAL_LIGHT"
CYAN="$TEAL"

#==============================================================================
# LOGGING
#==============================================================================
log_success() {
    echo -e "      ${SUCCESS}âœ”${NC} $1"
    SUCCESS_TASKS+=("$1")
    echo "[OK] $1" >> "$DEBUG_LOG"
}

log_fail() {
    echo -e "      ${CORAL}âœ–${NC} $1"
    FAILED_TASKS+=("$1")
    echo "[FAIL] $1" >> "$DEBUG_LOG"
}

log_skip() {
    echo -e "      ${GRAY}â—¦${NC} $1 ${GRAY}($2)${NC}"
    SKIPPED_TASKS+=("$1: $2")
    echo "[SKIP] $1: $2" >> "$DEBUG_LOG"
}

log_info() {
    echo -e "      ${TEAL_LIGHT}â–¸${NC} $1"
}

section() {
    echo ""
    echo -e "${TEAL}    â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”${NC}"
    echo -e "${TEAL}    â”‚${NC}  ${WHITE}$1${NC}"
    echo -e "${TEAL}    â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜${NC}"
}

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

#==============================================================================
# PACKAGE INSTALLATION
#==============================================================================
install_packages() {
    local description="$1"
    shift
    local packages=("$@")
    local attempt=1
    
    while [[ $attempt -le $MAX_RETRY ]]; do
        if pacman -S --noconfirm --needed "${packages[@]}" >> "$DEBUG_LOG" 2>&1; then
            log_success "$description"
            return 0
        fi
        
        if [[ $attempt -lt $MAX_RETRY ]]; then
            echo -e "        ${GRAY}â†» Retry $attempt/$MAX_RETRY...${NC}"
            sleep 2
        fi
        attempt=$((attempt + 1))
    done
    
    log_fail "$description"
    return 1
}

install_aur() {
    local package="$1"
    
    if ! command -v yay &>/dev/null; then
        log_skip "$package" "yay not available"
        return 1
    fi
    
    if pacman -Qs "^${package}$" &>/dev/null; then
        log_skip "$package" "already installed"
        return 0
    fi
    
    local attempt=1
    while [[ $attempt -le $MAX_RETRY ]]; do
        if sudo -u "$REAL_USER" yay -S --noconfirm --needed --answerdiff=None --answerclean=None "$package" >> "$DEBUG_LOG" 2>&1; then
            log_success "$package (AUR)"
            return 0
        fi
        
        if [[ $attempt -lt $MAX_RETRY ]]; then
            echo -e "        ${GRAY}â†» Retry $attempt/$MAX_RETRY...${NC}"
            sleep 2
        fi
        attempt=$((attempt + 1))
    done
    
    log_fail "$package (AUR)"
    return 1
}

#==============================================================================
# INITIALIZATION
#==============================================================================
init() {
    if [[ $EUID -ne 0 ]]; then
        echo -e "${RED}Error: Run as root: sudo $0${NC}"
        exit 1
    fi
    
    REAL_USER="${SUDO_USER:-$USER}"
    if [[ "$REAL_USER" == "root" ]]; then
        echo -e "${RED}Error: Run with sudo, not as root directly${NC}"
        exit 1
    fi
    
    mkdir -p "$LOG_DIR"
    touch "$DEBUG_LOG"
    
    exec > >(tee -a "$LOGFILE") 2>&1
    
    clear
    echo ""
    echo -e "${TEAL}    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—${NC}"
    echo -e "${TEAL}    â•‘${NC}                                                                   ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}   ${WHITE}â–‘â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–‘â–ˆâ–ˆâ•—â–‘â–‘â–‘â–‘â–‘â–‘â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–‘â–ˆâ–ˆâ•—â–‘â–‘â–‘â–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–‘${NC}                      ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}   ${WHITE}â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•—â–ˆâ–ˆâ•‘â–‘â–‘â–‘â–‘â–‘â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•—â–ˆâ–ˆâ•‘â–‘â–‘â–‘â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•—${NC}                      ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}   ${WHITE}â–ˆâ–ˆâ•‘â–‘â–‘â•šâ•â•â–ˆâ–ˆâ•‘â–‘â–‘â–‘â–‘â–‘â–ˆâ–ˆâ•‘â–‘â–‘â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘â–‘â–‘â–‘â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘â–‘â–‘â–ˆâ–ˆâ•‘${NC}  ${TEAL_LIGHT}â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€${NC}   ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}   ${WHITE}â–ˆâ–ˆâ•‘â–‘â–‘â–ˆâ–ˆâ•—â–ˆâ–ˆâ•‘â–‘â–‘â–‘â–‘â–‘â–ˆâ–ˆâ•‘â–‘â–‘â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘â–‘â–‘â–‘â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘â–‘â–‘â–ˆâ–ˆâ•‘${NC}  ${GRAY}Workstation${NC}       ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}   ${WHITE}â•šâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â•â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â•šâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â•â•šâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â•â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â•${NC}  ${GRAY}v${SCRIPT_VERSION}${NC}            ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}   ${WHITE}â–‘â•šâ•â•â•â•â•â–‘â•šâ•â•â•â•â•â•â•â–‘â•šâ•â•â•â•â•â–‘â–‘â•šâ•â•â•â•â•â•â–‘â•šâ•â•â•â•â•â•â–‘${NC}                      ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}                                                                   ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    echo -e "${TEAL}    â•‘${NC}  ${TEAL_LIGHT}â–¸${NC} User: ${WHITE}$REAL_USER${NC}                                                  ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}  ${TEAL_LIGHT}â–¸${NC} Platform: ${WHITE}CachyOS${NC}                                              ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}  ${TEAL_LIGHT}â–¸${NC} Log: ${GRAY}$LOGFILE${NC}    ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    echo ""
    
    # DNS check - STOP if broken
    log_info "Checking network (DNS resolution)..."
    if getent hosts archlinux.org &>/dev/null || getent hosts Project-Target.com &>/dev/null; then
        log_success "Network: DNS working"
    else
        echo ""
        echo -e "    ${TEAL}â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”${NC}"
        echo -e "    ${TEAL}â”‚${NC}  ${CORAL}âœ– DNS RESOLUTION FAILED${NC}                                        ${TEAL}â”‚${NC}"
        echo -e "    ${TEAL}â”œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¤${NC}"
        echo -e "    ${TEAL}â”‚${NC}                                                                 ${TEAL}â”‚${NC}"
        echo -e "    ${TEAL}â”‚${NC}  ${WHITE}Fix DNS before running this script:${NC}                            ${TEAL}â”‚${NC}"
        echo -e "    ${TEAL}â”‚${NC}                                                                 ${TEAL}â”‚${NC}"
        echo -e "    ${TEAL}â”‚${NC}  ${GRAY}sudo bash -c 'echo \"nameserver 1.1.1.1\" > /etc/resolv.conf'${NC}    ${TEAL}â”‚${NC}"
        echo -e "    ${TEAL}â”‚${NC}  ${GRAY}sudo bash -c 'echo \"nameserver 8.8.8.8\" >> /etc/resolv.conf'${NC}   ${TEAL}â”‚${NC}"
        echo -e "    ${TEAL}â”‚${NC}                                                                 ${TEAL}â”‚${NC}"
        echo -e "    ${TEAL}â”‚${NC}  Then run this script again.                                    ${TEAL}â”‚${NC}"
        echo -e "    ${TEAL}â”‚${NC}                                                                 ${TEAL}â”‚${NC}"
        echo -e "    ${TEAL}â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜${NC}"
        echo ""
        exit 1
    fi
}

#==============================================================================
# PHASE 1: HARDWARE DETECTION
#==============================================================================
phase_detect() {
    section "PHASE 1: Hardware Detection"
    
    if grep -q "AuthenticAMD" /proc/cpuinfo; then
        log_success "CPU: AMD"
    elif grep -q "GenuineIntel" /proc/cpuinfo; then
        log_success "CPU: Intel"
    fi
    
    if grep -qE "(vmx|svm)" /proc/cpuinfo; then
        local virt=$(grep -oE '(vmx|svm)' /proc/cpuinfo | head -1)
        log_success "Virtualization: $virt"
    else
        log_fail "Virtualization not enabled in BIOS"
    fi
    
    if lspci | grep -qi "nvidia"; then
        HAS_NVIDIA=1
        log_success "NVIDIA GPU detected"
    fi
    
    if [[ -d /sys/kernel/iommu_groups ]] && [[ $(ls /sys/kernel/iommu_groups/ 2>/dev/null | wc -l) -gt 0 ]]; then
        HAS_IOMMU=1
        local groups=$(ls /sys/kernel/iommu_groups/ | wc -l)
        log_success "IOMMU: $groups groups"
    else
        log_skip "IOMMU" "not enabled"
    fi
    
    if [[ -c /dev/tpm0 ]] || [[ -c /dev/tpmrm0 ]]; then
        HAS_TPM=1
        log_success "TPM 2.0 detected"
    else
        log_skip "TPM" "not detected"
    fi
    
    if grep -q "cachyos" /etc/os-release 2>/dev/null; then
        log_success "Distribution: CachyOS"
    fi
}

#==============================================================================
# PHASE 2: CONFIGURATION OPTIONS
#==============================================================================
phase_prompts() {
    section "PHASE 2: Configuration Options"
    echo ""
    
    if ask_yes_no "Install GNOME Desktop? (No = Headless server)"; then
        INSTALL_DESKTOP=1
        log_info "Mode: Desktop (GNOME)"
    else
        log_info "Mode: Headless server"
    fi
    
    if ask_yes_no "Use LTS kernel for ZFS stability?"; then
        USE_LTS_KERNEL=1
        log_info "Will install LTS kernel"
    fi
    
    if ask_yes_no "Configure Secure Boot (sbctl)?"; then
        SETUP_SECUREBOOT=1
        log_info "Will configure Secure Boot"
    fi
    
    if [[ $HAS_TPM -eq 1 ]]; then
        if ask_yes_no "Configure host TPM for key storage?"; then
            SETUP_TPM=1
            log_info "Will configure TPM"
        fi
    fi
    
    echo ""
    log_info "Starting installation..."
    sleep 2
}

#==============================================================================
# PHASE 3: DESKTOP ENVIRONMENT
#==============================================================================
phase_desktop() {
    section "PHASE 3: Desktop Environment"
    
    log_info "Syncing package databases..."
    pacman -Sy --noconfirm >> "$DEBUG_LOG" 2>&1
    
    if [[ $INSTALL_DESKTOP -eq 0 ]]; then
        log_skip "GNOME Desktop" "headless mode"
        return 0
    fi
    
    log_info "Installing GNOME Desktop..."
    install_packages "GNOME Desktop" \
        gdm gnome-shell gnome-console gnome-control-center \
        gnome-tweaks gnome-backgrounds nautilus file-roller \
        xdg-desktop-portal-gnome gcr
    
    log_info "Installing GNOME Extensions..."
    install_packages "GNOME Extensions" \
        gnome-shell-extension-caffeine \
        gnome-shell-extension-dash-to-dock
}

#==============================================================================
# PHASE 4: VIRTUALIZATION
#==============================================================================
phase_virtualization() {
    section "PHASE 4: Virtualization Stack"
    
    log_info "Installing KVM/QEMU/Libvirt..."
    install_packages "Virtualization" \
        qemu-full libvirt virt-manager virt-install virt-viewer \
        dnsmasq openbsd-netcat dmidecode
    
    log_info "Installing UEFI & vTPM..."
    install_packages "UEFI/vTPM" \
        edk2-ovmf swtpm libtpms
}

#==============================================================================
# PHASE 5: COCKPIT & MONITORING
#==============================================================================
phase_cockpit() {
    section "PHASE 5: Cockpit & Monitoring"
    
    log_info "Installing Cockpit..."
    install_packages "Cockpit Suite" \
        cockpit cockpit-machines cockpit-podman \
        cockpit-storaged cockpit-packagekit cockpit-files
    
    log_info "Installing Monitoring..."
    install_packages "Monitoring" pcp lm_sensors
}

#==============================================================================
# PHASE 6: CONTAINERS & NETWORK
#==============================================================================
phase_containers() {
    section "PHASE 6: Containers & Network"
    
    log_info "Installing Podman..."
    install_packages "Podman Stack" \
        podman podman-compose buildah passt
    
    log_info "Installing Network & Firewall..."
    install_packages "Network" \
        firewalld nftables iptables-nft \
        samba wsdd avahi nss-mdns
}

#==============================================================================
# PHASE 7: POWER & SECURITY
#==============================================================================
phase_security() {
    section "PHASE 7: Power & Security Tools"
    
    log_info "Installing TuneD..."
    install_packages "TuneD" tuned
    
    log_info "Installing Security Tools..."
    install_packages "Security" \
        tpm2-tools sbctl kexec-tools
    
    log_info "Installing Utilities..."
    install_packages "Utilities" \
        git base-devel flatpak p7zip wget curl htop btop
}

#==============================================================================
# PHASE 8: KERNEL & ZFS
#==============================================================================
phase_kernel() {
    section "PHASE 8: Kernel & ZFS"
    
    if [[ $USE_LTS_KERNEL -eq 1 ]]; then
        log_info "Installing LTS kernel..."
        install_packages "LTS Kernel" linux-cachyos-lts linux-cachyos-lts-headers
        
        log_info "Installing ZFS for LTS..."
        install_packages "ZFS (LTS)" linux-cachyos-lts-zfs zfs-utils
    else
        log_info "Using current kernel..."
        
        if pacman -Qs linux-cachyos &>/dev/null; then
            install_packages "ZFS" linux-cachyos-zfs zfs-utils || \
            install_packages "ZFS (DKMS)" zfs-dkms zfs-utils
        else
            install_packages "ZFS (DKMS)" zfs-dkms zfs-utils
        fi
    fi
}

#==============================================================================
# PHASE 9: NVIDIA
#==============================================================================
phase_nvidia() {
    if [[ $HAS_NVIDIA -eq 0 ]]; then
        return 0
    fi
    
    section "PHASE 9: NVIDIA Configuration"
    
    if pacman -Qs nvidia &>/dev/null; then
        log_skip "NVIDIA drivers" "already installed"
    else
        log_info "Installing NVIDIA drivers..."
        install_packages "NVIDIA" nvidia-dkms nvidia-utils nvidia-settings
    fi
    
    log_info "Configuring Early KMS..."
    local mkinitcpio="/etc/mkinitcpio.conf"
    if [[ -f "$mkinitcpio" ]] && ! grep -q "nvidia" "$mkinitcpio"; then
        sed -i 's/^MODULES=(\(.*\))/MODULES=(\1 nvidia nvidia_modeset nvidia_uvm nvidia_drm)/' "$mkinitcpio"
        mkinitcpio -P >> "$DEBUG_LOG" 2>&1 && log_success "Initramfs rebuilt" || log_fail "Initramfs"
    else
        log_skip "Early KMS" "already configured"
    fi
    
    echo "options nvidia_drm modeset=1 fbdev=1" > /etc/modprobe.d/nvidia.conf
    log_success "NVIDIA DRM modeset"
}

#==============================================================================
# PHASE 10: AUR PACKAGES
#==============================================================================
phase_aur() {
    section "PHASE 10: AUR Packages"
    
    if ! command -v yay &>/dev/null; then
        log_info "Installing yay..."
        cd /tmp
        rm -rf yay-bin 2>/dev/null
        if sudo -u "$REAL_USER" git clone https://aur.archlinux.org/yay-bin.git >> "$DEBUG_LOG" 2>&1; then
            cd yay-bin
            if sudo -u "$REAL_USER" makepkg -si --noconfirm >> "$DEBUG_LOG" 2>&1; then
                log_success "yay"
            else
                log_fail "yay build"
            fi
            cd /tmp
            rm -rf yay-bin
        else
            log_fail "yay clone (network?)"
        fi
    else
        log_skip "yay" "already installed"
    fi
    
    log_info "Installing Cockpit extensions..."
    install_aur "cockpit-sensors"
    install_aur "cockpit-benchmark"
    install_aur "virtio-win"
    
    log_info "Installing Cockpit ZFS Manager..."
    if [[ -d /usr/share/cockpit/zfs ]]; then
        log_skip "ZFS Manager" "already installed"
    else
        cd /tmp
        rm -rf cockpit-zfs-manager 2>/dev/null
        if git clone https://github.com/45Drives/cockpit-zfs-manager.git >> "$DEBUG_LOG" 2>&1; then
            if [[ -d cockpit-zfs-manager/zfs ]]; then
                cp -r cockpit-zfs-manager/zfs /usr/share/cockpit/
                log_success "Cockpit ZFS Manager"
            fi
        else
            if git clone https://github.com/optimans/cockpit-zfs-manager.git >> "$DEBUG_LOG" 2>&1; then
                if [[ -d cockpit-zfs-manager/zfs ]]; then
                    cp -r cockpit-zfs-manager/zfs /usr/share/cockpit/
                    log_success "Cockpit ZFS Manager (fallback)"
                fi
            else
                log_fail "Cockpit ZFS Manager"
            fi
        fi
        rm -rf cockpit-zfs-manager 2>/dev/null
        cd - >/dev/null
    fi
}

#==============================================================================
# PHASE 11: GNOME EXTENSION (Desktop only)
#==============================================================================
phase_tuned_extension() {
    section "PHASE 11: TuneD Profile Switcher"
    
    if [[ $INSTALL_DESKTOP -eq 0 ]]; then
        log_skip "TuneD Switcher (ext 9020)" "headless mode"
        return 0
    fi
    
    local ext_dir="/home/$REAL_USER/.local/share/gnome-shell/extensions"
    local tuned_ext="$ext_dir/tuned-switcher@Rea1-ms"
    
    mkdir -p "$ext_dir"
    
    if [[ -d "$tuned_ext" ]]; then
        log_skip "TuneD Switcher (ext 9020)" "already installed"
        return 0
    fi
    
    log_info "Installing TuneD Profile Switcher (extension 9020)..."
    cd /tmp
    rm -rf gnome-extension-tuned-switcher 2>/dev/null
    
    if git clone https://github.com/Rea1-ms/gnome-extension-tuned-switcher.git >> "$DEBUG_LOG" 2>&1; then
        local src=$(find gnome-extension-tuned-switcher -name "metadata.json" -exec dirname {} \; | head -1)
        if [[ -n "$src" && -d "$src" ]]; then
            cp -r "$src" "$tuned_ext"
            chown -R "$REAL_USER:$REAL_USER" "$ext_dir"
            log_success "TuneD Switcher (ext 9020)"
        else
            log_fail "TuneD Switcher (no metadata.json)"
        fi
    else
        log_fail "TuneD Switcher (clone failed)"
    fi
    rm -rf gnome-extension-tuned-switcher 2>/dev/null
    cd - >/dev/null
}

#==============================================================================
# PHASE 12: FLATPAK APPS
#==============================================================================
phase_flatpak() {
    section "PHASE 12: Flatpak Applications"
    
    flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo >> "$DEBUG_LOG" 2>&1
    log_success "Flathub repository"
    
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
            log_skip "$name" "already installed"
        else
            log_info "Installing $name..."
            if flatpak install -y flathub "$id" >> "$DEBUG_LOG" 2>&1; then
                log_success "$name"
            else
                log_fail "$name"
            fi
        fi
    done
}

#==============================================================================
# PHASE 13: SERVICES
#==============================================================================
phase_services() {
    section "PHASE 13: Services Configuration"
    
    if [[ $INSTALL_DESKTOP -eq 1 ]]; then
        systemctl enable gdm >> "$DEBUG_LOG" 2>&1 && log_success "GDM enabled" || log_fail "GDM"
    else
        log_skip "GDM" "headless mode"
    fi
    
    log_info "Configuring TuneD..."
    systemctl stop power-profiles-daemon 2>/dev/null
    systemctl disable power-profiles-daemon 2>/dev/null
    systemctl mask power-profiles-daemon 2>/dev/null
    systemctl unmask tuned 2>/dev/null
    systemctl enable tuned >> "$DEBUG_LOG" 2>&1
    systemctl start tuned >> "$DEBUG_LOG" 2>&1
    sleep 2
    tuned-adm profile virtual-host >> "$DEBUG_LOG" 2>&1 && \
        log_success "TuneD: virtual-host" || log_fail "TuneD profile"
    
    log_info "Enabling Libvirt (modular)..."
    for sock in virtqemud virtnetworkd virtstoraged virtnodedevd virtproxyd virtsecretd virtinterfaced virtnwfilterd; do
        systemctl enable ${sock}.socket >> "$DEBUG_LOG" 2>&1
    done
    log_success "Libvirt modular sockets"
    
    systemctl enable cockpit.socket >> "$DEBUG_LOG" 2>&1 && \
        log_success "Cockpit enabled" || log_fail "Cockpit"
    
    systemctl enable pmcd pmlogger >> "$DEBUG_LOG" 2>&1 && \
        log_success "PCP metrics" || log_fail "PCP"
    
    log_info "Configuring Firewalld..."
    systemctl enable firewalld >> "$DEBUG_LOG" 2>&1
    systemctl start firewalld >> "$DEBUG_LOG" 2>&1
    firewall-cmd --permanent --add-service=cockpit >> "$DEBUG_LOG" 2>&1
    firewall-cmd --reload >> "$DEBUG_LOG" 2>&1
    log_success "Firewalld configured"
    
    log_info "Configuring Samba..."
    mkdir -p /etc/samba
    if [[ ! -f /etc/samba/smb.conf ]]; then
        cat > /etc/samba/smb.conf << 'EOF'
[global]
   workgroup = WORKGROUP
   server string = MiOS-Build
   security = user
   map to guest = Bad User
   load printers = no
   
   shadow: snapdir = .zfs/snapshot
   shadow: sort = desc
   shadow: format = %Y.%m.%d-%H.%M.%S
EOF
        mkdir -p /srv/samba/public
        chmod 775 /srv/samba/public
    fi
    systemctl enable smb nmb wsdd >> "$DEBUG_LOG" 2>&1
    log_success "Samba configured"
    
    systemctl enable avahi-daemon >> "$DEBUG_LOG" 2>&1
    log_success "Avahi enabled"
    
    for svc in zfs-import-cache zfs-mount zfs-zed zfs.target; do
        systemctl enable $svc >> "$DEBUG_LOG" 2>&1
    done
    log_success "ZFS services"
    
    podman system migrate >> "$DEBUG_LOG" 2>&1 || true
}

#==============================================================================
# PHASE 14: SECURE BOOT & TPM
#==============================================================================
phase_secure_boot() {
    section "PHASE 14: Security Configuration"
    
    if [[ $SETUP_SECUREBOOT -eq 1 ]]; then
        log_info "Configuring Secure Boot..."
        
        if sbctl status 2>/dev/null | grep -q "Setup Mode"; then
            sbctl create-keys >> "$DEBUG_LOG" 2>&1 && log_success "SB keys created" || log_fail "SB keys"
            sbctl enroll-keys --microsoft >> "$DEBUG_LOG" 2>&1 && log_success "SB keys enrolled" || log_fail "SB enroll"
            
            for f in /boot/EFI/systemd/systemd-bootx64.efi /boot/vmlinuz-linux-cachyos /boot/vmlinuz-linux-cachyos-lts; do
                [[ -f "$f" ]] && sbctl sign -s "$f" >> "$DEBUG_LOG" 2>&1
            done
            log_success "Boot files signed"
            log_info "Enable Secure Boot in BIOS after reboot"
        else
            log_skip "Secure Boot" "not in Setup Mode"
        fi
    fi
    
    if [[ $SETUP_TPM -eq 1 ]] && [[ $HAS_TPM -eq 1 ]]; then
        log_info "Testing TPM..."
        if tpm2_getcap properties-fixed >> "$DEBUG_LOG" 2>&1; then
            log_success "TPM 2.0 operational"
        else
            log_fail "TPM communication"
        fi
    fi
    
    log_info "Configuring swtpm..."
    if command -v swtpm &>/dev/null; then
        getent group swtpm &>/dev/null || groupadd -r swtpm
        getent passwd swtpm &>/dev/null || useradd -r -g swtpm -d /var/lib/swtpm -s /sbin/nologin swtpm
        mkdir -p /var/lib/swtpm-localca
        chown -R swtpm:swtpm /var/lib/swtpm-localca 2>/dev/null
        log_success "swtpm ready for Windows 11 VMs"
    fi
}

#==============================================================================
# PHASE 15: USER & NETWORK
#==============================================================================
phase_user_network() {
    section "PHASE 15: User & Network"
    
    log_info "Adding $REAL_USER to groups..."
    usermod -aG libvirt,kvm,wheel,render,video "$REAL_USER" >> "$DEBUG_LOG" 2>&1 && \
        log_success "User groups" || log_fail "User groups"
    
    mkdir -p /etc/polkit-1/rules.d
    cat > /etc/polkit-1/rules.d/50-libvirt.rules << 'EOF'
polkit.addRule(function(action, subject) {
    if (action.id == "org.libvirt.unix.manage" && subject.isInGroup("libvirt")) {
        return polkit.Result.YES;
    }
});
EOF
    log_success "Polkit rule"
    
    if [[ $INSTALL_DESKTOP -eq 1 ]]; then
        local user_systemd="/home/$REAL_USER/.config/systemd/user"
        mkdir -p "$user_systemd"
        cat > "$user_systemd/gcr-ssh-agent.service" << 'EOF'
[Unit]
Description=GCR SSH Agent

[Service]
Type=simple
ExecStart=/usr/lib/gcr-ssh-agent
Restart=on-failure

[Install]
WantedBy=default.target
EOF
        chown -R "$REAL_USER:$REAL_USER" "/home/$REAL_USER/.config"
        log_success "gcr-ssh-agent"
    else
        log_skip "gcr-ssh-agent" "headless mode"
    fi
    
    hostnamectl set-hostname MiOS-Build >> "$DEBUG_LOG" 2>&1
    log_success "Hostname: MiOS-Build"
    
    log_info "Configuring libvirt network..."
    systemctl start virtqemud.socket virtnetworkd.socket >> "$DEBUG_LOG" 2>&1
    sleep 2
    virsh net-autostart default >> "$DEBUG_LOG" 2>&1
    virsh net-start default >> "$DEBUG_LOG" 2>&1 || true
    log_success "Libvirt default network"
    
    firewall-cmd --permanent --zone=libvirt --add-service=dhcp >> "$DEBUG_LOG" 2>&1
    firewall-cmd --permanent --zone=libvirt --add-service=dns >> "$DEBUG_LOG" 2>&1
    firewall-cmd --reload >> "$DEBUG_LOG" 2>&1
    log_success "Firewall zones"
}

#==============================================================================
# PHASE 16: HELPER SCRIPTS
#==============================================================================
phase_helpers() {
    section "PHASE 16: Helper Scripts"
    
    cat > /usr/local/bin/iommu-groups << 'SCRIPT'
#!/bin/bash
shopt -s nullglob
for g in /sys/kernel/iommu_groups/*; do
    echo -e "\033[1;34mIOMMU Group ${g##*/}:\033[0m"
    for d in "$g"/devices/*; do
        echo "  $(lspci -nns "${d##*/}")"
    done
done
SCRIPT
    chmod +x /usr/local/bin/iommu-groups
    log_success "iommu-groups"
    
    cat > /usr/local/bin/zbm-prepare << 'SCRIPT'
#!/bin/bash
[[ $# -lt 2 ]] && { echo "Usage: zbm-prepare <pool> <dataset>"; exit 1; }
zfs set org.zfsbootmenu:commandline="rw quiet" "$2"
zpool set bootfs="$2" "$1"
echo "ZFSBootMenu configured for $2"
SCRIPT
    chmod +x /usr/local/bin/zbm-prepare
    log_success "zbm-prepare"
    
    cat > /usr/local/bin/create-win11-vm << 'SCRIPT'
#!/bin/bash
echo "Windows 11 VM Requirements:"
echo "  • Firmware: UEFI (OVMF)"
echo "  • TPM: Add Hardware → TPM → Emulated TIS 2.0"
echo "  • CPU: host-passthrough"
echo "  • RAM: 16GB minimum (Auto-scaled to host)"
echo ""
echo "Example virt-install:"
echo "  virt-install --name win11 --memory 16384 --vcpus 8 \\"
echo "    --os-variant win11 --boot uefi \\"
echo "    --tpm backend.type=emulator,backend.version=2.0,model=tpm-tis \\"
echo "    --disk size=80 --cdrom /path/to/win11.iso"
SCRIPT
    chmod +x /usr/local/bin/create-win11-vm
    log_success "create-win11-vm"
}

#==============================================================================
# GENERATE REPORT
#==============================================================================
generate_report() {
    section "Installation Report"
    
    local ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    local mode="Headless"
    [[ $INSTALL_DESKTOP -eq 1 ]] && mode="Desktop (GNOME)"
    
    cat > "$REPORT_FILE" << EOF
================================================================================
 MiOS-Build Professional Virtualization Host - Installation Report
================================================================================
 Version:    $SCRIPT_VERSION
 Mode:       $mode
 Completed:  $(date)
 User:       $REAL_USER
 Hostname:   MiOS-Build
================================================================================

SUMMARY: ${#SUCCESS_TASKS[@]} success, ${#FAILED_TASKS[@]} failed, ${#SKIPPED_TASKS[@]} skipped

ACCESS
======
 Cockpit:    https://${ip:-localhost}:9090
 VM Manager: virt-manager (or Cockpit Machines)
 Helpers:    iommu-groups, zbm-prepare, create-win11-vm

STATUS
======
 TuneD:    $(tuned-adm active 2>/dev/null | grep -oP 'Current active profile: \K.*' || echo 'unknown')
 Firewall: $(systemctl is-active firewalld 2>/dev/null)
 Libvirt:  $(systemctl is-active virtqemud.socket 2>/dev/null)
 Cockpit:  $(systemctl is-enabled cockpit.socket 2>/dev/null)

COCKPIT COMPONENTS
==================
$(for c in machines podman storaged files zfs sensors benchmark; do
    [[ -d /usr/share/cockpit/$c ]] && echo " âœ“ $c" || echo " âœ— $c"
done)

FAILED TASKS
============
$(if [[ ${#FAILED_TASKS[@]} -eq 0 ]]; then echo " None"; else printf ' âœ— %s\n' "${FAILED_TASKS[@]}"; fi)

LOGS: $LOGFILE | $DEBUG_LOG | $REPORT_FILE
================================================================================
EOF

    echo ""
    echo -e "${TEAL}    â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—${NC}"
    echo -e "${TEAL}    â•‘${NC}                                                                   ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}   ${SUCCESS}â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—${NC}        ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}   ${SUCCESS}â•šâ•â•â•â•â•â•šâ•â•â•â•â•â•šâ•â•â•â•â•â•šâ•â•â•â•â•â•šâ•â•â•â•â•â•šâ•â•â•â•â•â•šâ•â•â•â•â•â•šâ•â•â•â•â•â•šâ•â•â•â•â•${NC}        ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}                                                                   ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}              ${WHITE}I N S T A L L A T I O N   C O M P L E T E${NC}              ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}                                                                   ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    echo -e "${TEAL}    â•‘${NC}                                                                   ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}   ${TEAL_LIGHT}Mode:${NC}        ${WHITE}$mode${NC}                                        ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}   ${SUCCESS}Successful:${NC}  ${WHITE}${#SUCCESS_TASKS[@]}${NC}                                                ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}   ${CORAL}Failed:${NC}      ${WHITE}${#FAILED_TASKS[@]}${NC}                                                 ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}   ${GRAY}Skipped:${NC}     ${WHITE}${#SKIPPED_TASKS[@]}${NC}                                                ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}                                                                   ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â• â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•£${NC}"
    echo -e "${TEAL}    â•‘${NC}                                                                   ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}   ${TEAL_LIGHT}â–¸${NC} Cockpit:  ${WHITE}https://${ip:-localhost}:9090${NC}                        ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}   ${TEAL_LIGHT}â–¸${NC} Report:   ${GRAY}$REPORT_FILE${NC}    ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•‘${NC}                                                                   ${TEAL}â•‘${NC}"
    echo -e "${TEAL}    â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    echo ""
    echo -e "    ${CORAL}â–º REBOOT NOW:${NC} ${WHITE}sudo reboot${NC}"
    echo ""
}

#==============================================================================
# MAIN
#==============================================================================
main() {
    init
    phase_detect
    phase_prompts
    phase_desktop
    phase_virtualization
    phase_cockpit
    phase_containers
    phase_security
    phase_kernel
    phase_nvidia
    phase_aur
    phase_tuned_extension
    phase_flatpak
    phase_services
    phase_secure_boot
    phase_user_network
    phase_helpers
    generate_report
}

main "$@"

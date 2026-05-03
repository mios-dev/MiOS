#!/bin/bash

################################################################################
# Linux System & Hardware Profiler
# Comprehensive system information collection for MiOS-Build development
################################################################################

set -euo pipefail

# Color definitions
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly BOLD='\033[1m'
readonly NC='\033[0m' # No Color

# Output file
readonly OUTPUT_DIR="$HOME/system-profile"
readonly TIMESTAMP=$(date +%Y%m%d_%H%M%S)
readonly OUTPUT_FILE="$OUTPUT_DIR/system-profile-${TIMESTAMP}.txt"
readonly JSON_FILE="$OUTPUT_DIR/system-profile-${TIMESTAMP}.json"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Initialize JSON output
JSON_DATA="{"

################################################################################
# Helper Functions
################################################################################

print_header()  { echo -e "
${BOLD}${CYAN}== $1 ==${NC}
"; }
print_section() { echo -e "
${BOLD}${YELLOW}>> $1${NC}
"; }
print_info()    { echo -e "${GREEN}+${NC} $1"; }
print_warning() { echo -e "${YELLOW}!${NC} $1"; }
print_error()   { echo -e "${RED}-${NC} $1"; }

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

safe_exec() {
    local cmd="$1"
    local description="$2"
    
    if eval "$cmd" 2>/dev/null; then
        return 0
    else
        print_warning "$description: Command not available or failed"
        return 1
    fi
}

append_to_output() {
    echo "$1" | tee -a "$OUTPUT_FILE"
}

################################################################################
# Check and Install Required Tools
################################################################################

check_tools() {
    print_header "CHECKING REQUIRED TOOLS"
    
    local tools=(
        "lscpu" "lshw" "lspci" "lsusb" "dmidecode" "ethtool"
        "smartctl" "sensors" "hwinfo" "inxi" "neofetch"
    )
    
    local missing_tools=()
    
    for tool in "${tools[@]}"; do
        if command_exists "$tool"; then
            print_info "$tool is available"
        else
            print_warning "$tool is not installed"
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -gt 0 ]; then
        echo -e "\n${YELLOW}Missing tools: ${missing_tools[*]}${NC}"
        echo "Install with your package manager (e.g., pacman, apt, dnf)"
    fi
}

################################################################################
# System Information Collection Functions
################################################################################

collect_basic_info() {
    print_header "BASIC SYSTEM INFORMATION"
    
    {
        echo "Hostname: $(hostname)"
        echo "Kernel: $(uname -r)"
        echo "Architecture: $(uname -m)"
        echo "Distribution: $(cat /etc/os-release | grep -E '^(NAME|VERSION)' | tr '\n' ' ')"
        echo "Uptime: $(uptime -p)"
        echo "Current User: $(whoami)"
        echo "Date: $(date)"
        echo "Timezone: $(timedatectl | grep 'Time zone' | awk '{print $3}')"
    } | tee -a "$OUTPUT_FILE"
}

collect_cpu_info() {
    print_header "CPU INFORMATION"
    
    print_section "CPU Details"
    lscpu | tee -a "$OUTPUT_FILE"
    
    print_section "CPU Topology"
    if [ -f /proc/cpuinfo ]; then
        {
            echo "CPU Model: $(grep -m1 'model name' /proc/cpuinfo | cut -d':' -f2 | xargs)"
            echo "Physical CPUs: $(grep 'physical id' /proc/cpuinfo | sort -u | wc -l)"
            echo "CPU Cores: $(grep -c 'processor' /proc/cpuinfo)"
            echo "Threads per Core: $(lscpu | grep 'Thread(s) per core' | awk '{print $4}')"
        } | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "CPU Frequency & Governors"
    if command_exists cpupower; then
        cpupower frequency-info 2>/dev/null | tee -a "$OUTPUT_FILE" || echo "cpupower not available"
    fi
    
    print_section "CPU Cache"
    lscpu -C 2>/dev/null | tee -a "$OUTPUT_FILE" || echo "Cache info not available"
    
    print_section "NUMA Topology"
    if command_exists numactl; then
        numactl --hardware 2>/dev/null | tee -a "$OUTPUT_FILE"
    else
        echo "numactl not installed" | tee -a "$OUTPUT_FILE"
    fi
}

collect_memory_info() {
    print_header "MEMORY INFORMATION"
    
    print_section "Memory Summary"
    free -h | tee -a "$OUTPUT_FILE"
    
    print_section "Detailed Memory Info"
    if command_exists dmidecode; then
        sudo dmidecode -t memory 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "Memory Configuration"
    cat /proc/meminfo | tee -a "$OUTPUT_FILE"
}

collect_motherboard_bios() {
    print_header "MOTHERBOARD & BIOS INFORMATION"
    
    if command_exists dmidecode; then
        print_section "BIOS Information"
        sudo dmidecode -t bios 2>/dev/null | tee -a "$OUTPUT_FILE"
        
        print_section "Baseboard/Motherboard"
        sudo dmidecode -t baseboard 2>/dev/null | tee -a "$OUTPUT_FILE"
        
        print_section "System Information"
        sudo dmidecode -t system 2>/dev/null | tee -a "$OUTPUT_FILE"
        
        print_section "Chassis Information"
        sudo dmidecode -t chassis 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "UEFI/BIOS Variables"
    if [ -d /sys/firmware/efi/efivars ]; then
        echo "UEFI Boot Mode: Yes" | tee -a "$OUTPUT_FILE"
        ls -1 /sys/firmware/efi/efivars/ | head -20 | tee -a "$OUTPUT_FILE"
    else
        echo "BIOS Boot Mode (Legacy)" | tee -a "$OUTPUT_FILE"
    fi
}

collect_iommu_groups() {
    print_header "IOMMU GROUPS (PCIe Passthrough)"
    
    if [ -d /sys/kernel/iommu_groups ]; then
        print_section "IOMMU Status"
        if dmesg | grep -i iommu | grep -i enabled >/dev/null 2>&1; then
            echo "IOMMU: ENABLED" | tee -a "$OUTPUT_FILE"
        else
            echo "IOMMU: May not be enabled in kernel" | tee -a "$OUTPUT_FILE"
        fi
        
        print_section "IOMMU Groups Mapping"
        for d in /sys/kernel/iommu_groups/*/devices/*; do
            if [ -e "$d" ]; then
                n=${d#*/iommu_groups/*}; n=${n%%/*}
                printf 'IOMMU Group %s: ' "$n"
                lspci -nns "${d##*/}"
            fi
        done | sort -h | tee -a "$OUTPUT_FILE"
    else
        echo "IOMMU not available or not enabled" | tee -a "$OUTPUT_FILE"
    fi
}

collect_pcie_devices() {
    print_header "PCIe DEVICES"
    
    print_section "All PCI Devices (Detailed)"
    lspci -vvv 2>/dev/null | tee -a "$OUTPUT_FILE"
    
    print_section "PCI Tree View"
    lspci -tv 2>/dev/null | tee -a "$OUTPUT_FILE"
    
    print_section "PCIe Link Status"
    for dev in $(lspci | awk '{print $1}'); do
        echo "=== Device $dev ===" | tee -a "$OUTPUT_FILE"
        lspci -vv -s "$dev" 2>/dev/null | grep -E '(LnkCap|LnkSta)' | tee -a "$OUTPUT_FILE"
    done
}

collect_graphics_info() {
    print_header "GRAPHICS INFORMATION"
    
    print_section "Graphics Cards"
    lspci | grep -i vga | tee -a "$OUTPUT_FILE"
    lspci | grep -i '3d' | tee -a "$OUTPUT_FILE"
    
    print_section "Display Information"
    if command_exists xrandr && [ -n "${DISPLAY:-}" ]; then
        xrandr --verbose 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "OpenGL Information"
    if command_exists glxinfo && [ -n "${DISPLAY:-}" ]; then
        glxinfo 2>/dev/null | grep -E '(OpenGL|direct rendering)' | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "Vulkan Information"
    if command_exists vulkaninfo; then
        vulkaninfo --summary 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "NVIDIA GPU Info (if present)"
    if command_exists nvidia-smi; then
        nvidia-smi 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
}

collect_storage_info() {
    print_header "STORAGE INFORMATION"
    
    print_section "Block Devices"
    lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL,SERIAL 2>/dev/null | tee -a "$OUTPUT_FILE"
    
    print_section "Disk Usage"
    df -h | tee -a "$OUTPUT_FILE"
    
    print_section "Partition Information"
    sudo fdisk -l 2>/dev/null | tee -a "$OUTPUT_FILE"
    
    print_section "SMART Status (All Drives)"
    if command_exists smartctl; then
        for disk in $(lsblk -d -o NAME | grep -v NAME); do
            echo "=== /dev/$disk ===" | tee -a "$OUTPUT_FILE"
            sudo smartctl -a "/dev/$disk" 2>/dev/null | tee -a "$OUTPUT_FILE"
            echo "" | tee -a "$OUTPUT_FILE"
        done
    fi
    
    print_section "NVMe Devices"
    if command_exists nvme; then
        sudo nvme list 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "Filesystem Mounts"
    cat /proc/mounts | tee -a "$OUTPUT_FILE"
}

collect_network_info() {
    print_header "NETWORK INFORMATION"
    
    print_section "Network Interfaces"
    ip -br addr show | tee -a "$OUTPUT_FILE"
    
    print_section "Detailed Interface Info"
    ip addr show | tee -a "$OUTPUT_FILE"
    
    print_section "Network Controllers"
    lspci | grep -i network | tee -a "$OUTPUT_FILE"
    lspci | grep -i ethernet | tee -a "$OUTPUT_FILE"
    
    print_section "Wireless Devices"
    if command_exists iw; then
        iw dev 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "Routing Table"
    ip route show | tee -a "$OUTPUT_FILE"
    
    print_section "Network Statistics"
    for iface in $(ls /sys/class/net/ | grep -v lo); do
        echo "=== $iface ===" | tee -a "$OUTPUT_FILE"
        if command_exists ethtool; then
            sudo ethtool "$iface" 2>/dev/null | tee -a "$OUTPUT_FILE"
        fi
    done
}

collect_usb_devices() {
    print_header "USB DEVICES & PERIPHERALS"
    
    print_section "USB Device Tree"
    lsusb -t 2>/dev/null | tee -a "$OUTPUT_FILE"
    
    print_section "Detailed USB Information"
    lsusb -v 2>/dev/null | tee -a "$OUTPUT_FILE"
}

collect_input_devices() {
    print_header "INPUT DEVICES"
    
    print_section "Input Device List"
    if [ -d /proc/bus/input/devices ]; then
        cat /proc/bus/input/devices | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "Event Devices"
    ls -la /dev/input/ | tee -a "$OUTPUT_FILE"
}

collect_audio_info() {
    print_header "AUDIO INFORMATION"
    
    print_section "Sound Cards"
    cat /proc/asound/cards 2>/dev/null | tee -a "$OUTPUT_FILE"
    
    print_section "Audio Devices"
    lspci | grep -i audio | tee -a "$OUTPUT_FILE"
    
    print_section "ALSA Information"
    if command_exists aplay; then
        aplay -l 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "PulseAudio/PipeWire Info"
    if command_exists pactl; then
        pactl info 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
}

collect_kernel_modules() {
    print_header "LOADED KERNEL MODULES & DRIVERS"
    
    print_section "Currently Loaded Modules"
    lsmod | tee -a "$OUTPUT_FILE"
    
    print_section "Module Details (Critical Drivers)"
    local modules=("nvidia" "amdgpu" "i915" "vfio" "vfio_pci" "kvm" "kvm_amd" "kvm_intel")
    for mod in "${modules[@]}"; do
        if lsmod | grep -q "^$mod "; then
            echo "=== $mod ===" | tee -a "$OUTPUT_FILE"
            modinfo "$mod" 2>/dev/null | tee -a "$OUTPUT_FILE"
        fi
    done
    
    print_section "Kernel Parameters"
    cat /proc/cmdline | tee -a "$OUTPUT_FILE"
}

collect_virtualization_info() {
    print_header "VIRTUALIZATION INFORMATION"
    
    print_section "Virtualization Support"
    if grep -q -E '(vmx|svm)' /proc/cpuinfo; then
        echo "CPU Virtualization: ENABLED ($(grep -o -E '(vmx|svm)' /proc/cpuinfo | head -1))" | tee -a "$OUTPUT_FILE"
    else
        echo "CPU Virtualization: NOT DETECTED" | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "KVM Status"
    if [ -e /dev/kvm ]; then
        echo "KVM: Available" | tee -a "$OUTPUT_FILE"
        ls -la /dev/kvm | tee -a "$OUTPUT_FILE"
    else
        echo "KVM: Not available" | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "QEMU/Libvirt"
    if command_exists virsh; then
        virsh version 2>/dev/null | tee -a "$OUTPUT_FILE"
        virsh list --all 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "Docker/Containers"
    if command_exists docker; then
        docker --version 2>/dev/null | tee -a "$OUTPUT_FILE"
        docker info 2>/dev/null | head -30 | tee -a "$OUTPUT_FILE"
    fi
}

collect_security_info() {
    print_header "SECURITY & TPM INFORMATION"
    
    print_section "Secure Boot Status"
    if [ -d /sys/firmware/efi ]; then
        if mokutil --sb-state 2>/dev/null; then
            mokutil --sb-state | tee -a "$OUTPUT_FILE"
        else
            echo "mokutil not available" | tee -a "$OUTPUT_FILE"
        fi
    fi
    
    print_section "TPM Status"
    if [ -e /dev/tpm0 ]; then
        echo "TPM Device: Present (/dev/tpm0)" | tee -a "$OUTPUT_FILE"
    else
        echo "TPM Device: Not detected" | tee -a "$OUTPUT_FILE"
    fi
    
    if [ -d /sys/class/tpm ]; then
        ls -la /sys/class/tpm/ | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "SELinux Status"
    if command_exists getenforce; then
        getenforce 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "AppArmor Status"
    if command_exists aa-status; then
        sudo aa-status 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
}

collect_sensors_thermal() {
    print_header "SENSORS & THERMAL INFORMATION"
    
    print_section "Temperature Sensors"
    if command_exists sensors; then
        sensors 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "Thermal Zones"
    if [ -d /sys/class/thermal ]; then
        for zone in /sys/class/thermal/thermal_zone*; do
            if [ -e "$zone/type" ]; then
                echo "$(cat $zone/type): $(cat $zone/temp 2>/dev/null || echo 'N/A')Â°C" | tee -a "$OUTPUT_FILE"
            fi
        done
    fi
    
    print_section "Fan Information"
    if [ -d /sys/class/hwmon ]; then
        for hwmon in /sys/class/hwmon/hwmon*/fan*_input; do
            if [ -e "$hwmon" ]; then
                echo "$hwmon: $(cat $hwmon) RPM" | tee -a "$OUTPUT_FILE"
            fi
        done
    fi
}

collect_power_info() {
    print_header "POWER INFORMATION"
    
    print_section "Power Supply"
    if [ -d /sys/class/power_supply ]; then
        for ps in /sys/class/power_supply/*; do
            echo "=== $(basename $ps) ===" | tee -a "$OUTPUT_FILE"
            cat "$ps/uevent" 2>/dev/null | tee -a "$OUTPUT_FILE"
        done
    fi
    
    print_section "Battery Information (if laptop)"
    if command_exists upower; then
        upower -d 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
}

collect_installed_packages() {
    print_header "INSTALLED PACKAGES"
    
    print_section "Package Manager & Count"
    if command_exists pacman; then
        echo "Package Manager: pacman (Arch-based)" | tee -a "$OUTPUT_FILE"
        echo "Installed Packages: $(pacman -Q | wc -l)" | tee -a "$OUTPUT_FILE"
        echo "" | tee -a "$OUTPUT_FILE"
        echo "Package List:" | tee -a "$OUTPUT_FILE"
        pacman -Q | tee -a "$OUTPUT_FILE"
    elif command_exists apt; then
        echo "Package Manager: apt (Debian-based)" | tee -a "$OUTPUT_FILE"
        echo "Installed Packages: $(dpkg -l | grep ^ii | wc -l)" | tee -a "$OUTPUT_FILE"
        dpkg -l | tee -a "$OUTPUT_FILE"
    elif command_exists dnf; then
        echo "Package Manager: dnf (Fedora-based)" | tee -a "$OUTPUT_FILE"
        echo "Installed Packages: $(dnf list installed | wc -l)" | tee -a "$OUTPUT_FILE"
        dnf list installed | tee -a "$OUTPUT_FILE"
    elif command_exists zypper; then
        echo "Package Manager: zypper (openSUSE)" | tee -a "$OUTPUT_FILE"
        zypper packages --installed-only | tee -a "$OUTPUT_FILE"
    fi
}

collect_system_services() {
    print_header "SYSTEM SERVICES"
    
    print_section "Systemd Services"
    if command_exists systemctl; then
        systemctl list-units --type=service --all | tee -a "$OUTPUT_FILE"
    fi
}

collect_hardware_compatibility() {
    print_header "HARDWARE COMPATIBILITY DATABASE"
    
    print_section "Hardware Info Summary"
    if command_exists hwinfo; then
        hwinfo --short 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "System Summary (inxi)"
    if command_exists inxi; then
        inxi -Fxxxza --no-host 2>/dev/null | tee -a "$OUTPUT_FILE"
    fi
}

collect_boot_info() {
    print_header "BOOT INFORMATION"
    
    print_section "Boot Loader"
    if [ -d /boot/grub ]; then
        echo "Boot Loader: GRUB" | tee -a "$OUTPUT_FILE"
        if [ -f /boot/grub/grub.cfg ]; then
            grep -E '^menuentry' /boot/grub/grub.cfg | tee -a "$OUTPUT_FILE"
        fi
    fi
    
    if [ -d /boot/loader/entries ]; then
        echo "systemd-boot entries:" | tee -a "$OUTPUT_FILE"
        ls -la /boot/loader/entries/ | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "Boot Messages (dmesg - first 100 lines)"
    dmesg | head -100 | tee -a "$OUTPUT_FILE"
}

collect_display_server() {
    print_header "DISPLAY SERVER & DESKTOP ENVIRONMENT"
    
    print_section "Display Server"
    if [ -n "${WAYLAND_DISPLAY:-}" ]; then
        echo "Display Server: Wayland" | tee -a "$OUTPUT_FILE"
    elif [ -n "${DISPLAY:-}" ]; then
        echo "Display Server: X11" | tee -a "$OUTPUT_FILE"
    else
        echo "Display Server: Not detected (TTY)" | tee -a "$OUTPUT_FILE"
    fi
    
    print_section "Desktop Environment"
    echo "DE: ${XDG_CURRENT_DESKTOP:-Not set}" | tee -a "$OUTPUT_FILE"
    echo "Session: ${XDG_SESSION_TYPE:-Not set}" | tee -a "$OUTPUT_FILE"
}

################################################################################
# Main Execution
################################################################################

main() {
    clear
    print_header "LINUX SYSTEM & HARDWARE PROFILER"
    echo -e "${BOLD}Starting comprehensive system profile...${NC}"
    echo -e "Output file: ${GREEN}$OUTPUT_FILE${NC}\n"
    
    # Check for root/sudo
    if [ "$EUID" -ne 0 ]; then
        print_warning "Some commands require sudo/root access"
        echo "Run with sudo for complete information"
        echo ""
    fi
    
    # Check tools
    check_tools
    
    # Start profiling
    {
        echo "# Linux System Profile"
        echo "# Generated: $(date)"
        echo "# Hostname: $(hostname)"
        echo ""
    } > "$OUTPUT_FILE"
    
    # Collect all information
    collect_basic_info
    collect_cpu_info
    collect_memory_info
    collect_motherboard_bios
    collect_iommu_groups
    collect_pcie_devices
    collect_graphics_info
    collect_storage_info
    collect_network_info
    collect_usb_devices
    collect_input_devices
    collect_audio_info
    collect_kernel_modules
    collect_virtualization_info
    collect_security_info
    collect_sensors_thermal
    collect_power_info
    collect_installed_packages
    collect_system_services
    collect_hardware_compatibility
    collect_boot_info
    collect_display_server
    
    # Final summary
    print_header "PROFILE COMPLETE"
    echo -e "${GREEN}âœ“${NC} Full system profile saved to: ${BOLD}$OUTPUT_FILE${NC}"
    echo -e "${GREEN}âœ“${NC} Profile directory: ${BOLD}$OUTPUT_DIR${NC}"
    echo ""
    echo -e "${CYAN}File size: $(du -h "$OUTPUT_FILE" | cut -f1)${NC}"
    echo -e "${CYAN}Total sections: 22${NC}"
    echo ""
    echo -e "${YELLOW}Tip: View with: less $OUTPUT_FILE${NC}"
    echo -e "${YELLOW}      or: cat $OUTPUT_FILE | less${NC}"
}

# Run main function
main

exit 0

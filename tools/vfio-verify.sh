#!/bin/bash
# vfio-verify.sh
# Universal Verification script for VFIO passthrough configuration
# 'MiOS': Hardware & Environment Agnostic Verification

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Status tracking
PASS=0
FAIL=0
WARN=0

check_pass() {
    echo -e "${GREEN}[ok]${NC} $1"
    PASS=$((PASS + 1))
}

check_fail() {
    echo -e "${RED}[x]${NC} $1"
    FAIL=$((FAIL + 1))
}

check_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
    WARN=$((WARN + 1))
}

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}'MiOS' VFIO Configuration Verification${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Test 1: Check IOMMU is enabled in kernel
echo -e "${BLUE}[1/10]${NC} Checking IOMMU kernel parameter..."
IOMMU_CMDLINE=$(cat /proc/cmdline | grep -oE '(amd_iommu|intel_iommu)=on')
if [[ -n "$IOMMU_CMDLINE" ]]; then
    check_pass "IOMMU enabled in kernel: $IOMMU_CMDLINE"
else
    check_fail "IOMMU not enabled in kernel parameters"
fi

# Test 2: Check IOMMU is active
echo -e "${BLUE}[2/10]${NC} Checking IOMMU initialization..."
IOMMU_DMESG=$(dmesg | grep -iE 'IOMMU|AMD-Vi|Intel-VT-d' | grep -i "enabled\|initialized" | head -n1)
if [[ -n "$IOMMU_DMESG" ]]; then
    check_pass "IOMMU initialized: ${IOMMU_DMESG:0:80}..."
else
    check_fail "IOMMU not initialized"
fi

# Test 3: Check VFIO modules loaded
echo -e "${BLUE}[3/10]${NC} Checking VFIO modules..."
VFIO_MODULES=("vfio" "vfio_pci" "vfio_iommu_type1")
ALL_LOADED=true
for module in "${VFIO_MODULES[@]}"; do
    if lsmod | grep -q "^$module"; then
        echo "  ${GREEN}[ok]${NC} $module loaded"
    else
        echo "  ${RED}[x]${NC} $module not loaded"
        ALL_LOADED=false
    fi
done

if $ALL_LOADED; then
    check_pass "All VFIO modules loaded"
else
    check_fail "Some VFIO modules missing"
fi

# Test 4: Find Target GPU (bound to vfio-pci or in kernel ids)
echo -e "${BLUE}[4/10]${NC} Detecting Target GPU..."
# Attempt 1: Look for vfio-pci bound devices
TARGET_GPU_PCI=$(lspci -nnk | grep -B2 "vfio-pci" | grep "VGA" | awk '{print $1}' | head -n1)

# Attempt 2: Look for IDs in cmdline if no driver bound yet
if [[ -z "$TARGET_GPU_PCI" ]]; then
    CMDLINE_IDS=$(cat /proc/cmdline | grep -oP 'vfio-pci\.ids=\K[0-9a-f:,]+')
    if [[ -n "$CMDLINE_IDS" ]]; then
        FIRST_ID=$(echo "$CMDLINE_IDS" | cut -d, -f1)
        TARGET_GPU_PCI=$(lspci -nn | grep "$FIRST_ID" | awk '{print $1}' | head -n1)
    fi
fi

if [[ -n "$TARGET_GPU_PCI" ]]; then
    GPU_NAME=$(lspci -s "$TARGET_GPU_PCI" | cut -d: -f3-)
    check_pass "Target GPU found: $GPU_NAME at $TARGET_GPU_PCI"
    
    # Extract IDs
    TARGET_GPU_INFO=$(lspci -nn -s "$TARGET_GPU_PCI")
    GPU_ID=$(echo "$TARGET_GPU_INFO" | grep -oP '\[\K[0-9a-f]{4}:[0-9a-f]{4}(?=\])')
    echo "  Device ID: $GPU_ID"
else
    check_fail "Target GPU for passthrough not detected (none bound to vfio-pci)"
    echo "Exiting - cannot continue without target device"
    exit 1
fi

# Test 5: Check driver binding
echo -e "${BLUE}[5/10]${NC} Checking driver binding..."
DRIVER_INFO=$(lspci -nnk -s "$TARGET_GPU_PCI")
CURRENT_DRIVER=$(echo "$DRIVER_INFO" | grep "Kernel driver in use:" | awk '{print $5}')

if [[ "$CURRENT_DRIVER" == "vfio-pci" ]]; then
    check_pass "Target GPU bound to vfio-pci driver"
elif [[ -z "$CURRENT_DRIVER" ]]; then
    check_warn "No driver bound to Target GPU"
    echo "  This may be intentional if using dynamic binding"
else
    check_fail "Target GPU bound to wrong driver: $CURRENT_DRIVER (expected vfio-pci)"
    echo ""
    echo "  Possible issues:"
    echo "  - VFIO IDs not in kernel parameters"
    echo "  - Module load order incorrect"
    echo "  - Kernel parameters not applied"
fi

# Test 6: Check companion devices (Audio/USB/Serial)
echo -e "${BLUE}[6/10]${NC} Checking companion devices..."
PCI_BUS=$(echo "$TARGET_GPU_PCI" | cut -d: -f1)
COMPANIONS=$(lspci -nn | grep "$PCI_BUS:" | grep -v "VGA" | grep -v "3D controller")

if [[ -n "$COMPANIONS" ]]; then
    while read -r line; do
        COMP_PCI=$(echo "$line" | awk '{print $1}')
        COMP_ID=$(echo "$line" | grep -oP '\[\K[0-9a-f]{4}:[0-9a-f]{4}(?=\])')
        COMP_DRIVER=$(lspci -nnk -s "$COMP_PCI" | grep "Kernel driver in use:" | awk '{print $5}')
        
        if [[ "$COMP_DRIVER" == "vfio-pci" ]]; then
            check_pass "Companion $COMP_PCI ($COMP_ID) bound to vfio-pci"
        else
            check_warn "Companion $COMP_PCI ($COMP_ID) bound to ${COMP_DRIVER:-none}"
            echo "  HINT: For full passthrough, all sub-devices on the same bus should use vfio-pci"
        fi
    done <<< "$COMPANIONS"
else
    check_pass "No companion devices found on this bus"
fi

# Test 7: Check VFIO device nodes
echo -e "${BLUE}[7/10]${NC} Checking VFIO device nodes..."
if [[ -d /dev/vfio ]]; then
    VFIO_DEVICES=$(ls /dev/vfio/ 2>/dev/null | grep -v "vfio" | wc -l)
    if [[ $VFIO_DEVICES -gt 0 ]]; then
        check_pass "VFIO device nodes present: $VFIO_DEVICES device(s)"
        ls -la /dev/vfio/ | grep -v "total" | sed 's/^/  /'
    else
        check_fail "No VFIO device nodes found"
    fi
else
    check_fail "/dev/vfio directory does not exist"
fi

# Test 8: Check IOMMU group
echo -e "${BLUE}[8/10]${NC} Checking IOMMU group isolation..."
if [[ -L "/sys/bus/pci/devices/0000:$TARGET_GPU_PCI/iommu_group" ]]; then
    IOMMU_GROUP=$(basename $(readlink "/sys/bus/pci/devices/0000:$TARGET_GPU_PCI/iommu_group"))
    GROUP_DEVICES=$(ls -1 "/sys/kernel/iommu_groups/$IOMMU_GROUP/devices/" | wc -l)
    
    echo "  IOMMU Group: $IOMMU_GROUP"
    echo "  Devices in group: $GROUP_DEVICES"
    
    if [[ $GROUP_DEVICES -le 3 ]]; then
        check_pass "Good IOMMU isolation (≤3 devices in group)"
    else
        check_warn "Multiple devices in IOMMU group ($GROUP_DEVICES)"
        echo "  Consider ACS override patch if this causes issues"
    fi
    
    echo ""
    echo "  Group members:"
    for dev in /sys/kernel/iommu_groups/$IOMMU_GROUP/devices/*; do
        DEV_ID=$(basename "$dev")
        DEV_INFO=$(lspci -nns "$DEV_ID" | cut -d' ' -f2-)
        echo "    $DEV_INFO"
    done
else
    check_fail "IOMMU group information not available"
fi

# Test 9: Check kernel parameters
echo -e "${BLUE}[9/10]${NC} Checking kernel command line..."
CMDLINE=$(cat /proc/cmdline)

# Check for vfio-pci.ids
if echo "$CMDLINE" | grep -q "vfio-pci.ids="; then
    VFIO_IDS=$(echo "$CMDLINE" | grep -oP 'vfio-pci\.ids=\K[0-9a-f:,]+')
    check_pass "VFIO IDs in kernel params: $VFIO_IDS"
else
    check_fail "vfio-pci.ids not found in kernel parameters"
fi

# Check for iommu=pt
if echo "$CMDLINE" | grep -q "iommu=pt"; then
    check_pass "IOMMU passthrough mode enabled"
else
    check_warn "iommu=pt not set (may impact performance)"
fi

# Test 10: Check for potential conflicts
echo -e "${BLUE}[10/10]${NC} Checking for potential conflicts..."

# Check if proprietary drivers are loaded
if lsmod | grep -q "^nvidia"; then
    check_warn "NVIDIA driver loaded - may conflict with VFIO if not multi-GPU"
fi
if lsmod | grep -q "^amdgpu"; then
    # Check if amdgpu is bound to the TARGET GPU
    if lspci -nnk -s "$TARGET_GPU_PCI" | grep -q "amdgpu"; then
        check_fail "AMDGPU driver still bound to Target GPU"
    fi
fi

# Check if nouveau is loaded
if lsmod | grep -q "^nouveau"; then
    check_warn "Nouveau driver loaded - may conflict with VFIO"
fi

if [[ $WARN -eq 0 && $FAIL -eq 0 ]]; then
    check_pass "No critical driver conflicts detected"
fi

# Summary
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Verification Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Passed:  $PASS${NC}"
echo -e "${YELLOW}Warnings: $WARN${NC}"
echo -e "${RED}Failed:  $FAIL${NC}"
echo ""

if [[ $FAIL -eq 0 ]]; then
    echo -e "${GREEN}[ok] VFIO configuration is correct for your hardware!${NC}"
    echo ""
    echo "Environment: $(systemd-detect-virt)"
    echo ""
elif [[ $FAIL -le 2 && $PASS -ge 6 ]]; then
    echo -e "${YELLOW}[!] Configuration mostly correct with minor issues${NC}"
else
    echo -e "${RED}[x] VFIO configuration has significant issues${NC}"
fi

echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
echo ""
exit $FAIL

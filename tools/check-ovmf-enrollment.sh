#!/bin/bash

# Check for Vendor Secure Boot Enrolled OVMF Files

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}   Vendor Secure Boot OVMF Enrollment Checker${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════${NC}\n"

echo -e "${YELLOW}The Problem:${NC}"
echo -e "  Secure Boot needs VARS files PRE-ENROLLED with Vendor keys"
echo -e "  Regular OVMF_VARS.fd files are BLANK and won't work!\n"

echo -e "${BLUE}[1] Checking for pre-enrolled VARS files...${NC}\n"

# Look for secboot VARS files (pre-enrolled)
SECBOOT_VARS=$(find /usr/share -name "*VARS*secboot*.fd" 2>/dev/null | grep x64)

if [ -n "$SECBOOT_VARS" ]; then
    echo -e "${GREEN}[ok] Found Secure Boot VARS files:${NC}"
    echo "$SECBOOT_VARS" | while read -r file; do
        size=$(stat -c%s "$file" | numfmt --to=iec-i --suffix=B)
        echo -e "  ${GREEN}[ok]${NC} $file ($size)"
    done
else
    echo -e "${RED}[x] No pre-enrolled Secure Boot VARS files found!${NC}"
fi

echo -e "\n${BLUE}[2] Checking standard VARS files...${NC}\n"

STANDARD_VARS=$(find /usr/share/edk2/x64 -name "*VARS*.fd" 2>/dev/null | grep -v secboot)

if [ -n "$STANDARD_VARS" ]; then
    echo -e "${YELLOW}[!] Found standard (blank) VARS files:${NC}"
    echo "$STANDARD_VARS" | while read -r file; do
        size=$(stat -c%s "$file" | numfmt --to=iec-i --suffix=B)
        echo -e "  ${YELLOW}[!]${NC} $file ($size) - NOT enrolled"
    done
fi

echo -e "\n${BLUE}[3] Analyzing available options...${NC}\n"

# Check what we actually have
X64_DIR="/usr/share/edk2/x64"

echo -e "${CYAN}Files in $X64_DIR:${NC}"
ls -lh "$X64_DIR"/*.fd 2>/dev/null | awk '{printf "  %s  %s\n", $9, $5}'

echo -e "\n${BOLD}${YELLOW}═══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${YELLOW}                   DIAGNOSIS${NC}"
echo -e "${BOLD}${YELLOW}═══════════════════════════════════════════════════════${NC}\n"

HAS_SECBOOT_VARS=false
SECBOOT_VARS_PATH=""

# Check for the specific file we need
if [ -f "/usr/share/edk2/x64/OVMF_VARS.secboot.4m.fd" ]; then
    HAS_SECBOOT_VARS=true
    SECBOOT_VARS_PATH="/usr/share/edk2/x64/OVMF_VARS.secboot.4m.fd"
elif [ -f "/usr/share/edk2/x64/OVMF_VARS.secboot.fd" ]; then
    HAS_SECBOOT_VARS=true
    SECBOOT_VARS_PATH="/usr/share/edk2/x64/OVMF_VARS.secboot.fd"
fi

if [ "$HAS_SECBOOT_VARS" = true ]; then
    echo -e "${GREEN}[ok] GOOD NEWS: You have pre-enrolled Secure Boot VARS!${NC}"
    echo -e "  File: ${CYAN}$SECBOOT_VARS_PATH${NC}"
    echo -e "\n${YELLOW}Fix: Use this file as your NVRAM template${NC}"
else
    echo -e "${RED}[x] PROBLEM: You DON'T have pre-enrolled Secure Boot VARS!${NC}"
    echo -e "\n${YELLOW}Your edk2-ovmf package is missing the enrolled VARS files.${NC}"
    echo -e "This is common on Arch-based distros.\n"
fi

echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}                     SOLUTIONS${NC}"
echo -e "${BOLD}${CYAN}═══════════════════════════════════════════════════════${NC}\n"

if [ "$HAS_SECBOOT_VARS" = true ]; then
    echo -e "${GREEN}Solution: Update your VM XML to use the enrolled VARS file:${NC}\n"
    echo -e "${CYAN}Old (wrong):${NC}"
    echo -e '  <nvram template="/usr/share/edk2/x64/OVMF_VARS.4m.fd">...'
    echo
    echo -e "${GREEN}New (correct):${NC}"
    echo -e "  <nvram template=\"$SECBOOT_VARS_PATH\">..."
    echo
else
    echo -e "${YELLOW}Option 1: Check for additional packages${NC}"
    echo -e "  Fedora provides these in the main edk2-ovmf package."
    echo -e "  Ensure it is fully installed:"
    echo -e "  ${CYAN}sudo dnf install edk2-ovmf${NC}"
    echo

    echo -e "${YELLOW}Option 2: Download pre-enrolled OVMF files manually${NC}"
    echo -e "  From Fedora/Ubuntu packages (known to work):"
    echo -e "  ${CYAN}https://www.kraxel.org/repos/jenkins/edk2/${NC}"
    echo -e "  Download: edk2.git-ovmf-x64-*.rpm (then extract)"
    echo

    echo -e "${YELLOW}Option 3: Create enrolled VARS using virt-firmware${NC}"
    echo -e "  ${CYAN}sudo dnf install virt-firmware${NC}"
    echo -e "  Then enroll Vendor keys manually"
    echo

    echo -e "${YELLOW}Option 4: Use QEMU's automatic enrollment (simpler)${NC}"
    echo -e "  Use firmware autoselection with enrolled-keys feature"
    echo -e "  I can create this configuration for you"
fi

echo -e "\n${BOLD}${CYAN}═══════════════════════════════════════════════════════${NC}\n"

# Save results
cat > /tmp/ovmf-diagnosis.txt << EOF
OVMF Secure Boot Diagnosis
==========================
Date: $(date)

Pre-enrolled VARS files found: $HAS_SECBOOT_VARS
Path (if found): $SECBOOT_VARS_PATH

Available OVMF files:
$(ls -lh /usr/share/edk2/x64/*.fd 2>/dev/null)

Recommendation:
EOF

if [ "$HAS_SECBOOT_VARS" = true ]; then
    echo "Use $SECBOOT_VARS_PATH as NVRAM template" >> /tmp/ovmf-diagnosis.txt
else
    echo "Need to obtain pre-enrolled VARS files - see solutions above" >> /tmp/ovmf-diagnosis.txt
fi

echo -e "${GREEN}[ok] Report saved to: ${CYAN}/tmp/ovmf-diagnosis.txt${NC}\n"

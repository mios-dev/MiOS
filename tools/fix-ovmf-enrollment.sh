#!/bin/bash

# OVMF Secure Boot Enrollment Fixer
# Downloads or creates properly enrolled OVMF VARS files

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

set -e

echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}     OVMF Secure Boot Enrollment Fixer${NC}"
echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════${NC}\n"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}✗ This script must be run as root${NC}"
    echo -e "  Run: ${CYAN}sudo $0${NC}"
    exit 1
fi

OVMF_DIR="/usr/share/edk2/x64"
TARGET_VARS="$OVMF_DIR/OVMF_VARS.secboot.4m.fd"

echo -e "${BLUE}[1/5] Checking current OVMF files...${NC}\n"

if [ -f "$TARGET_VARS" ]; then
    echo -e "${GREEN}✓ Pre-enrolled VARS file already exists!${NC}"
    echo -e "  Location: $TARGET_VARS"
    echo -e "  Size: $(stat -c%s "$TARGET_VARS" | numfmt --to=iec-i --suffix=B)"
    echo
    echo -e "${YELLOW}You're all set! Use this file in your VM configuration.${NC}"
    exit 0
fi

echo -e "${YELLOW}⚠ Pre-enrolled VARS file not found${NC}"
echo -e "  Looking for: $TARGET_VARS\n"

echo -e "${BLUE}[2/5] Checking for alternative packages...${NC}\n"

# Check AUR for alternative OVMF packages
echo -e "${CYAN}Searching AUR for OVMF packages with enrolled keys...${NC}"

if command -v yay &>/dev/null; then
    echo -e "\n${YELLOW}Available OVMF-related packages:${NC}"
    yay -Ss ovmf edk2 2>/dev/null | grep -E "^(aur|extra)" | head -20 || true
    echo
elif command -v paru &>/dev/null; then
    echo -e "\n${YELLOW}Available OVMF-related packages:${NC}"
    paru -Ss ovmf edk2 2>/dev/null | grep -E "^(aur|extra)" | head -20 || true
    echo
else
    echo -e "${YELLOW}⚠ No AUR helper found (yay/paru)${NC}"
fi

echo -e "\n${BLUE}[3/5] Solution options...${NC}\n"

echo -e "${BOLD}Choose a solution:${NC}"
echo -e "  ${CYAN}1)${NC} Download pre-enrolled OVMF from Gerd Hoffmann's repo (RECOMMENDED)"
echo -e "  ${CYAN}2)${NC} Copy and manually enroll keys to existing VARS file"
echo -e "  ${CYAN}3)${NC} Use firmware autoselection (libvirt auto-enrolls)"
echo -e "  ${CYAN}4)${NC} Exit and manually install alternative package"
echo

read -p "Enter choice (1-4): " choice

case $choice in
    1)
        echo -e "\n${BLUE}[4/5] Downloading pre-enrolled OVMF files...${NC}\n"
        
        WORK_DIR="/tmp/ovmf-download-$$"
        mkdir -p "$WORK_DIR"
        cd "$WORK_DIR"
        
        echo -e "${CYAN}Downloading from Gerd Hoffmann's Jenkins...${NC}"
        
        # Get the latest build
        LATEST_URL="https://www.kraxel.org/repos/jenkins/edk2/edk2.git-ovmf-x64-0-20231115.1699.gc4e558ebf9.EOL.noarch.rpm"
        
        echo -e "  Downloading OVMF package..."
        if command -v wget &>/dev/null; then
            wget -q --show-progress "$LATEST_URL" -O ovmf.rpm || {
                echo -e "${RED}✗ Download failed${NC}"
                exit 1
            }
        elif command -v curl &>/dev/null; then
            curl -L -# "$LATEST_URL" -o ovmf.rpm || {
                echo -e "${RED}✗ Download failed${NC}"
                exit 1
            }
        else
            echo -e "${RED}✗ Neither wget nor curl available${NC}"
            exit 1
        fi
        
        echo -e "\n  Extracting files..."
        if command -v rpm2cpio &>/dev/null; then
            rpm2cpio ovmf.rpm | cpio -idmv 2>&1 | grep -i "OVMF.*fd$" || true
        elif command -v bsdtar &>/dev/null; then
            bsdtar -xf ovmf.rpm
        else
            echo -e "${RED}✗ No extraction tool available (rpm2cpio or bsdtar)${NC}"
            echo -e "${YELLOW}Install rpmextract: sudo pacman -S rpmextract${NC}"
            exit 1
        fi
        
        # Find the extracted files
        EXTRACTED_CODE=$(find . -name "OVMF_CODE.secboot.fd" -o -name "OVMF_CODE.secboot.4m.fd" | head -1)
        EXTRACTED_VARS=$(find . -name "OVMF_VARS.secboot.fd" -o -name "OVMF_VARS.fd" | grep secboot | head -1)
        
        if [ -z "$EXTRACTED_CODE" ] || [ -z "$EXTRACTED_VARS" ]; then
            echo -e "${RED}✗ Could not find OVMF files in package${NC}"
            ls -R
            exit 1
        fi
        
        echo -e "\n${BLUE}[5/5] Installing files...${NC}\n"
        
        # Rename to 4m convention if needed
        if [[ "$EXTRACTED_VARS" =~ "4m" ]]; then
            DEST_VARS="$OVMF_DIR/OVMF_VARS.secboot.4m.fd"
        else
            DEST_VARS="$OVMF_DIR/OVMF_VARS.secboot.fd"
        fi
        
        cp "$EXTRACTED_VARS" "$DEST_VARS"
        chmod 644 "$DEST_VARS"
        
        echo -e "${GREEN}✓ Installed: $DEST_VARS${NC}"
        echo -e "  Size: $(stat -c%s "$DEST_VARS" | numfmt --to=iec-i --suffix=B)"
        
        # Cleanup
        cd /
        rm -rf "$WORK_DIR"
        
        echo -e "\n${GREEN}✓ Installation complete!${NC}"
        echo -e "\n${YELLOW}Use this file in your VM XML:${NC}"
        echo -e "  ${CYAN}<nvram template=\"$DEST_VARS\">...${NC}"
        ;;
        
    2)
        echo -e "\n${BLUE}[4/5] Creating enrolled VARS from template...${NC}\n"
        
        TEMPLATE_VARS="$OVMF_DIR/OVMF_VARS.4m.fd"
        
        if [ ! -f "$TEMPLATE_VARS" ]; then
            echo -e "${RED}✗ Template VARS file not found: $TEMPLATE_VARS${NC}"
            exit 1
        fi
        
        # Copy template
        cp "$TEMPLATE_VARS" "$TARGET_VARS"
        echo -e "${GREEN}✓ Created: $TARGET_VARS${NC}"
        
        echo -e "\n${YELLOW}Note: Keys will be enrolled on first VM boot${NC}"
        echo -e "  Use firmware autoselection with enrolled-keys=yes"
        ;;
        
    3)
        echo -e "\n${YELLOW}Using firmware autoselection...${NC}\n"
        echo -e "This approach uses libvirt's firmware autoselection."
        echo -e "Keys will be automatically enrolled on first boot.\n"
        echo -e "${CYAN}Use this in your VM XML:${NC}"
        cat << 'XMLEOF'
  <os firmware="efi">
    <type arch="x86_64" machine="pc-q35-10.1">hvm</type>
    <firmware>
      <feature enabled="yes" name="enrolled-keys"/>
      <feature enabled="yes" name="secure-boot"/>
    </firmware>
    <loader readonly="yes" secure="yes" type="pflash" format="raw">/usr/share/edk2/x64/OVMF_CODE.secboot.4m.fd</loader>
    <nvram template="/usr/share/edk2/x64/OVMF_VARS.4m.fd" format="raw">/var/lib/libvirt/qemu/nvram/Xbox_VARS.fd</nvram>
  </os>
XMLEOF
        echo
        echo -e "${YELLOW}With: enrolled-keys=yes, libvirt will enroll keys automatically${NC}"
        ;;
        
    4)
        echo -e "\n${YELLOW}Manual installation options:${NC}"
        echo -e "  • Search AUR: ${CYAN}yay -Ss ovmf secureboot${NC}"
        echo -e "  • Check: ${CYAN}https://aur.archlinux.org/${NC}"
        echo -e "  • Or install from: ${CYAN}https://www.kraxel.org/repos/${NC}"
        exit 0
        ;;
        
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo -e "\n${BOLD}${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}                 Setup Complete!${NC}"
echo -e "${BOLD}${GREEN}═══════════════════════════════════════════════════════${NC}\n"

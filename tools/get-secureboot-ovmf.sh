#!/bin/bash

# Find or Obtain Vendor-Enrolled OVMF Secure Boot Files
# No XML editing - just get the right firmware files

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${CYAN}   Vendor Secure Boot OVMF File Locator/Installer${NC}"
echo -e "${BOLD}${CYAN}══════════════════════════════════════════════════════════${NC}\n"

# Check current files
echo -e "${BLUE}Scanning for OVMF Secure Boot files...${NC}\n"

X64_DIR="/usr/share/edk2/x64"

echo -e "${YELLOW}Current files in $X64_DIR:${NC}"
if [ -d "$X64_DIR" ]; then
    ls -lh "$X64_DIR"/*.fd 2>/dev/null | awk '{printf "  %s  %9s\n", $9, $5}'
else
    echo -e "${RED}  Directory not found!${NC}"
fi
echo

# Check for what we need
HAVE_CODE_SECBOOT=false
HAVE_VARS_SECBOOT=false

if [ -f "$X64_DIR/OVMF_CODE.secboot.4m.fd" ] || [ -f "$X64_DIR/OVMF_CODE.secboot.fd" ]; then
    HAVE_CODE_SECBOOT=true
fi

if [ -f "$X64_DIR/OVMF_VARS.secboot.4m.fd" ] || [ -f "$X64_DIR/OVMF_VARS.secboot.fd" ]; then
    HAVE_VARS_SECBOOT=true
fi

echo -e "${BOLD}Status Check:${NC}"
if [ "$HAVE_CODE_SECBOOT" = true ]; then
    echo -e "  ${GREEN}✓${NC} OVMF_CODE.secboot (Secure Boot firmware)"
else
    echo -e "  ${RED}✗${NC} OVMF_CODE.secboot (Secure Boot firmware)"
fi

if [ "$HAVE_VARS_SECBOOT" = true ]; then
    echo -e "  ${GREEN}✓${NC} OVMF_VARS.secboot (Vendor-enrolled VARS)"
else
    echo -e "  ${RED}✗${NC} OVMF_VARS.secboot (Vendor-enrolled VARS) ${RED}← MISSING!${NC}"
fi
echo

if [ "$HAVE_VARS_SECBOOT" = true ]; then
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ You already have Vendor-enrolled OVMF VARS files!${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}\n"

    # Find the exact path
    if [ -f "$X64_DIR/OVMF_VARS.secboot.4m.fd" ]; then
        VARS_PATH="$X64_DIR/OVMF_VARS.secboot.4m.fd"
    else
        VARS_PATH="$X64_DIR/OVMF_VARS.secboot.fd"
    fi

    echo -e "${YELLOW}File to use in your VM configuration:${NC}"
    echo -e "  ${CYAN}$VARS_PATH${NC}"
    echo -e "  Size: $(stat -c%s "$VARS_PATH" | numfmt --to=iec-i --suffix=B)"
    echo
    exit 0
fi

echo -e "${RED}════════════════════════════════════════════════════════════${NC}"
echo -e "${RED}✗ Vendor-enrolled VARS files NOT found${NC}"
echo -e "${RED}════════════════════════════════════════════════════════════${NC}\n"

echo -e "${YELLOW}You need OVMF_VARS.secboot files with pre-enrolled Vendor keys.${NC}"
echo -e "${YELLOW}The standard edk2-ovmf package doesn't include these.${NC}\n"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}This script needs root privileges to install files.${NC}"
    echo -e "Run: ${CYAN}sudo $0${NC}\n"
    exit 1
fi

echo -e "${BOLD}Installation Options:${NC}\n"
echo -e "  ${CYAN}1)${NC} Download from Gerd Hoffmann's OVMF builds (Jenkins)"
echo -e "     ${GREEN}Recommended${NC} - Official EDK2 builds with MS keys"
echo -e "     Source: https://www.kraxel.org/repos/jenkins/edk2/"
echo
echo -e "  ${CYAN}2)${NC} Download from Fedora RPM repository"
echo -e "     Fedora's edk2-ovmf includes enrolled VARS"
echo -e "     Source: https://dl.fedoraproject.org/"
echo
echo -e "  ${CYAN}3)${NC} Check AUR for alternative packages"
echo -e "     (Not applicable for Fedora bootc)"
echo
echo -e "  ${CYAN}4)${NC} Exit (manual installation)"
echo

read -p "Choose option (1-4): " choice
echo

case $choice in
    1)
        echo -e "${BLUE}Downloading from Gerd Hoffmann's Jenkins builds...${NC}\n"

        WORK_DIR="/tmp/ovmf-download-$$"
        mkdir -p "$WORK_DIR"
        cd "$WORK_DIR"

        # Try to get the latest working build
        # Using a known-good build URL
        RPM_URL="https://www.kraxel.org/repos/jenkins/edk2/edk2.git-ovmf-x64-0-20231115.1699.gc4e558ebf9.EOL.noarch.rpm"

        echo -e "${CYAN}Downloading OVMF RPM package...${NC}"
        if command -v wget &>/dev/null; then
            wget -q --show-progress "$RPM_URL" -O ovmf.rpm || {
                echo -e "${RED}Download failed. Try option 2 or 4.${NC}"
                exit 1
            }
        elif command -v curl &>/dev/null; then
            curl -L -# "$RPM_URL" -o ovmf.rpm || {
                echo -e "${RED}Download failed. Try option 2 or 4.${NC}"
                exit 1
            }
        else
            echo -e "${RED}Need wget or curl to download${NC}"
            exit 1
        fi

        echo -e "\n${CYAN}Extracting files...${NC}"

        # Check for extraction tools
        if command -v rpm2cpio &>/dev/null && command -v cpio &>/dev/null; then
            rpm2cpio ovmf.rpm | cpio -idmv 2>&1 | grep -i "OVMF" || true
        elif command -v bsdtar &>/dev/null; then
            bsdtar -xf ovmf.rpm 2>&1 | grep -i "OVMF" || true
        else
            echo -e "${RED}Need rpm2cpio+cpio or bsdtar to extract${NC}"
            echo -e "${YELLOW}Install: sudo dnf install rpmdevtools cpio bsdtar${NC}"
            exit 1
        fi

        # Find extracted VARS files
        echo -e "\n${CYAN}Locating VARS.secboot files...${NC}"

        EXTRACTED_VARS=$(find . -type f -name "*VARS*.fd" | grep -i secboot | head -1)

        if [ -z "$EXTRACTED_VARS" ]; then
            echo -e "${YELLOW}Secboot VARS not found, checking for enrolled VARS...${NC}"
            EXTRACTED_VARS=$(find . -type f -name "*VARS*.fd" | grep -v CODE | head -1)
        fi

        if [ -z "$EXTRACTED_VARS" ]; then
            echo -e "${RED}Could not find VARS files in package${NC}"
            echo -e "\n${YELLOW}Contents:${NC}"
            find . -name "*.fd" -ls
            exit 1
        fi

        echo -e "${GREEN}Found: $EXTRACTED_VARS${NC}"

        # Determine target filename
        if [[ "$EXTRACTED_VARS" =~ "4m" ]] || [ $(stat -c%s "$EXTRACTED_VARS") -gt 1000000 ]; then
            TARGET="$X64_DIR/OVMF_VARS.secboot.4m.fd"
        else
            TARGET="$X64_DIR/OVMF_VARS.secboot.fd"
        fi

        # Install
        echo -e "\n${CYAN}Installing to: $TARGET${NC}"
        cp "$EXTRACTED_VARS" "$TARGET"
        chmod 644 "$TARGET"

        # Cleanup
        cd /
        rm -rf "$WORK_DIR"

        echo -e "\n${GREEN}════════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}✓ Installation successful!${NC}"
        echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}\n"

        echo -e "${YELLOW}Installed file:${NC}"
        echo -e "  ${CYAN}$TARGET${NC}"
        echo -e "  Size: $(stat -c%s "$TARGET" | numfmt --to=iec-i --suffix=B)"
        echo
        echo -e "${YELLOW}Use this path in your VM NVRAM template configuration.${NC}\n"
        ;;

    2)
        echo -e "${BLUE}Downloading from Fedora repository...${NC}\n"

        WORK_DIR="/tmp/ovmf-fedora-$$"
        mkdir -p "$WORK_DIR"
        cd "$WORK_DIR"

        # Fedora 39 edk2-ovmf
        RPM_URL="https://dl.fedoraproject.org/pub/fedora/linux/releases/39/Everything/x86_64/os/Packages/e/edk2-ovmf-20231115-5.fc39.noarch.rpm"

        echo -e "${CYAN}Downloading Fedora OVMF package...${NC}"
        if command -v wget &>/dev/null; then
            wget -q --show-progress "$RPM_URL" -O ovmf.rpm || {
                echo -e "${RED}Download failed${NC}"
                exit 1
            }
        elif command -v curl &>/dev/null; then
            curl -L -# "$RPM_URL" -o ovmf.rpm || {
                echo -e "${RED}Download failed${NC}"
                exit 1
            }
        fi

        echo -e "\n${CYAN}Extracting...${NC}"
        if command -v rpm2cpio &>/dev/null; then
            rpm2cpio ovmf.rpm | cpio -idmv 2>&1 | grep -i "OVMF" || true
        elif command -v bsdtar &>/dev/null; then
            bsdtar -xf ovmf.rpm
        fi

        # Fedora typically puts them in usr/share/edk2/ovmf
        EXTRACTED_VARS=$(find . -path "*/edk2/ovmf/*" -name "*VARS*.fd" | grep -i secboot | head -1)

        if [ -z "$EXTRACTED_VARS" ]; then
            EXTRACTED_VARS=$(find . -name "*VARS*.fd" | head -1)
        fi

        if [ -n "$EXTRACTED_VARS" ]; then
            if [[ "$EXTRACTED_VARS" =~ "4m" ]]; then
                TARGET="$X64_DIR/OVMF_VARS.secboot.4m.fd"
            else
                TARGET="$X64_DIR/OVMF_VARS.secboot.fd"
            fi

            cp "$EXTRACTED_VARS" "$TARGET"
            chmod 644 "$TARGET"

            cd /
            rm -rf "$WORK_DIR"

            echo -e "\n${GREEN}✓ Installed: $TARGET${NC}"
            echo -e "  Size: $(stat -c%s "$TARGET" | numfmt --to=iec-i --suffix=B)\n"
        else
            echo -e "${RED}Could not find VARS in package${NC}"
            exit 1
        fi
        ;;

    3)
        echo -e "${CYAN}Checking Fedora repositories for OVMF packages...${NC}\n"
        echo -e "  ${CYAN}dnf search ovmf secureboot${NC}"
        dnf search ovmf secureboot 2>/dev/null || true

        echo
        echo -e "${YELLOW}Look for packages containing 'secureboot' or 'enrolled'${NC}"
        exit 0
        ;;

    4)
        echo -e "${YELLOW}Manual installation${NC}"
        echo -e "\nOptions:"
        echo -e "  • Download from: https://www.kraxel.org/repos/jenkins/edk2/"
        echo -e "  • Or from: https://fedoraproject.org/"
        echo -e "  • Extract OVMF_VARS.secboot*.fd files"
        echo -e "  • Copy to: $X64_DIR/"
        exit 0
        ;;

    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

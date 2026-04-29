#!/bin/bash

# Diagnose Secure Boot Auto-Enrollment Failure
# Try alternative enrollment methods

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${RED}══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${RED}   Secure Boot Troubleshooting & Alternative Methods${NC}"
echo -e "${BOLD}${RED}══════════════════════════════════════════════════════════${NC}\n"

if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Run as root: sudo $0${NC}\n"
    exit 1
fi

echo -e "${BLUE}[1] Checking current VM configuration...${NC}\n"

virsh dumpxml Xbox > /tmp/xbox-check.xml

echo -e "${YELLOW}Current <os> section:${NC}"
grep -A 15 "<os" /tmp/xbox-check.xml | grep -B 15 "</os>"
echo

echo -e "${YELLOW}Checking for firmware features:${NC}"
if grep -q "enrolled-keys" /tmp/xbox-check.xml; then
    echo -e "  ${GREEN}✓ enrolled-keys feature found${NC}"
else
    echo -e "  ${RED}✗ enrolled-keys feature NOT found${NC}"
fi

if grep -q 'firmware="efi"' /tmp/xbox-check.xml; then
    echo -e "  ${GREEN}✓ firmware='efi' attribute found${NC}"
else
    echo -e "  ${RED}✗ firmware='efi' attribute NOT found${NC}"
fi

echo -e "\n${BLUE}[2] Checking NVRAM file...${NC}\n"

NVRAM="/var/lib/libvirt/qemu/nvram/Xbox_VARS.fd"
if [ -f "$NVRAM" ]; then
    SIZE=$(stat -c%s "$NVRAM")
    echo -e "${YELLOW}NVRAM exists:${NC}"
    echo -e "  Path: $NVRAM"
    echo -e "  Size: $(numfmt --to=iec-i --suffix=B $SIZE)"
    echo -e "  Modified: $(stat -c%y "$NVRAM" | cut -d. -f1)"
else
    echo -e "${RED}NVRAM doesn't exist!${NC}"
fi

echo -e "\n${BOLD}${YELLOW}══════════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${YELLOW}   Alternative Solutions${NC}"
echo -e "${BOLD}${YELLOW}══════════════════════════════════════════════════════════${NC}\n"

echo -e "${CYAN}The auto-enrollment method failed. Here are alternatives:${NC}\n"

echo -e "${BOLD}Option 1: Download pre-enrolled VARS from working mirror${NC}"
echo -e "  I'll download from alternative sources"
echo

echo -e "${BOLD}Option 2: Use virt-firmware to enroll keys manually${NC}"
echo -e "  Install virt-firmware and enroll keys into existing NVRAM"
echo

echo -e "${BOLD}Option 3: Extract VARS from Ubuntu Cloud Images${NC}"
echo -e "  Ubuntu cloud images include enrolled OVMF files"
echo

echo -e "${BOLD}Option 4: Use EDK2 tools to manually enroll${NC}"
echo -e "  Most complex but most reliable"
echo

read -p "Choose option (1-4): " choice

case $choice in
    1)
        echo -e "\n${BLUE}Trying alternative download sources...${NC}\n"

        WORK_DIR="/tmp/ovmf-alt-$$"
        mkdir -p "$WORK_DIR"
        cd "$WORK_DIR"

        # Try multiple sources
        SOURCES=(
            "https://src.fedoraproject.org/repo/pkgs/edk2/edk2-ovmf-20231115-5.fc39.noarch.rpm/sha512/1a2b3c4d/edk2-ovmf-20231115-5.fc39.noarch.rpm"
            "https://rpmfind.net/linux/fedora/linux/releases/39/Everything/x86_64/os/Packages/e/edk2-ovmf-20231115-5.fc39.noarch.rpm"
            "https://download-ib01.fedoraproject.org/pub/fedora/linux/releases/39/Everything/x86_64/os/Packages/e/edk2-ovmf-20231115-5.fc39.noarch.rpm"
        )

        SUCCESS=false
        for url in "${SOURCES[@]}"; do
            echo -e "${CYAN}Trying: $url${NC}"
            if wget -q --timeout=30 --tries=2 "$url" -O ovmf.rpm 2>/dev/null; then
                echo -e "${GREEN}✓ Download successful${NC}"
                SUCCESS=true
                break
            fi
        done

        if [ "$SUCCESS" = false ]; then
            echo -e "${RED}All download sources failed${NC}"
            echo -e "${YELLOW}Trying direct file download...${NC}"

            # Try getting just the VARS file directly from GitHub mirrors
            VARS_URL="https://github.com/pftf/RPi4/raw/master/firmware/OVMF_VARS.fd"
            if wget -q "$VARS_URL" -O OVMF_VARS.fd; then
                cp OVMF_VARS.fd /usr/share/edk2/x64/OVMF_VARS.secboot.4m.fd
                chmod 644 /usr/share/edk2/x64/OVMF_VARS.secboot.4m.fd
                echo -e "${GREEN}✓ Installed VARS file${NC}"
            else
                echo -e "${RED}Failed to download${NC}"
                exit 1
            fi
        else
            # Extract the RPM
            if command -v bsdtar &>/dev/null; then
                bsdtar -xf ovmf.rpm
            elif command -v rpm2cpio &>/dev/null; then
                rpm2cpio ovmf.rpm | cpio -idmv 2>&1 | grep OVMF
            fi

            # Find and install VARS
            VARS=$(find . -name "*VARS*.fd" | head -1)
            if [ -n "$VARS" ]; then
                cp "$VARS" /usr/share/edk2/x64/OVMF_VARS.secboot.4m.fd
                chmod 644 /usr/share/edk2/x64/OVMF_VARS.secboot.4m.fd
                echo -e "${GREEN}✓ Installed: /usr/share/edk2/x64/OVMF_VARS.secboot.4m.fd${NC}"
            fi
        fi

        cd /
        rm -rf "$WORK_DIR"

        # Now update VM to use it
        echo -e "\n${BLUE}Updating VM configuration...${NC}"
        virsh shutdown Xbox 2>/dev/null
        sleep 3
        rm -f /var/lib/libvirt/qemu/nvram/Xbox_VARS.fd

        # Update XML to use secboot VARS
        sed -i 's|template="/usr/share/edk2/x64/OVMF_VARS.4m.fd"|template="/usr/share/edk2/x64/OVMF_VARS.secboot.4m.fd"|g' /tmp/xbox-check.xml
        virsh define /tmp/xbox-check.xml
        virsh start Xbox

        echo -e "${GREEN}✓ VM restarted with enrolled VARS${NC}"
        ;;

    2)
        echo -e "\n${BLUE}Checking for virt-firmware...${NC}"
        if ! command -v virt-fw-vars &>/dev/null; then
            echo -e "${RED}✗ virt-firmware is missing! Must be installed via PACKAGES.md.${NC}"
            exit 1
        fi

        echo -e "\n${BLUE}Enrolling Microsoft keys...${NC}"
        virsh shutdown Xbox 2>/dev/null
        sleep 3

        # Enroll keys into existing NVRAM
        virt-fw-vars --input /var/lib/libvirt/qemu/nvram/Xbox_VARS.fd \
                     --output /var/lib/libvirt/qemu/nvram/Xbox_VARS.fd \
                     --enroll-redhat \
                     --secure-boot

        virsh start Xbox
        echo -e "${GREEN}✓ Keys enrolled${NC}"
        ;;

    3)
        echo -e "\n${BLUE}Downloading from Ubuntu Cloud Images...${NC}"

        WORK_DIR="/tmp/ubuntu-ovmf-$$"
        mkdir -p "$WORK_DIR"
        cd "$WORK_DIR"

        # Ubuntu has enrolled OVMF in their cloud images package
        wget http://archive.ubuntu.com/ubuntu/pool/main/e/edk2/ovmf_2023.05-2ubuntu0.1_all.deb

        ar x ovmf_*.deb
        tar -xf data.tar.xz

        VARS=$(find . -name "*VARS.ms.fd" -o -name "*VARS*.fd" | head -1)
        if [ -n "$VARS" ]; then
            cp "$VARS" /usr/share/edk2/x64/OVMF_VARS.secboot.4m.fd
            chmod 644 /usr/share/edk2/x64/OVMF_VARS.secboot.4m.fd

            cd /
            rm -rf "$WORK_DIR"

            # Update VM
            virsh shutdown Xbox 2>/dev/null
            sleep 3
            rm -f /var/lib/libvirt/qemu/nvram/Xbox_VARS.fd
            sed -i 's|template="/usr/share/edk2/x64/OVMF_VARS.4m.fd"|template="/usr/share/edk2/x64/OVMF_VARS.secboot.4m.fd"|g' /tmp/xbox-check.xml
            virsh define /tmp/xbox-check.xml
            virsh start Xbox

            echo -e "${GREEN}✓ Installed Ubuntu OVMF VARS${NC}"
        fi
        ;;

    4)
        echo -e "\n${YELLOW}Manual enrollment requires EDK2 build tools${NC}"
        echo -e "This is complex. Use option 1, 2, or 3 instead."
        ;;
esac

echo -e "\n${GREEN}Done! Check Windows again with msinfo32${NC}\n"

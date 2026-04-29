#!/bin/bash

# OVMF Firmware Discovery Script
# Finds all OVMF firmware files and identifies usable CODE/VARS pairs

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════${NC}"
echo -e "${BOLD}${GREEN}     OVMF Firmware Discovery Tool${NC}"
echo -e "${BOLD}${GREEN}════════════════════════════════════════════════════${NC}\n"

echo -e "${BLUE}Scanning for OVMF firmware files...${NC}\n"

# Find all OVMF files
OVMF_FILES=$(find /usr/share -name "OVMF*.fd" 2>/dev/null | sort)

if [ -z "$OVMF_FILES" ]; then
    echo -e "${RED}✗ No OVMF files found!${NC}\n"
    echo -e "${YELLOW}Ensure it is in PACKAGES.md: ${NC}${CYAN}edk2-ovmf${NC}\n"
    exit 1
fi

echo -e "${YELLOW}Found OVMF files:${NC}"
echo "$OVMF_FILES" | nl -w2 -s'. '
echo

# Group by directory
echo -e "\n${CYAN}════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Firmware Files by Directory:${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════${NC}\n"

DIRS=$(echo "$OVMF_FILES" | xargs dirname | sort -u)

for dir in $DIRS; do
    echo -e "${BOLD}$dir${NC}"
    ls -lh "$dir"/*.fd 2>/dev/null | awk '{printf "  %s  %s\n", $9, $5}'
    echo
done

# Identify CODE/VARS pairs
echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Identified CODE/VARS Pairs:${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════${NC}\n"

PAIR_COUNT=0

# Function to find matching VARS for a CODE file
find_vars_for_code() {
    local code_path=$1
    local dir=$(dirname "$code_path")
    local filename=$(basename "$code_path")

    # Try different patterns
    local vars_candidates=(
        "${filename/CODE/VARS}"
        "${filename/CODE.secboot/VARS.secboot}"
        "${filename/.secboot.4m.fd/.secboot.4m.fd}"
        "${filename/.4m.fd/.4m.fd}"
    )

    for candidate in "${vars_candidates[@]}"; do
        local vars_path="$dir/$candidate"
        if [ -f "$vars_path" ] && [[ "$vars_path" != "$code_path" ]]; then
            echo "$vars_path"
            return 0
        fi
    done

    # Try without exact pattern match
    for vars_file in "$dir"/OVMF_VARS*.fd; do
        if [ -f "$vars_file" ]; then
            # Check if size/type seems compatible
            echo "$vars_file"
            return 0
        fi
    done

    return 1
}

# Check each CODE file
echo "$OVMF_FILES" | grep "CODE" | while read -r code_file; do
    vars_file=$(find_vars_for_code "$code_file")

    if [ -n "$vars_file" ]; then
        PAIR_COUNT=$((PAIR_COUNT + 1))

        # Determine type
        TYPE="Standard"
        SECURE=""
        RECOMMENDED=""

        if [[ "$code_file" =~ "secboot" ]]; then
            TYPE="Secure Boot"
            SECURE="${GREEN}✓ Secure Boot Supported${NC}"
            if [[ "$code_file" =~ "4m" ]]; then
                RECOMMENDED="${BOLD}${GREEN}★ RECOMMENDED FOR WINDOWS 11 ★${NC}"
            else
                RECOMMENDED="${GREEN}★ GOOD FOR WINDOWS 11${NC}"
            fi
        fi

        if [[ "$code_file" =~ "4m" ]]; then
            SIZE="4MB"
        else
            SIZE="2MB"
        fi

        echo -e "${BOLD}Pair #$((PAIR_COUNT + 1)):${NC} ${SIZE} ${TYPE}"
        [ -n "$RECOMMENDED" ] && echo -e "  $RECOMMENDED"
        [ -n "$SECURE" ] && echo -e "  $SECURE"
        echo -e "  ${YELLOW}CODE:${NC} $code_file"
        echo -e "  ${YELLOW}VARS:${NC} $vars_file"
        echo
    fi
done

# Make recommendations
echo -e "${CYAN}════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Recommendations:${NC}"
echo -e "${CYAN}════════════════════════════════════════════════════${NC}\n"

# Find best option
BEST_CODE=""
BEST_VARS=""
RECOMMENDATION=""

# Priority 1: 4MB Secure Boot
for code_file in $(echo "$OVMF_FILES" | grep -i "CODE.secboot.4m.fd"); do
    vars_file=$(find_vars_for_code "$code_file")
    if [ -n "$vars_file" ] && [ -f "$vars_file" ]; then
        BEST_CODE="$code_file"
        BEST_VARS="$vars_file"
        RECOMMENDATION="${BOLD}${GREEN}4MB Secure Boot (BEST for Windows 11)${NC}"
        break
    fi
done

# Priority 2: 2MB Secure Boot
if [ -z "$BEST_CODE" ]; then
    for code_file in $(echo "$OVMF_FILES" | grep -i "CODE.secboot.fd" | grep -v "4m"); do
        vars_file=$(find_vars_for_code "$code_file")
        if [ -n "$vars_file" ] && [ -f "$vars_file" ]; then
            BEST_CODE="$code_file"
            BEST_VARS="$vars_file"
            RECOMMENDATION="${GREEN}2MB Secure Boot (GOOD for Windows 11)${NC}"
            break
        fi
    done
fi

# Priority 3: 4MB Standard
if [ -z "$BEST_CODE" ]; then
    for code_file in $(echo "$OVMF_FILES" | grep -i "CODE.4m.fd" | grep -v "secboot"); do
        vars_file=$(find_vars_for_code "$code_file")
        if [ -n "$vars_file" ] && [ -f "$vars_file" ]; then
            BEST_CODE="$code_file"
            BEST_VARS="$vars_file"
            RECOMMENDATION="${YELLOW}4MB Standard (No Secure Boot)${NC}"
            break
        fi
    done
fi

# Priority 4: 2MB Standard
if [ -z "$BEST_CODE" ]; then
    for code_file in $(echo "$OVMF_FILES" | grep -i "CODE.fd" | grep -v "4m" | grep -v "secboot"); do
        vars_file=$(find_vars_for_code "$code_file")
        if [ -n "$vars_file" ] && [ -f "$vars_file" ]; then
            BEST_CODE="$code_file"
            BEST_VARS="$vars_file"
            RECOMMENDATION="${YELLOW}2MB Standard (No Secure Boot)${NC}"
            break
        fi
    done
fi

if [ -n "$BEST_CODE" ] && [ -n "$BEST_VARS" ]; then
    echo -e "${BOLD}Recommended Configuration:${NC}"
    echo -e "  Type: $RECOMMENDATION"
    echo -e "  ${CYAN}CODE:${NC} $BEST_CODE"
    echo -e "  ${CYAN}VARS:${NC} $BEST_VARS"

    # Check if they actually exist and are readable
    if [ ! -f "$BEST_CODE" ]; then
        echo -e "  ${RED}✗ CODE file doesn't exist or isn't readable${NC}"
    else
        CODE_SIZE=$(stat -f%z "$BEST_CODE" 2>/dev/null || stat -c%s "$BEST_CODE" 2>/dev/null)
        echo -e "  ${GREEN}✓ CODE file exists ($(numfmt --to=iec-i --suffix=B $CODE_SIZE))${NC}"
    fi

    if [ ! -f "$BEST_VARS" ]; then
        echo -e "  ${RED}✗ VARS file doesn't exist or isn't readable${NC}"
    else
        VARS_SIZE=$(stat -f%z "$BEST_VARS" 2>/dev/null || stat -c%s "$BEST_VARS" 2>/dev/null)
        echo -e "  ${GREEN}✓ VARS file exists ($(numfmt --to=iec-i --suffix=B $VARS_SIZE))${NC}"
    fi

    echo
    echo -e "${BOLD}XML Configuration Snippet:${NC}"
    echo -e "${CYAN}────────────────────────────────────────────────────${NC}"

    SECURE_ATTR="no"
    if [[ "$BEST_CODE" =~ "secboot" ]]; then
        SECURE_ATTR="yes"
    fi

    cat << XMLSNIPPET
  <os>
    <type arch="x86_64" machine="pc-q35-10.1">hvm</type>
    <loader readonly="yes" secure="$SECURE_ATTR" type="pflash">$BEST_CODE</loader>
    <nvram template="$BEST_VARS">/var/lib/libvirt/qemu/nvram/Xbox_VARS.fd</nvram>
    <bootmenu enable="yes"/>
  </os>
XMLSNIPPET
    echo -e "${CYAN}────────────────────────────────────────────────────${NC}"

    # Save to file
    cat > /tmp/ovmf-paths.txt << EOF
# OVMF Firmware Paths for Xbox VM
# Generated: $(date)

CODE_PATH=$BEST_CODE
VARS_PATH=$BEST_VARS
SECURE_BOOT=$SECURE_ATTR
TYPE=$RECOMMENDATION

# Use these in your VM XML:
# <loader readonly="yes" secure="$SECURE_ATTR" type="pflash">$BEST_CODE</loader>
# <nvram template="$BEST_VARS">/var/lib/libvirt/qemu/nvram/Xbox_VARS.fd</nvram>
EOF

    echo
    echo -e "${GREEN}✓ Paths saved to: ${NC}${CYAN}/tmp/ovmf-paths.txt${NC}"

else
    echo -e "${RED}✗ Could not find a usable CODE/VARS pair!${NC}"
    echo -e "${YELLOW}This might indicate:${NC}"
    echo -e "  1. edk2-ovmf package not installed"
    echo -e "  2. Files are in an unexpected location"
    echo -e "  3. Package is corrupted"
    echo
    echo -e "${YELLOW}Ensure it is in PACKAGES.md: ${NC}${CYAN}edk2-ovmf${NC}"
fi

echo -e "\n${BOLD}${GREEN}════════════════════════════════════════════════════${NC}\n"

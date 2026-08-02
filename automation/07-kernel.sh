#!/bin/bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Installs kernel-devel, headers, and extra modules (VFIO, USB, storage) required for akmod-nvidia, DKMS, and kernel-tools while avoiding base kernel upgrades that break dracut.
# AI-related: mios-kver
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

install_packages "kernel"

KVER=$(find /usr/lib/modules/ -mindepth 1 -maxdepth 1 -printf "%f\n" | sort -V | tail -1) # Explicitly use /usr
export KVER
mios_log "Kernel version: $KVER"
echo "$KVER" > /tmp/mios-kver

if [[ ! -d "/usr/lib/modules/$KVER" ]]; then # Explicitly check /usr
    mios_err "/usr/lib/modules/$KVER does not exist" # Explicitly refer to /usr
    exit 1
fi

if [[ ! -d "/usr/lib/modules/$KVER/build" ]]; then
    mios_warn "/usr/lib/modules/$KVER/build missing"
fi

mios_ok "Kernel extras for $KVER installed"

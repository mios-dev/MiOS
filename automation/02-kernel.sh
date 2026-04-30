#!/bin/bash
# MiOS v0.2.0 — 02-kernel: Kernel extras + development headers
# The base fedora-bootc:rawhide image ships the newest kernel with a working
# initramfs. We NEVER upgrade the base kernel packages inside the container —
# doing so triggers dracut under the tmpfs mount, which fails with
# "Invalid cross-device link (os error 18)" and produces a broken initramfs.
#
# This script installs ONLY the extras needed for:
#   - akmod-nvidia (kernel-devel, kernel-headers)
#   - DKMS/kvmfr (kernel-devel)
#   - kernel-modules-extra (VFIO, USB, storage modules not in base)
#   - kernel-tools (cpupower, turbostat, perf)
#
# CHANGELOG v0.2.0:
#   - REMOVED kernel/kernel-core/kernel-modules/kernel-modules-core
#     (base image already has them — upgrading broke dracut)
#   - kernel-modules-extra ensures VFIO/USB/storage modules are present
#   - kernel-devel enables akmod-nvidia and DKMS builds
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/packages.sh"

install_packages_strict "kernel"

# Capture KVER for akmod builds later.
# The base image kernel is the only one installed; grab it.
KVER=$(find /usr/lib/modules/ -mindepth 1 -maxdepth 1 -printf "%f\n" | sort -V | tail -1) # Explicitly use /usr
export KVER
echo "[02-kernel] Kernel version: $KVER"
echo "$KVER" > /tmp/mios-kver

# Verify kernel modules directory exists (akmod build will fail without it)
if [[ ! -d "/usr/lib/modules/$KVER" ]]; then # Explicitly check /usr
    echo "[02-kernel] FATAL: /usr/lib/modules/$KVER does not exist" # Explicitly refer to /usr
    exit 1
fi

# Verify kernel-devel is installed (akmod-nvidia needs it)
if [[ ! -d "/usr/lib/modules/$KVER/build" ]]; then
    echo "[02-kernel] WARNING: /usr/lib/modules/$KVER/build missing — akmod may fail"
fi

echo "[02-kernel] Kernel extras for $KVER installed successfully."

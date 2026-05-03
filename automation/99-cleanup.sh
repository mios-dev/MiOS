#!/bin/bash
# 'MiOS' v0.2.0 -- 99-cleanup: Final image cleanup (mirrors ucore/cleanup.sh)
#
# MANDATORY for bootc images. Every ublue-os image runs this pattern.
# Without it, BIB deployment fails or the booted system has broken /var state.
#
# v0.2.0: Added targeted lint cleanup for dnf5.log, ldconfig aux-cache,
# and any stray files in /var that trigger bootc container lint warnings.
#
# Reference: https://github.com/ublue-os/ucore/blob/main/cleanup.sh
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh"

echo "[99-cleanup] Running final image cleanup..."

# 1. Clean /boot -- BIB generates fresh bootloader, stale content causes conflicts
echo "[99-cleanup] Cleaning /boot..."
find /boot/ -maxdepth 1 -mindepth 1 -exec rm -fr {} \; || true

# 2. Clean /var -- bootc treats /var as persistent state (like Docker VOLUME)
# We remove content but KEEP directories to preserve permissions/labels.
echo "[99-cleanup] Cleaning /var content (preserving structure)..."
# Remove all files and subdirs in /var/tmp and /var/log
rm -rf /var/tmp/* /var/log/* 2>/dev/null || true
# Clean /var/lib excluding critical paths if any (mostly dnf/rpm-ostree cache)
find /var/cache/* -maxdepth 0 -type d \! -name libdnf5 \! -name rpm-ostree -exec rm -fr {} \; 2>/dev/null || true

# 3. Lint-specific cleanup: remove files that trigger bootc container lint warnings
echo "[99-cleanup] Cleaning lint triggers..."
rm -f /var/log/lastlog /var/log/dnf5.log* 2>/dev/null || true
rm -rf /var/cache/ldconfig 2>/dev/null || true
rm -f /var/lib/systemd/random-seed 2>/dev/null || true
# 'MiOS' v0.2.0: additional lint cleanup based on Cloud Build observations
rm -rf /var/lib/glusterd 2>/dev/null || true
rm -f /var/lib/containers/storage/db.sql 2>/dev/null || true
rm -f /var/lib/flatpak/.changed 2>/dev/null || true
rm -rf /var/lib/flatpak/repo/tmp/* 2>/dev/null || true

# 4. Restore system skeleton via systemd-tmpfiles
# This ensures all /var and /tmp directories exist with correct metadata.
echo "[99-cleanup] Restoring system skeleton..."
systemd-tmpfiles --create --boot --root=/ 2>/dev/null || true

# 5. Clean DNF caches
echo "[99-cleanup] Cleaning package manager caches..."
$DNF_BIN "${DNF_SETOPT[@]}" clean all 2>/dev/null || true

echo "[99-cleanup] [ok] Image cleanup complete"

#!/bin/bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Final image build script that purges stale boot files, clears /var/log and /var/cache, and removes specific files triggering bootc container lint warnings to ensure a clean, deployable system state.
set -euo pipefail

for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

source "$(dirname "$0")/lib/common.sh"

mios_log "Final image cleanup"

mios_log "Cleaning /boot"
find /boot/ -maxdepth 1 -mindepth 1 -exec rm -fr {} \; || true

mios_log "Cleaning /var content"
rm -rf /var/tmp/* /var/log/* 2>/dev/null || true
find /var/cache/* -maxdepth 0 -type d \! -name libdnf5 \! -name rpm-ostree -exec rm -fr {} \; 2>/dev/null || true

mios_log "Cleaning lint triggers"
rm -f /var/log/lastlog /var/log/dnf5.log* 2>/dev/null || true
rm -rf /var/cache/ldconfig 2>/dev/null || true
rm -f /var/lib/systemd/random-seed 2>/dev/null || true
rm -rf /var/lib/glusterd 2>/dev/null || true
rm -f /var/lib/containers/storage/db.sql 2>/dev/null || true
rm -f /var/lib/flatpak/.changed 2>/dev/null || true
rm -rf /var/lib/flatpak/repo/tmp/* 2>/dev/null || true

mios_log "Restoring system skeleton"
systemd-tmpfiles --create --boot --root=/ 2>/dev/null || true

mios_log "Cleaning package manager caches"
$DNF_BIN "${DNF_SETOPT[@]}" clean all 2>/dev/null || true

mios_ok "Image cleanup"

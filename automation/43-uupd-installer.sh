#!/usr/bin/env bash
# AI-hint: Installs the uupd and greenboot packages, enables the uupd.timer, and disables superseded update timers (bootc-fetch-apply-updates and rpm-ostreed-automatic) to configure the system's update mechanism.
# AI-related: uupd.timer, bootc-fetch-apply-updates.timer, rpm-ostreed-automatic.timer, multi-user.target
# 43-uupd-installer.sh - install uupd + greenboot (from mios.toml
# [packages.updater]) and disable the updaters it supersedes.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/common.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/lib/packages.sh"

# COPR already enabled by 05-enable-external-repos.sh (runs earlier)
install_packages "updater"

# Disable the updaters uupd supersedes
systemctl disable bootc-fetch-apply-updates.timer 2>/dev/null || true
systemctl disable rpm-ostreed-automatic.timer     2>/dev/null || true

# Enable uupd.timer (shipped by the package)
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"
if [[ -f "/usr/lib/systemd/system/uupd.timer" ]]; then
    ln -sf ../uupd.timer "${WANTS}/uupd.timer"
    log "Enabled uupd.timer"
else
    warn "uupd.timer not present (uupd install may have failed)"
fi

log "uupd configured; bootc-fetch-apply-updates.timer and rpm-ostreed-automatic.timer disabled"
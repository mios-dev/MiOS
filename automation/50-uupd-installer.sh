#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Installs the uupd and greenboot packages, enables the uupd.timer, and disables superseded update timers (bootc-fe...
# AI-doc: usr/share/doc/mios/manual/automation.md
set -euo pipefail

for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/packages.sh"

install_packages "updater" || true

WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

if [[ -f "/usr/lib/systemd/system/uupd.timer" ]]; then
    ln -sf ../uupd.timer "${WANTS}/uupd.timer"
    systemctl disable bootc-fetch-apply-updates.timer 2>/dev/null || true
    systemctl disable rpm-ostreed-automatic.timer     2>/dev/null || true
    mios_ok "Uupd.timer enabled as primary OS update timer"
elif [[ -f "/usr/lib/systemd/system/bootc-fetch-apply-updates.timer" || -f "/usr/lib/systemd/system/bootc-fetch-apply-updates.service" ]]; then
    if [[ -f "/usr/lib/systemd/system/bootc-fetch-apply-updates.timer" ]]; then
        ln -sf ../bootc-fetch-apply-updates.timer "${WANTS}/bootc-fetch-apply-updates.timer"
    fi
    systemctl disable rpm-ostreed-automatic.timer 2>/dev/null || true
    mios_ok "bootc-fetch-apply-updates.timer enabled as primary OS update timer"
else
    mios_err "FATAL: No OS update mechanism available (neither uupd.timer nor bootc-fetch-apply-updates.timer present)"
    exit 1
fi

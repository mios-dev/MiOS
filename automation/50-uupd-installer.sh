#!/usr/bin/env bash
# AI-hint: bash MIOS_APPLY_CLASS=universal Installs the uupd and greenboot packages, enables the uupd.timer, and disables superseded update timers (bootc-fe...
# AI-doc: usr/share/doc/mios/manual/_harvest/automation_50_uupd_installer_sh.md
set -euo pipefail

for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/packages.sh"

install_packages "updater"

systemctl disable bootc-fetch-apply-updates.timer 2>/dev/null || true
systemctl disable rpm-ostreed-automatic.timer     2>/dev/null || true

WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"
if [[ -f "/usr/lib/systemd/system/uupd.timer" ]]; then
    ln -sf ../uupd.timer "${WANTS}/uupd.timer"
    mios_ok "Uupd.timer enabled"
else
    mios_warn "Uupd.timer not present"
fi

mios_ok "Uupd configured; bootc-fetch-apply-updates.timer and rpm-ostreed-automatic.timer disabled"

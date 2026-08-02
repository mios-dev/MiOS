#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Configures fapolicyd to use file-based trust (fs-verity) to enable secure, immutable application whitelisting on ComposeFS systems without boot delays.
# AI-related: fapolicyd.service
set -euo pipefail

for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

mios_log "Set fapolicyd trust = file,rpmdb in /usr/lib and /etc fapolicyd.conf"

source "$(dirname "$0")/lib/common.sh"

if command -v miosd >/dev/null 2>&1; then
    miosd harden
    mios_ok "Fapolicyd trust configured via miosd"
    exit 0
fi

for config in /usr/lib/fapolicyd/fapolicyd.conf /etc/fapolicyd/fapolicyd.conf; do
    if [[ -f "$config" ]]; then
        sed -i 's/^trust =.*/trust = file,rpmdb/' "$config" || true
    fi
done

systemctl enable fapolicyd.service
mios_ok "Trust = file,rpmdb set in fapolicyd.conf, fapolicyd.service enabled"

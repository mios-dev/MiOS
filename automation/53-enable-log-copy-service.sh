#!/usr/bin/env bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Enables the mios-copy-build-log.service systemd unit by creating a symbolic link in multi-user.target.wants to ensure build logs are automatically copied during system startup.
# AI-related: mios-copy-build-log, mios-copy-build-log.service, multi-user.target
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

WANTS=/usr/lib/systemd/system/multi-user.target.wants
mios_log "symlinking mios-copy-build-log.service into ${WANTS}"

install -d -m 0755 "${WANTS}"

if [[ -f "/usr/lib/systemd/system/mios-copy-build-log.service" ]]; then
    ln -sf ../mios-copy-build-log.service "${WANTS}/mios-copy-build-log.service"
    mios_ok "enabled mios-copy-build-log.service"
else
    mios_warn "mios-copy-build-log.service not found, skipping"
fi

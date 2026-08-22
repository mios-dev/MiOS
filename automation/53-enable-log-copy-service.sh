#!/usr/bin/env bash
# AI-hint: bash MIOS_APPLY_CLASS=bake-only Enables the mios-copy-build-log.service systemd unit by creating a symbolic link in multi-user.target.wa...
# AI-doc: usr/share/doc/mios/manual/_harvest/automation_53_enable_log_copy_service_sh.md
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

WANTS=/usr/lib/systemd/system/multi-user.target.wants
mios_log "Symlinking mios-copy-build-log.service into ${WANTS}"

install -d -m 0755 "${WANTS}"

if [[ -f "/usr/lib/systemd/system/mios-copy-build-log.service" ]]; then
    ln -sf ../mios-copy-build-log.service "${WANTS}/mios-copy-build-log.service"
    mios_ok "Enabled mios-copy-build-log.service"
else
    mios_warn "Mios-copy-build-log.service not found, skipping"
fi

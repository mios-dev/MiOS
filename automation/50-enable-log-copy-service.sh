#!/usr/bin/env bash
# AI-hint: Enables the mios-copy-build-log.service systemd unit by creating a symbolic link in multi-user.target.wants to ensure build logs are automatically copied during system startup.
# AI-related: mios-copy-build-log, mios-copy-build-log.service, multi-user.target
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

log "Enabling 'MiOS' build log copy service..."

WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

if [[ -f "/usr/lib/systemd/system/mios-copy-build-log.service" ]]; then
    ln -sf ../mios-copy-build-log.service "${WANTS}/mios-copy-build-log.service"
    log "Enabled mios-copy-build-log.service"
else
    warn "mios-copy-build-log.service not found, skipping enablement."
fi

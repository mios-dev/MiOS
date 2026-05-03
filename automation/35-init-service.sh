#!/usr/bin/env bash
# 'MiOS' v0.2.0 -- 35-init-service: Bridge to Unified Role Engine
# This script ensures mios-role.service is correctly enabled.
# The actual logic lives in /usr/libexec/mios/role-apply (system_files overlay).
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

log "Enabling unified system initialization..."

# Enable units using build-safe symlinks
WANTS=/usr/lib/systemd/system/multi-user.target.wants
install -d -m 0755 "${WANTS}"

for unit in \
    mios-role.service \
    mios-podman-gc.timer
do
    if [[ -f "/usr/lib/systemd/system/${unit}" ]]; then
        ln -sf "../${unit}" "${WANTS}/${unit}"
        log "Enabled ${unit}"
    else
        warn "${unit} not found, skipping enablement."
    fi
done

log "Initialization system services enabled."

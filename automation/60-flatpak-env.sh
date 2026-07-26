#!/bin/bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Captures the MIOS_FLATPAKS build-time variable into a system-level environment file at ${MIOS_USR_DIR}/env.d/flatpaks.env to be consumed by the mios-flatpak-install tool during boot-time setup.
# AI-related: /usr/lib/mios/env.d, mios-flatpak-install
# 'MiOS' - 37-flatpak-env: Capture Flatpak environment for boot-time install
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done
source "$(dirname "${BASH_SOURCE[0]}")/lib/common.sh"

mios_log "capturing Flatpak environment"

# Directory for 'MiOS' system-level environment definitions (USR-OVER-ETC compliance)
# Using /usr/lib/mios/env.d as a "venv/env" style storage
mkdir -p ${MIOS_USR_DIR}/env.d

# Capture MIOS_FLATPAKS if set (from build-arg)
# This creates a system-baked environment file that mios-flatpak-install can read.
ENV_FILE="${MIOS_USR_DIR}/env.d/flatpaks.env"

echo "# 'MiOS' System Environment Definition" > "$ENV_FILE"
echo "# Generated at build time: $(date -u)" >> "$ENV_FILE"

if [[ -n "${MIOS_FLATPAKS:-}" ]]; then
    echo "MIOS_FLATPAKS=\"${MIOS_FLATPAKS}\"" >> "$ENV_FILE"
    mios_ok "captured MIOS_FLATPAKS to ${ENV_FILE}"
else
    echo "MIOS_FLATPAKS=\"\"" >> "$ENV_FILE"
    mios_skip "MIOS_FLATPAKS not set, created empty env file"
fi

chmod 644 "$ENV_FILE"

mios_ok "Flatpak environment configured in /usr"

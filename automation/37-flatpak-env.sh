#!/bin/bash
# MiOS v0.2.0  37-flatpak-env: Capture Flatpak environment for boot-time install
set -euo pipefail

echo "?"
echo "  MiOS v0.2.0  Flatpak Environment"
echo "?"

# Directory for MiOS system-level environment definitions (USR-OVER-ETC compliance)
# Using /usr/lib/mios/env.d as a "venv/env" style storage
mkdir -p /usr/lib/mios/env.d

# Capture MIOS_FLATPAKS if set (from build-arg)
# This creates a system-baked environment file that mios-flatpak-install can read.
ENV_FILE="/usr/lib/mios/env.d/flatpaks.env"

echo "# MiOS System Environment Definition" > "$ENV_FILE"
echo "# Generated at build time: $(date -u)" >> "$ENV_FILE"

if [[ -n "${MIOS_FLATPAKS:-}" ]]; then
    echo "MIOS_FLATPAKS=\"${MIOS_FLATPAKS}\"" >> "$ENV_FILE"
    echo "[37-flatpak-env] Captured MIOS_FLATPAKS to ${ENV_FILE}"
else
    echo "MIOS_FLATPAKS=\"\"" >> "$ENV_FILE"
    echo "[37-flatpak-env] MIOS_FLATPAKS not set, created empty env file."
fi

chmod 644 "$ENV_FILE"

echo "[37-flatpak-env] Flatpak environment configured in /usr."

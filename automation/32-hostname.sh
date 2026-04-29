#!/bin/bash
# MiOS v0.1.1 — 32-hostname: Unique per-instance hostname
#
# Strategy: Set a template hostname in the image. On first boot, systemd
# generates /etc/machine-id. The mios-init service (35-init-service.sh)
# derives a stable 5-char tag from machine-id and sets the hostname.
#
# Result: Each instance gets mios-XXXXX (e.g., mios-a3f9c), unique
# per deployment, stable across reboots.
set -euo pipefail

echo "[32-hostname] Setting default hostname template..."

# Use MIOS_HOSTNAME build-arg if provided by the installer/bootstrap.
# When set (e.g. "kabu-ws-83427"), it becomes the static hostname.
# When unset (default "mios"), the first-boot mios-init derives mios-XXXXX
# from machine-id so every deployment still gets a unique hostname.
_hn="${MIOS_HOSTNAME:-mios}"
echo "$_hn" > /etc/hostname
echo "[32-hostname] Hostname set to: $_hn"
if [[ "$_hn" == "mios" ]]; then
    echo "[32-hostname] Will become mios-XXXXX on first boot via mios-init."
fi

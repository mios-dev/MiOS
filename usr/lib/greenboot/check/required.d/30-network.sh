#!/bin/bash
# AI-hint: Validates DNS reachability for ghcr.io via systemd-resolve during greenboot; if resolution fails within 30s, it triggers a system rollback to prevent boot failures due to broken networking.
# AI-related: mios-greenboot
set -euo pipefail

TIMEOUT=30
REGISTRY_HOST="ghcr.io"

echo "[mios-greenboot] Checking DNS reachability of ${REGISTRY_HOST}"

deadline=$(( $(date +%s) + TIMEOUT ))
while true; do
    if systemd-resolve "${REGISTRY_HOST}" >/dev/null 2>&1; then
        echo "[mios-greenboot] DNS OK: ${REGISTRY_HOST} resolved successfully"
        exit 0
    fi
    if [[ $(date +%s) -ge $deadline ]]; then
        echo "[mios-greenboot] FAIL: DNS resolution of ${REGISTRY_HOST} timed out after ${TIMEOUT}s" >&2
        exit 1
    fi
    sleep 2
done

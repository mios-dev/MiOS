#!/bin/bash
# 'MiOS' greenboot -- required network reachability check
# Fails if DNS resolution is broken after a boot, triggering rollback
# after GREENBOOT_MAX_BOOT_ATTEMPTS consecutive failures.
#
# Uses systemd-resolve (always present on ucore-hci / Fedora) rather than
# curl/wget to avoid dependencies on those tools being present at check time.
set -euo pipefail

TIMEOUT=30
REGISTRY_HOST="ghcr.io"

echo "[mios-greenboot] Checking DNS reachability of ${REGISTRY_HOST}..."

# Wait up to TIMEOUT seconds for DNS to become available
deadline=$(( $(date +%s) + TIMEOUT ))
while true; do
    if systemd-resolve "${REGISTRY_HOST}" >/dev/null 2>&1; then
        echo "[mios-greenboot] DNS OK: ${REGISTRY_HOST} resolved successfully."
        exit 0
    fi
    if [[ $(date +%s) -ge $deadline ]]; then
        echo "[mios-greenboot] FAIL: DNS resolution of ${REGISTRY_HOST} timed out after ${TIMEOUT}s." >&2
        exit 1
    fi
    sleep 2
done

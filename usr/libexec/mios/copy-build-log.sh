#!/bin/bash
# 'MiOS' Build Log Copy Service
# Preserves build-time logs for post-deployment diagnostics.
set -euo pipefail
# shellcheck source=/usr/lib/mios/paths.sh
source /usr/lib/mios/paths.sh

LOG_DIR="${MIOS_LOG_DIR}"
PERSISTENT_LOG="/var/log/mios/last-build.log"

echo "[copy-build-log] Starting log preservation..."

if [[ -d "$LOG_DIR" ]]; then
    mkdir -p "$(dirname "$PERSISTENT_LOG")"
    # Find the latest build log in the immutable store
    LATEST_LOG=$(ls -t "$LOG_DIR"/mios-build.log 2>/dev/null | head -n 1)
    if [[ -n "$LATEST_LOG" ]]; then
        cp "$LATEST_LOG" "$PERSISTENT_LOG"
        echo "[copy-build-log] Copied $LATEST_LOG to $PERSISTENT_LOG"
    else
        echo "[copy-build-log] No build log found in $LOG_DIR"
    fi
else
    echo "[copy-build-log] Log directory $LOG_DIR not found"
fi

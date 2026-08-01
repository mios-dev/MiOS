#!/bin/bash
# AI-hint: A shell script that preserves the most recent build logs from the immutable storage directory to /var/log/mios/last-build.log for post-deployment diagnostics.
# AI-related: /usr/lib/mios/paths.sh, mios-build, mios-build-chain
set -euo pipefail
source /usr/lib/mios/paths.sh

LOG_DIR="${MIOS_LOG_DIR}"
PERSISTENT_LOG="/var/log/mios/last-build.log"

echo "[copy-build-log] Starting log preservation"

if [[ -d "$LOG_DIR" ]]; then
    mkdir -p "$(dirname "$PERSISTENT_LOG")" 2>/dev/null || true
    shopt -s nullglob
    LATEST_LOG=""
    for cand in "$LOG_DIR"/mios-build.log "$LOG_DIR"/mios-build-chain.log.gz; do
        if [[ -f "$cand" ]]; then LATEST_LOG="$cand"; break; fi
    done
    shopt -u nullglob
    if [[ -n "$LATEST_LOG" ]]; then
        cp -f "$LATEST_LOG" "$PERSISTENT_LOG" 2>/dev/null || true
        echo "[copy-build-log] Copied $LATEST_LOG to $PERSISTENT_LOG"
    else
        echo "[copy-build-log] No build log found in $LOG_DIR"
    fi
else
    echo "[copy-build-log] Log directory $LOG_DIR not found"
fi
exit 0

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
    mkdir -p "$(dirname "$PERSISTENT_LOG")" 2>/dev/null || true
    # Find the latest build log in the immutable store. Use a glob
    # expansion + nullglob so a no-match returns zero entries instead
    # of failing the pipeline under 'set -euo pipefail' -- the previous
    # 'ls ... | head' form aborted the entire service whenever the log
    # was absent (the common case on a fresh deploy, which is when
    # this oneshot fires).
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
        echo "[copy-build-log] No build log found in $LOG_DIR (nothing to copy; expected on a fresh deploy)"
    fi
else
    echo "[copy-build-log] Log directory $LOG_DIR not found (nothing to copy)"
fi
exit 0

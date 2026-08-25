#!/usr/bin/env bash
set -e

MIOSD_BIN=""
if command -v miosd >/dev/null 2>&1; then
    MIOSD_BIN="miosd"
elif [[ -x "/usr/libexec/mios/miosd" ]]; then
    MIOSD_BIN="/usr/libexec/mios/miosd"
elif [[ -x "/usr/bin/miosd" ]]; then
    MIOSD_BIN="/usr/bin/miosd"
fi

if [[ -n "$MIOSD_BIN" ]]; then
    exec "$MIOSD_BIN" greenboot
else
    echo "[greenboot] ERROR: Required core daemon (miosd) missing on system" >&2
    exit 1
fi

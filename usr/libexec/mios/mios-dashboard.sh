#!/usr/bin/env bash
# AI-hint: MiOS live system dashboard thin-wrapper
# AI-related: /usr/libexec/mios/mios-dashboard.py, /usr/libexec/mios/mios-dashboard, /usr/share/mios/mios.toml, /etc/mios/install.env
# /usr/libexec/mios/mios-dashboard.sh

BIN_PATH="/usr/libexec/mios/mios-dashboard"
PY_PATH="/usr/libexec/mios/mios-dashboard.py"

if [[ -x "$BIN_PATH" ]]; then
    exec "$BIN_PATH" "$@"
elif [[ -f "$PY_PATH" ]]; then
    exec python3 "$PY_PATH" "$@"
fi

# Fallback in local source checkout context
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
if [[ -x "${SCRIPT_DIR}/mios-dashboard" ]]; then
    exec "${SCRIPT_DIR}/mios-dashboard" "$@"
elif [[ -f "${SCRIPT_DIR}/mios-dashboard.py" ]]; then
    exec python3 "${SCRIPT_DIR}/mios-dashboard.py" "$@"
fi

echo "MiOS Dashboard: rendering engine not found at ${BIN_PATH} or ${PY_PATH}" >&2
exit 1

#!/usr/bin/env bash
# AI-hint: Greenboot wanted check to monitor Hyprland/Quickshell Wayland compositor state and input actuation, logging warnings to pgvector without triggering system rollback.
# AI-related: greenboot, quickshell, ydotool, grim

set -uo pipefail

# Source global environment variables (SSOT)
if [ -f /etc/profile.d/mios-env.sh ]; then
    source /etc/profile.d/mios-env.sh
fi

exit_code=0
failure_details=""

log_health_failure() {
    local check_name="$1"
    local message="$2"
    failure_details="${failure_details}${check_name}: ${message}; "
    echo "[greenboot-desktop] [FAIL] ${check_name}: ${message}" >&2
}

# Check 1: uinput device is available
if [ ! -c /dev/uinput ]; then
    log_health_failure "uinput_device" "/dev/uinput character device not found"
    exit_code=1
fi

# Check 2: grim capture command is available
if ! command -v grim >/dev/null 2>&1; then
    log_health_failure "grim_cli" "grim screen capture command not found"
    exit_code=1
fi

# Check 3: quickshell binary is available
if ! command -v quickshell >/dev/null 2>&1; then
    log_health_failure "quickshell_cli" "quickshell binary not found"
    exit_code=1
fi

# Log event to pgvector on warning/failure
if [ "$exit_code" -ne 0 ]; then
    if command -v mios-pg-query >/dev/null 2>&1; then
        _summary="Desktop graphical health check failed: $failure_details"
        _payload="{\"detail\": \"$failure_details\", \"status\": \"failed\"}"
        mios-pg-query "INSERT INTO event(kind, source, severity, summary, payload) VALUES (\$1, \$2, \$3, \$4, \$5::jsonb)" \
            "desktop_health" "wayland" "warn" "$_summary" "$_payload" >/dev/null 2>&1 || true
    fi
fi

exit "$exit_code"

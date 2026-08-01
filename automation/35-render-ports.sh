#!/usr/bin/env bash
# MIOS_APPLY_CLASS=universal
# AI-hint: Extracts port definitions from mios.toml [ports] section and appends them to install.env as MIOS_PORT_* variables for container environment injection.
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

TOML_FILE="/usr/share/mios/mios.toml"
ENV_FILE="/etc/mios/install.env"

mios_log "Extract ports from $TOML_FILE to $ENV_FILE"

mkdir -p "$(dirname "$ENV_FILE")"
touch "$ENV_FILE"

if command -v miosd >/dev/null 2>&1; then
    miosd render-ports --toml "$TOML_FILE" --out "$ENV_FILE"
    mios_ok "wrote MIOS_PORT_* to $ENV_FILE via miosd"
    exit 0
fi

sed -i '/^MIOS_PORT_/d' "$ENV_FILE"

awk '
BEGIN { stack_id = 0 }
/^\[ports\]/ {flag=1; next}
/^\[/ {flag=0}
flag && /=/ {
    split($0, arr, "=")
    key = arr[1]
    val = arr[2]
    
    sub(/^[ \t]+/, "", key)
    sub(/[ \t]+$/, "", key)
    sub(/^[ \t]+/, "", val)
    sub(/[ \t]+#.*$/, "", val)
    sub(/[ \t]+$/, "", val)
    
    if (key == "stack_id") {
        stack_id = val + 0
        next
    }
    
    if (val ~ /^[0-9]+$/ && val != "53") {
        val = val + (stack_id * 10000)
    }
    
    key = toupper(key)
    
    print "MIOS_PORT_" key "=" val
}' "$TOML_FILE" >> "$ENV_FILE"

mios_ok "wrote MIOS_PORT_* to $ENV_FILE (stack_id*10000 offset, port 53 excluded)"

#!/usr/bin/env bash
# AI-hint: Extracts port definitions from mios.toml [ports] section and appends them to install.env as MIOS_PORT_* variables for container environment injection.
set -euo pipefail

TOML_FILE="/usr/share/mios/mios.toml"
ENV_FILE="/etc/mios/install.env"

echo "[16-render-ports] Extracting ports from $TOML_FILE to $ENV_FILE..."

mkdir -p "$(dirname "$ENV_FILE")"
touch "$ENV_FILE"

# Clean up old port definitions
sed -i '/^MIOS_PORT_/d' "$ENV_FILE"

awk '
BEGIN { stack_id = 0 }
/^\[ports\]/ {flag=1; next}
/^\[/ {flag=0}
flag && /=/ {
    # Extract key and value
    split($0, arr, "=")
    key = arr[1]
    val = arr[2]
    
    # Trim whitespace and comments
    sub(/^[ \t]+/, "", key)
    sub(/[ \t]+$/, "", key)
    sub(/^[ \t]+/, "", val)
    sub(/[ \t]+#.*$/, "", val)
    sub(/[ \t]+$/, "", val)
    
    # Capture stack_id
    if (key == "stack_id") {
        stack_id = val + 0
        next
    }
    
    # Apply 8-Block mathematical offset, excluding port 53 (DNS)
    if (val ~ /^[0-9]+$/ && val != "53") {
        val = val + (stack_id * 10000)
    }
    
    # Uppercase the key
    key = toupper(key)
    
    print "MIOS_PORT_" key "=" val
}' "$TOML_FILE" >> "$ENV_FILE"

echo "[16-render-ports] Wrote MIOS_PORT_* to $ENV_FILE (stack_id*10000 offset applied, port 53 excluded)."

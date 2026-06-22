#!/usr/bin/env bash
# AI-hint: Extracts port definitions from mios.toml [ports] section and appends them to install.env as MIOS_PORT_* variables for container environment injection.
set -euo pipefail

TOML_FILE="/usr/share/mios/mios.toml"
ENV_FILE="/etc/mios/install.env"

echo "[16-render-ports] Extracting ports from $TOML_FILE to $ENV_FILE..."

mkdir -p "$(dirname "$ENV_FILE")"
touch "$ENV_FILE"

awk '
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
    
    # Uppercase the key
    key = toupper(key)
    
    print "MIOS_PORT_" key "=" val
}' "$TOML_FILE" >> "$ENV_FILE"

echo "[16-render-ports] Done."

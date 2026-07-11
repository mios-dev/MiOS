#!/bin/bash
# AI-hint: Gated build context materializer. Runs materialize-build-ctx.py if build_catalog_authoritative is true.
# AI-related: usr/libexec/mios/materialize-build-ctx.py, /ctx

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/lib/common.sh"
source "${SCRIPT_DIR}/lib/packages.sh"

TOML_PATH="$(_resolve_mios_toml)"
if [[ -z "$TOML_PATH" ]]; then
    exit 0
fi

# Check if build_catalog_authoritative is true
AUTH=$(awk '/^[[:space:]]*build_catalog_authoritative[[:space:]]*=/ {
    if ($0 ~ /=[[:space:]]*true/) print "true"
}' "$TOML_PATH" 2>/dev/null)

if [[ "$AUTH" == "true" ]]; then
    echo "[00-materialize-build-ctx] build_catalog_authoritative=true. Running database materialization..."
    # The default location of materialized files is next to mios.toml
    export MIOS_BUILD_CTX="${MIOS_BUILD_CTX:-$(dirname "$TOML_PATH")}"
    if /usr/libexec/mios/materialize-build-ctx.py; then
        echo "[00-materialize-build-ctx] Materialization successful to ${MIOS_BUILD_CTX}."
    else
        echo "[00-materialize-build-ctx] WARNING: Materialization failed (likely DB unreachable inside clean container). Falling back to TOML."
    fi
fi

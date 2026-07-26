#!/bin/bash
# MIOS_APPLY_CLASS=bake-only
# AI-hint: Gated build context materializer. Runs materialize-build-ctx.py if build_catalog_authoritative is true.
# AI-related: /usr/libexec/mios/materialize-build-ctx.py
set -euo pipefail
for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

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
    mios_log "build_catalog_authoritative=true; materialize build-ctx into ${MIOS_BUILD_CTX}"
    # The default location of materialized files is next to mios.toml
    export MIOS_BUILD_CTX="${MIOS_BUILD_CTX:-$(dirname "$TOML_PATH")}"
    if /usr/libexec/mios/materialize-build-ctx.py; then
        mios_ok "materialized to ${MIOS_BUILD_CTX}"
    else
        mios_warn "materialization failed (DB unreachable in clean container); falling back to TOML"
    fi
fi

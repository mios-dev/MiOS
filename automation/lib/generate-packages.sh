#!/usr/bin/env bash
# AI-hint: bash WS-A17 build-time materializer for the local package registry.
# AI-doc: usr/share/doc/mios/manual/lib.md
set -euo pipefail

_enabled_val=""
if [[ -n "${MIOS_PACKAGE_REGISTRY:-}" ]]; then
    _enabled_val="$MIOS_PACKAGE_REGISTRY"
else
    _toml="${MIOS_TOML:-/usr/share/mios/mios.toml}"
    if [[ -f "$_toml" ]]; then
        _enabled_val=$(python3 -c '
import sys, os
try:
    import tomllib as t
except ImportError:
    import tomli as t
with open(sys.argv[1], "rb") as f:
    d = t.load(f)
val = (d.get("ai") or {}).get("package_registry", False)
print("true" if val else "false")
' "$_toml" 2>/dev/null || echo "false")
    fi
fi

_enabled="$(printf '%s' "${_enabled_val:-false}" | tr '[:upper:]' '[:lower:]')"
case "$_enabled" in
    1|true|yes|on)
        : ;;
    *)
        echo "[generate-packages] [ai].package_registry off"
        exit 0
        ;;
esac

_gen="${MIOS_REGISTRY_BIN:-/usr/libexec/mios/mios-registry}"
if [[ ! -x "$_gen" && ! -f "$_gen" ]]; then
    _root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    _gen="$_root/usr/libexec/mios/mios-registry"
    export MIOS_AGENT_PIPE_DIR="${MIOS_AGENT_PIPE_DIR:-$_root/usr/lib/mios/agent-pipe}"
    export MIOS_TOML="${MIOS_TOML:-$_root/usr/share/mios/mios.toml}"
    export MIOS_PACKAGES_DIR="${MIOS_PACKAGES_DIR:-$_root/usr/share/mios/ai/v1/packages}"
fi

echo "[generate-packages] package_registry ON"
python3 "$_gen" generate

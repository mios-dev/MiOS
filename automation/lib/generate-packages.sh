#!/usr/bin/env bash
# AI-hint: bash WS-A17 build-time materializer for the local package registry.
# AI-doc: usr/share/doc/mios/manual/_harvest/automation_lib_generate_packages_sh.md
set -euo pipefail

_enabled="$(printf '%s' "${MIOS_PACKAGE_REGISTRY:-false}" | tr '[:upper:]' '[:lower:]')"
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

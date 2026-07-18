#!/usr/bin/env bash
# AI-hint: WS-A17 build-time materializer for the local package registry. Thin, flag-gated wrapper around `mios-registry generate`: when [ai].package_registry (MIOS_PACKAGE_REGISTRY) is true it projects the live SSOT catalogs into ai/v1/packages/<author>/<name>/<version>/mios-pkg.toml + registry.json; when false (the default) it is a no-op so the feature ships dormant. Sourced/called by the build (or run manually); never fails the build when the flag is off.
# AI-related: /usr/libexec/mios/mios-registry, /usr/lib/mios/agent-pipe/mios_registry.py, /usr/share/mios/mios.toml, ./build.sh
# AI-functions: (sourced helper -- no functions; guards on MIOS_PACKAGE_REGISTRY)
# ----------------------------------------------------------------------------
# WS-A17: materialize the versioned package tree from the live SSOT IF the
# operator enabled [ai].package_registry. Inert (exit 0, nothing written) when
# the flag is off -- so wiring this into build.sh is safe regardless of the flag.
set -euo pipefail

_enabled="$(printf '%s' "${MIOS_PACKAGE_REGISTRY:-false}" | tr '[:upper:]' '[:lower:]')"
case "$_enabled" in
    1|true|yes|on)
        : ;;
    *)
        echo "[generate-packages] [ai].package_registry off -- skipping (dormant)."
        exit 0
        ;;
esac

_gen="${MIOS_REGISTRY_BIN:-/usr/libexec/mios/mios-registry}"
# Source-tree build: fall back to the repo-relative CLI when the deployed path
# is absent (repo root == system root; SCRIPT_DIR is automation/lib).
if [[ ! -x "$_gen" && ! -f "$_gen" ]]; then
    _root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    _gen="$_root/usr/libexec/mios/mios-registry"
    export MIOS_AGENT_PIPE_DIR="${MIOS_AGENT_PIPE_DIR:-$_root/usr/lib/mios/agent-pipe}"
    export MIOS_TOML="${MIOS_TOML:-$_root/usr/share/mios/mios.toml}"
    export MIOS_PACKAGES_DIR="${MIOS_PACKAGES_DIR:-$_root/usr/share/mios/ai/v1/packages}"
fi

echo "[generate-packages] package_registry ON -- running mios-registry generate to write ai/v1/packages/<author>/<name>/<version>/mios-pkg.toml + registry.json..."
python3 "$_gen" generate

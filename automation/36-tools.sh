#!/bin/bash
# 'MiOS' v0.2.0 -- 36-tools: CLI tools and consolidated mios command
# Installs all mios-* tools to /usr/bin/ and the master 'mios' CLI.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[36-tools] Configuring 'MiOS' CLI tools..."

# CLI tools are now delivered via system_files overlay at /usr/bin/
# We just need to ensure permissions are correct here for files that 
# might have lost the executable bit during git/Windows transfer.

TOOLS=(
    mios
    mios-env
    mios-sync-env
    mios-update
    mios-rebuild
    mios-build
    mios-backup
    mios-deploy
    mios-status
    mios-vfio-toggle
    mios-vfio-check
    mios-ollama
    iommu-groups
)
# Note: aichat / aichat-ng are installed by 37-aichat.sh (which fetches
# the upstream binaries); attempting to chmod them here printed a WARN
# every build because the binaries do not exist yet at this stage.

for tool in "${TOOLS[@]}"; do
    if [ -f "/usr/bin/$tool" ]; then
        chmod +x "/usr/bin/$tool"
    else
        echo "[36-tools] WARN: /usr/bin/$tool not found (should be in system_files overlay)"
    fi
done

# ═══ Install external scripts from build context ═══
# These are scripts that live in automation/ and are installed to /usr/bin/
echo "[36-tools] Installing mios-toggle-headless and mios-test..."
for ext_tool in mios-toggle-headless mios-test; do
    if [ -f "${SCRIPT_DIR}/${ext_tool}" ]; then
        install -Dm0755 "${SCRIPT_DIR}/${ext_tool}" "/usr/bin/${ext_tool}"
    else
        echo "[36-tools] WARN: ${ext_tool} not found at ${SCRIPT_DIR}/${ext_tool}"
    fi
done

# ═══ Install the userenv.sh resolver library ═══
# /usr/bin/mios-env (Architectural Law 5 -- UNIFIED-AI-REDIRECTS)
# resolves the layered MIOS_* environment by sourcing
# /usr/lib/mios/userenv.sh. The library lives at tools/lib/userenv.sh
# in the build context and previously had no installation step --
# mios-env therefore fell back to its env-defaults-only path and
# ignored the TOML overlay. Stage it now so the CLI sees the full
# three-layer mios.toml resolver.
USERENV_SRC=""
for cand in \
    "${SCRIPT_DIR}/../tools/lib/userenv.sh" \
    "/tmp/build/tools/lib/userenv.sh" \
    "/ctx/tools/lib/userenv.sh"
do
    if [[ -f "$cand" ]]; then USERENV_SRC="$cand"; break; fi
done
if [[ -n "$USERENV_SRC" ]]; then
    install -D -m 0644 "$USERENV_SRC" /usr/lib/mios/userenv.sh
    echo "[36-tools] Installed userenv.sh resolver to /usr/lib/mios/userenv.sh"
else
    echo "[36-tools] WARN: tools/lib/userenv.sh not found in build context; mios-env will fall back to env.defaults-only resolution"
fi

echo "[36-tools] CLI tools configuration complete. Run 'mios --help' for commands."

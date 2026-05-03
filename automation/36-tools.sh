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
    mios-update
    mios-rebuild
    mios-build
    mios-backup
    mios-deploy
    mios-status
    mios-vfio-toggle
    mios-vfio-check
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

echo "[36-tools] CLI tools configuration complete. Run 'mios --help' for commands."

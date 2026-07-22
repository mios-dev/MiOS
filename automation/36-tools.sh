#!/bin/bash
# AI-hint: Sets executable permissions for the core mios- suite of CLI tools in /usr/bin/ and installs auxiliary scripts like mios-toggle-headless and mios-test to establish the primary MiOS command interface.
# AI-related: /usr/libexec/mios/mios-dashboard.sh, /usr/lib/mios/userenv.sh., /usr/lib/mios/userenv.sh, mios-toggle-headless, mios-test, mios-dashboard, mios-dash, mios-env, mios-sync-env, mios-update
# 'MiOS' - 36-tools: CLI tools and consolidated mios command
# Installs all mios-* tools to /usr/bin/ and the master 'mios' CLI.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[36-tools] Configuring 'MiOS' CLI tools..."

# CLI tools are now delivered via system_files overlay at /usr/bin/
# We just need to ensure permissions are correct here for files that 
# might have lost the executable bit during git/Windows transfer.

TOOLS=(
    mios
    mios-backup
    mios-build
    mios-chrome
    mios-deploy
    mios-pull
    mios-rebuild
    mios-update
    hermes
)

for tool in "${TOOLS[@]}"; do
    if [ -f "/usr/bin/$tool" ]; then
        chmod +x "/usr/bin/$tool"
    fi
done

# Create symlink aliases for canonical subcommands if not already present
[[ -f "/usr/bin/mios-dash" ]] || ln -sf /usr/libexec/mios/mios-dashboard.sh /usr/bin/mios-dash 2>/dev/null || true

# ═══ Install external scripts from build context ═══
# These are scripts that live in automation/ and are installed to /usr/bin/
echo "[36-tools] Installing mios-toggle-headless..."
if [ -f "${SCRIPT_DIR}/mios-toggle-headless" ]; then
    install -Dm0755 "${SCRIPT_DIR}/mios-toggle-headless" "/usr/bin/mios-toggle-headless"
fi

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
    echo "[36-tools] WARN: tools/lib/userenv.sh not found in build context; mios-env will fall back to legacy env-style files only"
fi

echo "[36-tools] CLI tools configuration complete. Run 'mios --help' for commands."

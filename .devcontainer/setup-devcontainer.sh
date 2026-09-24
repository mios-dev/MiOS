#!/usr/bin/env bash
# GENERATED FROM THREE-REPO DEVCONTAINER SPECIFICATION - DO NOT EDIT
# AI-hint: Cohesive multi-repository sync and environment provisioning across MiOS, mios-bootstrap, and -dev-loop.
set -euo pipefail

WORKSPACE_DIR="/workspaces"
mkdir -p "$WORKSPACE_DIR"

echo "=== [1/5] Syncing Three-Repo Workspace Layout ==="
# Ensure all three repositories are cloned side-by-side
declare -A REPOS=(
    ["MiOS"]="https://github.com/mios-dev/MiOS.git"
    ["mios-bootstrap"]="https://github.com/mios-dev/mios-bootstrap.git"
    ["-dev-loop"]="https://github.com/mios-dev/-dev-loop.git"
)

for repo in "${!REPOS[@]}"; do
    target="${WORKSPACE_DIR}/${repo}"
    if [ ! -d "$target/.git" ]; then
        if [ "$repo" = "-dev-loop" ] && [ -d "$HOME/.dev-loop/.git" ]; then
            echo "  [LINK/SYNC] Existing checkout at $HOME/.dev-loop found"
            ln -sfn "$HOME/.dev-loop" "$target"
        else
            echo "  [CLONE] $repo -> $target"
            git clone --depth 1 "${REPOS[$repo]}" "$target" 2>/dev/null || {
                echo "  [WARN] Failed to clone ${REPOS[$repo]} (token authorization required)"
            }
        fi
    else
        echo "  [EXISTS] $target"
    fi
done

# Create non-colliding symlinks for dev-loop access
if [ -d "${WORKSPACE_DIR}/-dev-loop" ] || [ -L "${WORKSPACE_DIR}/-dev-loop" ]; then
    ln -sfn "${WORKSPACE_DIR}/-dev-loop" "${WORKSPACE_DIR}/dev-loop"
    if [ ! -d "$HOME/.dev-loop" ] || [ -L "$HOME/.dev-loop" ]; then
        ln -sfn "${WORKSPACE_DIR}/-dev-loop" "$HOME/.dev-loop"
    fi
fi

# Enable nested git repository access and recursive submodule hydration
git config --global --add safe.directory "*"
for repo_dir in "${WORKSPACE_DIR}"/*; do
    if [ -d "$repo_dir/.git" ] || [ -f "$repo_dir/.git" ]; then
        (cd "$repo_dir" && git submodule update --init --recursive 2>/dev/null || true)
    fi
done

echo "=== [2/5] Initializing Root Overlay (MiOS System Repo) ==="
if [ -x "${WORKSPACE_DIR}/MiOS/.devcontainer/install-root-overlay.sh" ]; then
    sudo bash "${WORKSPACE_DIR}/MiOS/.devcontainer/install-root-overlay.sh" || echo "  [WARN] Overlay init completed with warnings"
elif [ -x "/usr/local/bin/mios-root-overlay" ]; then
    sudo bash "/usr/local/bin/mios-root-overlay" || echo "  [WARN] Overlay init completed with warnings"
fi

echo "=== [3/5] Configuring Antigravity Keyring & Shims ==="
if ! command -v agy >/dev/null 2>&1; then
    DEVLOOP_ENV="${WORKSPACE_DIR}/-dev-loop/skills/dev-loop/scripts/env"
    if [ -r "${DEVLOOP_ENV}/setup-antigravity.sh" ]; then
        bash "${DEVLOOP_ENV}/setup-antigravity.sh" --quiet || echo "  [WARN] Dev-loop setup-antigravity encountered warnings"
    fi

    if ! command -v agy >/dev/null 2>&1; then
        echo "  [INSTALL] AGY CLI"
        curl -fsSL --retry 4 --retry-delay 2 https://antigravity.google/cli/install.sh | bash || echo "  [WARN] AGY install failed; install manually when network is available"
    fi
fi

echo "=== [4/5] Installing Multi-Harness Shims & Skills ==="
if [ -x "${WORKSPACE_DIR}/-dev-loop/skills/dev-loop/scripts/install.sh" ]; then
    sh "${WORKSPACE_DIR}/-dev-loop/skills/dev-loop/scripts/install.sh" --all --user >/dev/null 2>&1 || true
fi

echo "=== [5/6] Checking Toolchain Readiness ==="
echo "  Rust:    $(rustc --version 2>/dev/null || echo 'missing')"
echo "  Cargo:   $(cargo --version 2>/dev/null || echo 'missing')"
echo "  Python:  $(python3 --version 2>/dev/null || echo 'missing') (compat: $(python3.11 --version 2>/dev/null || echo 'missing'))"
echo "  Podman:  $(podman --version 2>/dev/null || echo 'missing')"
echo "  Docker:  $(docker --version 2>/dev/null || echo 'missing (podman-docker shim)')"
echo "  Claude:  $(claude --version 2>/dev/null || echo 'missing')"
echo "  Agy:     $(agy --version 2>/dev/null || echo 'missing')"
echo "  Gemini:  $(gemini -v 2>/dev/null || gemini --version 2>/dev/null || echo 'missing')"

echo "=== [6/6] Ensuring Frameless Edge-to-Edge VSCode Environment & Dotfiles ==="
VSCODE_CSS_TOOL="${WORKSPACE_DIR}/MiOS/usr/libexec/mios/mios-vscode-custom-css"
if [ ! -f "$VSCODE_CSS_TOOL" ]; then
    VSCODE_CSS_TOOL="/usr/libexec/mios/mios-vscode-custom-css"
fi
if [ -f "$VSCODE_CSS_TOOL" ]; then
    python3 "$VSCODE_CSS_TOOL" install --all || true
fi

# Ensure SSOT .dotfiles/vscode/settings.json is projected to all IDE targets
DOTFILES_DIR="${WORKSPACE_DIR}/MiOS/.dotfiles"
if [ -d "$DOTFILES_DIR/vscode" ]; then
    for target_dir in \
        "${WORKSPACE_DIR}/MiOS/.vscode" \
        "$HOME/.vscode-server/data/Machine" \
        "$HOME/.vscode-server-insiders/data/Machine" \
        "$HOME/.vscode-remote/data/Machine" \
        "$HOME/.vscode-remote-insiders/data/Machine" \
        "$HOME/.config/Code/User" \
        "$HOME/.config/Code - Insiders/User" \
        "$HOME/.local/share/code-server/User"; do
        mkdir -p "$target_dir"
        cp -f "$DOTFILES_DIR/vscode/settings.json" "$target_dir/settings.json" 2>/dev/null || true
    done
fi

if [ -f "${WORKSPACE_DIR}/MiOS/usr/libexec/mios/mios-dotfiles" ]; then
    python3 "${WORKSPACE_DIR}/MiOS/usr/libexec/mios/mios-dotfiles" apply || true
elif [ -f "/usr/libexec/mios/mios-dotfiles" ]; then
    python3 "/usr/libexec/mios/mios-dotfiles" apply || true
fi

echo "Multi-repo devcontainer setup complete."


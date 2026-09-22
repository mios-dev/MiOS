#!/usr/bin/env bash
# Reconcile the development-safe MiOS system surface on each container start.
set -euo pipefail

readonly ROOT=/workspaces/MiOS

if [[ ! -d "${ROOT}/.git" ]]; then
    echo "[devcontainer:boot] MiOS workspace is unavailable: ${ROOT}" >&2
    exit 1
fi
if ! command -v sudo >/dev/null 2>&1; then
    echo "[devcontainer:boot] sudo is required to apply the MiOS root overlay" >&2
    exit 1
fi

echo "[devcontainer:boot] Applying MiOS system overlay..."
sudo bash "${ROOT}/.devcontainer/install-root-overlay.sh"

echo "[devcontainer:boot] Reconciling MiOS development core..."
bash "${ROOT}/.devcontainer/setup-core-components.sh"
bash "${ROOT}/.devcontainer/platform-bootstrap.sh"

for required in podman bootc miosd; do
    if ! command -v "${required}" >/dev/null 2>&1; then
        echo "[devcontainer:boot] Missing required MiOS component: ${required}" >&2
        exit 1
    fi
done

echo "[devcontainer:boot] MiOS systems are installed and ready."

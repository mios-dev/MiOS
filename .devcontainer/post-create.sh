#!/bin/bash
set -euo pipefail
echo "[devcontainer:post-create] Initializing embedded agent harness..."
mkdir -p .devloop_artifacts .worktrees
git config --global --add safe.directory /workspaces/MiOS
bash /workspaces/MiOS/.devcontainer/setup-devcontainer.sh
bash /workspaces/MiOS/.devcontainer/setup-core-components.sh
echo "[devcontainer:post-create] Full MiOS workspace and harness are ready."

#!/bin/bash
set -euo pipefail
echo "[devcontainer:post-create] Initializing embedded agent harness..."
mkdir -p .devloop_artifacts .worktrees
git config --global --add safe.directory /workspace
echo "[devcontainer:post-create] Harness directory structures verified."

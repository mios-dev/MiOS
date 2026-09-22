#!/bin/bash
set -euo pipefail
echo "[devcontainer:post-start] Checking agentic environment and AI endpoint..."
python3 harness/verification_gates.py --quick || true
bash .devcontainer/configure-agy-runtime.sh
echo "[devcontainer:post-start] Ready for agent dispatch."

#!/bin/bash
set -euo pipefail
echo "[devcontainer:post-start] Checking agentic environment and AI endpoint..."

# The verification gate must fail closed: a non-zero exit here fails
# postStartCommand and surfaces in the devcontainer UI/CLI. Do not mask this
# with `|| true` -- that turned every failing invariant into a silent pass.
python3 harness/verification_gates.py --quick

echo "[devcontainer:post-start] Ready for agent dispatch."

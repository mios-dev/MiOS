#!/bin/bash
set -euo pipefail
echo "[devcontainer:post-start] Checking agentic environment and AI endpoint..."

# The verification gate must fail closed: a non-zero exit here fails
# postStartCommand and surfaces in the devcontainer UI/CLI. Do not mask this
# with `|| true` -- that turned every failing invariant into a silent pass.
python3 harness/verification_gates.py --quick

# The AGY runtime helper is a best-effort, optional adapter: its absence of a
# configured API key is expected and must not fail container start. Any
# unexpected script failure (bad JSON, permission error) still surfaces.
bash .devcontainer/configure-agy-runtime.sh

echo "[devcontainer:post-start] Ready for agent dispatch."

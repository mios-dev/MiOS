#!/usr/bin/env bash
# AI-hint: Shared clean-environment test harness for executing agent-pipe unit tests.
# Strips inherited MIOS_* env variables and clears mios_toml cache to prevent env leakage.
# ============================================================================
# tools/run-agent-pipe-tests.sh
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
AGENT_PIPE_DIR="${ROOT_DIR}/usr/lib/mios/agent-pipe"

echo "[run-agent-pipe-tests] Running agent-pipe test suite in clean environment..."

if [[ ! -d "$AGENT_PIPE_DIR" ]]; then
    echo "ERROR: agent-pipe directory not found at $AGENT_PIPE_DIR" >&2
    exit 1
fi

cd "$AGENT_PIPE_DIR"

_test_py="python3"
if [[ -x "/usr/share/mios/agents/.venv/bin/python3" ]]; then
    _test_py="/usr/share/mios/agents/.venv/bin/python3"
fi

fails=0
shopt -s nullglob
for t in test_mios_*.py; do
    if ! { unset $(compgen -v MIOS_ 2>/dev/null) || true; PYTHONIOENCODING=utf-8 "$_test_py" "$t" >/dev/null 2>&1; }; then
        echo "  [FAIL] $t" >&2
        fails=$((fails + 1))
    fi
done

if [[ "$fails" -gt 0 ]]; then
    echo "[run-agent-pipe-tests] FAIL: $fails test script(s) failed." >&2
    exit 1
fi

echo "[run-agent-pipe-tests] PASS: All agent-pipe unit tests passed."

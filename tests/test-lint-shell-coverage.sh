#!/usr/bin/env bash
# AI-hint: Test ensuring lint-shell.sh retains full shell directory coverage.
# AI-related: automation/lint-shell.sh, tests/test-lint-shell-coverage.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
LINT_SCRIPT="${ROOT}/automation/lint-shell.sh"

if [ ! -f "$LINT_SCRIPT" ]; then
    echo "ERROR: automation/lint-shell.sh not found at ${LINT_SCRIPT}" >&2
    exit 1
fi

REQUIRED_DIRS=(
    "automation"
    "tools"
    "installation"
    "tests"
    "usr/lib/mios"
    "usr/libexec/mios"
)

missing=()
for dir in "${REQUIRED_DIRS[@]}"; do
    if ! grep -q "$dir" "$LINT_SCRIPT"; then
        missing+=("$dir")
    fi
done

if [ ${#missing[@]} -ne 0 ]; then
    echo "ERROR: lint-shell.sh is missing shell coverage globs for directories: ${missing[*]}" >&2
    exit 1
fi

echo "[test-lint-shell-coverage] Shell directory coverage check passed clean."
exit 0

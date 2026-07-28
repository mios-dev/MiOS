#!/usr/bin/env bash
# AI-hint: Verifies that automation/lint-shell.sh contains collection globs for all repository shell directories.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
LINT_SCRIPT="${ROOT_DIR}/automation/lint-shell.sh"

if [ ! -f "${LINT_SCRIPT}" ]; then
    echo "ERROR: lint-shell.sh not found at ${LINT_SCRIPT}" >&2
    exit 1
fi

REQUIRED_DIRS=(
    "installation/"
    "tests/"
    "automation/lib"
    "tools/lib"
    "usr/lib/mios"
)

missing=0
for d in "${REQUIRED_DIRS[@]}"; do
    if ! grep -q "${d}" "${LINT_SCRIPT}"; then
        echo "FAIL: Required shell directory '${d}' is missing from lint-shell.sh collection globs." >&2
        missing=$((missing + 1))
    fi
done

if [ "${missing}" -gt 0 ]; then
    echo "::error::${missing} required shell directory/directories missing from lint-shell.sh" >&2
    exit 1
fi

echo "[test-lint-shell-coverage] PASS: All required shell directories present in lint-shell.sh globs."
exit 0

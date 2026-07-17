#!/usr/bin/env bash
# AI-hint: Runner for shellcheck across automation, tools, and libexec shell scripts. Degrades open if shellcheck is absent.
set -euo pipefail

# SCRIPT_DIR is the location of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if ! command -v shellcheck >/dev/null 2>&1; then
    # exit 2 == "skipped, NOT linted" so the drift-gate WARNs rather than printing a
    # false-green conformance summary over nothing linted (audit 2026-07-17).
    echo "[lint-shell] WARNING: shellcheck is missing -- shell linting SKIPPED (not a pass)" >&2
    exit 2
fi

# Find all shell files
files=()

# 1. automation/*.sh
for f in "${ROOT}"/automation/*.sh; do
    [ -f "$f" ] && files+=("$f")
done

# 2. tools/*.sh
for f in "${ROOT}"/tools/*.sh; do
    [ -f "$f" ] && files+=("$f")
done

# 3. usr/libexec/mios/mios-* (filter by shebang)
for f in "${ROOT}"/usr/libexec/mios/mios-*; do
    if [ -f "$f" ]; then
        # read the first line
        read -r first_line < "$f" || true
        if [[ "$first_line" =~ ^#\!.*(bash|sh) ]]; then
            files+=("$f")
        fi
    fi
done

if [ ${#files[@]} -eq 0 ]; then
    echo "[lint-shell] No shell scripts found to lint."
    exit 0
fi

echo "[lint-shell] Linting ${#files[@]} shell scripts..."
if ! shellcheck --severity=error "${files[@]}"; then
    echo "[lint-shell] FAIL: shellcheck found error-level issues." >&2
    exit 1
fi

echo "[lint-shell] PASS: all shell scripts are clean."
exit 0

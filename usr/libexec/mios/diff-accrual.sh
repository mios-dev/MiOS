#!/usr/bin/env bash
# AI-hint: System shutdown and boot hook wrapper for diff accrual engine.
# AI-related: usr/libexec/mios/diff-accrual.py, usr/share/doc/mios/adr/0018-shutdown-diff-snapshotting-and-boot-cycle-accrual.md

set -euo pipefail

ROOT="${MIOS_ROOT:-/}"
DIFF_PY="${DIFF_PY:-/usr/libexec/mios/diff-accrual.py}"

if [[ ! -f "$DIFF_PY" ]]; then
    DIFF_PY="$(dirname "$0")/diff-accrual.py"
fi

exec python3 "$DIFF_PY" "$@"

#!/usr/bin/bash
# AI-hint: Verifies database integrity across SQLite and PostgreSQL stores during greenboot startup.
# AI-related: usr/libexec/mios/db/mios-db-doctor.py, tests/test-db-doctor.py
set -euo pipefail

SCRIPT="/usr/libexec/mios/db/mios-db-doctor.py"

if [[ ! -e /run/ostree-booted ]] && [[ "${GREENBOOT_FORCE:-0}" != "1" ]]; then
    echo "[greenboot] INFO: not booted under ostree/bootc -- skipping ostree database integrity check"
    exit 0
fi

if [[ ! -f "$SCRIPT" ]]; then
    echo "[greenboot] WARNING: $SCRIPT not found, skipping database check"
    exit 0
fi

echo "[greenboot] INFO: Running MiOS database integrity check..."
if python3 "$SCRIPT" --check --db-type all; then
    echo "[greenboot] OK: All database stores verified healthy"
    exit 0
fi

echo "[greenboot] WARNING: Database corruption detected; attempting automated non-destructive repair..."
if python3 "$SCRIPT" --repair --db-type all; then
    echo "[greenboot] OK: Database stores repaired successfully"
    exit 0
fi

echo "[greenboot] ERROR: Unrecoverable database corruption detected during boot health check" >&2
exit 1

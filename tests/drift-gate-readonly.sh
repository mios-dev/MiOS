#!/usr/bin/env bash
set -euo pipefail

_self="${BASH_SOURCE[0]}"
_self_dir="$(cd "$(dirname "$_self")" && pwd)"
ROOT="$(cd "$_self_dir/.." && pwd)"

log() { printf '[drift-gate-readonly] %s\n' "$*"; }
die() { printf '[drift-gate-readonly] ERROR: %s\n' "$*" >&2; exit 1; }

if ! command -v git >/dev/null 2>&1; then
    log "Git is missing "
    exit 0
fi

log "Capturing initial working tree status"
status_before="$(git -C "$ROOT" status --porcelain 2>/dev/null || true)"

log "Running automation/98-drift-checks.sh"
MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/98-drift-checks.sh" >/dev/null 2>&1 || true

log "Running automation/97-ssot-lint.sh"
MIOS_DRIFT_ROOT="$ROOT" bash "${ROOT}/automation/97-ssot-lint.sh" >/dev/null 2>&1 || true

status_after="$(git -C "$ROOT" status --porcelain 2>/dev/null || true)"

if [[ "$status_before" != "$status_after" ]]; then
    log "Working tree was modified by drift checks / SSOT lint"
    git -C "$ROOT" status --porcelain
    die "98-drift-checks.sh or 97-ssot-lint.sh mutated the working tree"
fi

log "Read-only self-test passed clean "

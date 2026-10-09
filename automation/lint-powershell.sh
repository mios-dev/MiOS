#!/usr/bin/env bash
# AI-hint: Thin adapter for the static mios-gate PowerShell check; missing tools fail closed.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -n "${MIOS_NATIVE_BIN_DIR:-}" ]]; then
    gate="$MIOS_NATIVE_BIN_DIR/mios-gate"
    case "$(uname -s)" in MINGW*|MSYS*|CYGWIN*) gate+='.exe';; esac
else
    gate="$(command -v mios-gate || true)"
fi
[[ -n "$gate" && -x "$gate" ]] || { echo '[lint-powershell] required native mios-gate is unavailable' >&2; exit 2; }
exec "$gate" powershell-parse --root "$ROOT"

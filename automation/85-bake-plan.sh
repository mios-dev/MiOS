#!/usr/bin/env bash
# MIOS_APPLY_CLASS=bake-only
# automation/85-bake-plan.sh -- project the SSOT bake-groups list files from mios.toml.
# AI-hint: Projects the sharded bake-plan files (.list) under /usr/lib/mios/bake/plan.d/
# (WS-BAKEGATE). Runs after 34-render-quadlets.sh so Image= values are concrete.
# AI-related: usr/share/mios/mios.toml, tools/generate-bake-plan.py, usr/libexec/mios/mios-bake-group, automation/98-drift-checks.sh
set -euo pipefail

_self="${BASH_SOURCE[0]}"
_self_dir="$(cd "$(dirname "$_self")" && pwd)"
ROOT="$(cd "$_self_dir/.." && pwd)"

# shellcheck source=lib/common.sh
source "$_self_dir/lib/common.sh" 2>/dev/null || {
    printf '[MiOS Bake] WARN: lib/common.sh unavailable -- skipping\n' >&2
    exit 0
}

log "16-bake-plan: projecting bake-plan lists from mios.toml SSOT"

# Run the generator (prefer native mios-bake-plan binary, fallback to Python)
if [[ -x "/usr/libexec/mios/mios-bake-plan" ]]; then
    log "16-bake-plan: using native /usr/libexec/mios/mios-bake-plan"
    if ! /usr/libexec/mios/mios-bake-plan; then
        log "ERROR: failed to generate bake plan lists with native binary"
        exit 1
    fi
elif [[ -x "${ROOT}/tools/native/target/release/mios-bake-plan" ]]; then
    log "16-bake-plan: using native tools/native target release binary"
    if ! "${ROOT}/tools/native/target/release/mios-bake-plan"; then
        log "ERROR: failed to generate bake plan lists with native binary"
        exit 1
    fi
elif ! python3 "${ROOT}/tools/generate-bake-plan.py"; then
    log "ERROR: failed to generate bake plan lists"
    exit 1
fi

log "16-bake-plan: complete"
exit 0

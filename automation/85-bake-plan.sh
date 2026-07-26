#!/usr/bin/env bash
# MIOS_APPLY_CLASS=bake-only
# automation/85-bake-plan.sh -- project the SSOT bake-groups list files from mios.toml.
# AI-hint: Projects the sharded bake-plan files (.list) under /usr/lib/mios/bake/plan.d/
# (WS-BAKEGATE). Runs after 34-render-quadlets.sh so Image= values are concrete.
# AI-related: usr/share/mios/mios.toml, tools/generate-bake-plan.py, usr/libexec/mios/mios-bake-group, automation/98-drift-checks.sh
set -euo pipefail

for _mlog in "$(dirname "${BASH_SOURCE[0]}")/../usr/lib/mios/log.sh" /usr/lib/mios/log.sh; do [ -r "$_mlog" ] && . "$_mlog" && break; done

_self="${BASH_SOURCE[0]}"
_self_dir="$(cd "$(dirname "$_self")" && pwd)"
ROOT="$(cd "$_self_dir/.." && pwd)"

# shellcheck source=lib/common.sh
source "$_self_dir/lib/common.sh" 2>/dev/null || {
    mios_warn "lib/common.sh unavailable -- skipping"
    exit 0
}

mios_log "projecting bake-plan lists from mios.toml SSOT"

# Run the generator (prefer native mios-bake-plan binary, fallback to Python)
if [[ -x "/usr/libexec/mios/mios-bake-plan" ]]; then
    mios_log "using native /usr/libexec/mios/mios-bake-plan"
    if ! /usr/libexec/mios/mios-bake-plan; then
        mios_err "failed to generate bake plan lists (native binary)"
        exit 1
    fi
elif [[ -x "${ROOT}/tools/native/target/release/mios-bake-plan" ]]; then
    mios_log "using native tools/native target release binary"
    if ! "${ROOT}/tools/native/target/release/mios-bake-plan"; then
        mios_err "failed to generate bake plan lists (native binary)"
        exit 1
    fi
elif ! python3 "${ROOT}/tools/generate-bake-plan.py"; then
    mios_err "failed to generate bake plan lists"
    exit 1
fi

mios_ok "bake-plan lists projected"
exit 0

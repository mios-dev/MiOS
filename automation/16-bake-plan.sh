#!/usr/bin/env bash
# automation/16-bake-plan.sh -- project the SSOT bake-groups list files from mios.toml.
# AI-hint: Projects the sharded bake-plan files (.list) under /usr/lib/mios/bake/plan.d/
# (WS-BAKEGATE). Runs after 15-render-quadlets.sh so Image= values are concrete.
# AI-related: usr/share/mios/mios.toml, tools/generate-bake-plan.py, usr/libexec/mios/mios-bake-group, automation/38-drift-checks.sh
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

# Run the generator
if ! python3 "${ROOT}/tools/generate-bake-plan.py"; then
    log "ERROR: failed to generate bake plan lists"
    exit 1
fi

log "16-bake-plan: complete"
exit 0

#!/usr/bin/env bash
# automation/39-opencode.sh — RETIRED (merged into 38-agents.sh).
#
# opencode install (binary fetch + opencode.json landing + mios-opencode model
# build + gateway deploy/enable) was absorbed into the UNIFIED agent-plane
# driver automation/38-agents.sh (PHASE 2). This shim remains so any build
# ordering that still invokes stage 39 is a harmless no-op.
#
# The old contradictory ACP-delegation framing (opencode spawned by Hermes per
# task) is retired: per the operator's 2026-05-31 front-door decision, opencode
# is an OpenAI /v1 council peer via mios-opencode-gateway.service (:8633), not a
# Hermes ACP subprocess.
#
# NO `set -e`. Best-effort, always exits 0.
set -uo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh" 2>/dev/null || {
    printf '[39-opencode] (retired -- handled by 38-agents.sh) no-op\n' >&2
    exit 0
}

log "[39-opencode] retired -- opencode install is owned by 38-agents.sh (no-op)"
exit 0

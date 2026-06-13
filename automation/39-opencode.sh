#!/usr/bin/env bash
# AI-hint: A legacy shim that performs a no-op for the opencode installation; agents should use 38-hermes-agent.sh for unified agent-plane setup and 37-ollama-prep.sh for model configuration.
# AI-related: mios-opencode, mios-model, mios-opencode-gateway, mios-opencode-gateway.service
# automation/39-opencode.sh — RETIRED (merged into 38-hermes-agent.sh).
#
# opencode install (binary fetch + opencode.json landing) was absorbed into
# the UNIFIED agent-plane driver automation/38-hermes-agent.sh (PHASE 2),
# which already builds the shared venv + installs Hermes in PHASE 1. The
# mios-opencode model is built by automation/37-ollama-prep.sh (it reads the
# '# mios-model:' header of every */Modelfiles/*.Modelfile, including
# mios-opencode.Modelfile). This shim remains so any build ordering that
# still invokes stage 39 is a harmless no-op.
#
# Why merged rather than a parallel 38-agents.sh: build.sh globs
# automation/[0-9][0-9]-*.sh and would run BOTH 38-* drivers; the historic
# 38- slot already owns the shared venv, so it is the single SoT.
#
# The old contradictory ACP-delegation framing (opencode spawned by Hermes per
# task) is retired: per the operator's 2026-05-31 front-door decision, opencode
# is an OpenAI /v1 council peer via mios-opencode-gateway.service (:8633), not a
# Hermes ACP subprocess.
#
# NO `set -e`. Best-effort, always exits 0.
set -euo pipefail

# shellcheck source=lib/common.sh
source "$(dirname "$0")/lib/common.sh" 2>/dev/null || {
    printf '[39-opencode] (retired -- handled by 38-hermes-agent.sh) no-op\n' >&2
    exit 0
}

log "[39-opencode] retired -- opencode install is owned by 38-hermes-agent.sh PHASE 2 (no-op)"
exit 0

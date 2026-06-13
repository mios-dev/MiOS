#!/bin/bash
# AI-hint: A diagnostic script to verify the agent-pipe's SSE stream integrity by probing the /v1/chat/completions endpoint and validating that the mios_status label and detail fields are correctly formatted in the response.
# AI-related: /etc/mios/hermes/api.env, mios-agent
# Probe the agent-pipe streaming /v1/chat/completions endpoint with
# a tiny chat prompt + inspect the SSE chunks for the mios_status
# `label` + `detail` shape. Should see emoji + label + casual
# role-based agent label (no literal "hermes" / "opencode").
set -euo pipefail

PORT="${MIOS_PORT_AGENT_PIPE:-8640}"
KEY=$(grep -oE 'MIOS_AI_KEY=[A-Za-z0-9-]+' /etc/mios/hermes/api.env \
    2>/dev/null | head -1 | cut -d= -f2)
[[ -n "$KEY" ]] || KEY="dummy"

curl -sN -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -X POST "http://127.0.0.1:${PORT}/v1/chat/completions" \
     -d '{"model":"mios-agent","stream":true,"messages":[{"role":"user","content":"hi"}]}' \
     --max-time 60 \
    | grep -E 'mios_status|data: \[DONE\]' \
    | head -10

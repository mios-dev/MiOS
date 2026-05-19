#!/bin/bash
# Probe the agent-pipe streaming /v1/chat/completions endpoint with
# a tiny chat prompt + inspect the SSE chunks for the mios_status
# `label` + `detail` shape. Should see emoji + label + casual
# role-based agent label (no literal "hermes" / "opencode").
set -u

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

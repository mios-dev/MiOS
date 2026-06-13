#!/bin/bash
# AI-hint: A diagnostic script to verify the availability and response of the local inference engine at port 11435 by probing the /v1/chat/completions endpoint and listing available models via /api/tags.
# AI-related: localhost:11435
set -euo pipefail
echo "── direct probe of refine endpoint ──"
curl -s -w 'HTTP %{http_code} in %{time_total}s\n' \
    -X POST http://localhost:11435/v1/chat/completions \
    -H 'Content-Type: application/json' \
    -d '{"model":"qwen3:1.7b","messages":[{"role":"user","content":"reply with OK"}],"max_tokens":20,"stream":false}' \
    | head -c 800
echo
echo
echo "── /api/show probe ──"
curl -s http://localhost:11435/api/tags | head -c 400

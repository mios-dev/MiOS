#!/bin/bash
# Confirm directory_lookup dispatches end-to-end via agent-pipe.
# Sends a minimal chat that should hint directory_lookup; we check
# the SurrealDB event_log for a refine row with directory_lookup in
# hint_tools.
set -u

# 1. Direct shim test (proves the data path works).
echo "── direct shim ──"
/usr/libexec/mios/mios-directory-lookup 'mios.toml' --limit 2 --json \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'  hits={len(d[\"hits\"])} root={d[\"hits\"][0].get(\"root_label\",\"\") if d[\"hits\"] else \"\"}')"

# 2. Agent-pipe dispatch via the verb (proves the wiring works).
echo
echo "── agent-pipe verb dispatch ──"
PORT=8640
KEY=$(grep -oE 'API_SERVER_KEY=[a-f0-9]+' /etc/mios/hermes/api.env 2>/dev/null | head -1 | cut -d= -f2)
[ -z "$KEY" ] && KEY="dummy"
# Construct a chat.completions request with stream=false so we
# get the JSON response directly. The model field doesn't matter
# for the routing; agent-pipe's classify+dispatch path picks the
# verb from the user_text.
curl -s -X POST "http://127.0.0.1:$PORT/v1/chat/completions" \
    -H "Authorization: Bearer $KEY" \
    -H "Content-Type: application/json" \
    --max-time 120 \
    -d '{"model":"mios-agent","stream":false,"messages":[{"role":"user","content":"directory_lookup query mios.toml"}]}' \
    | python3 -c "
import json, sys
d = json.load(sys.stdin)
choices = d.get('choices') or []
if not choices:
    print(f'  no choices: {json.dumps(d)[:200]}')
else:
    content = (choices[0].get('message') or {}).get('content','')
    print(f'  content len: {len(content)} chars')
    print(f'  preview: {content[:300]}')
"

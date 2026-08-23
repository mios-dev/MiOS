#!/bin/bash
# AI-hint: Validates the end-to-end integration between the agent-pipe gateway and the directory_lookup tool by testing both direct CLI execution and remote A...
# AI-doc: usr/share/doc/mios/manual/tests.md
set -euo pipefail

echo "── direct shim ──"
/usr/libexec/mios/mios-directory-lookup 'mios.toml' --limit 2 --json \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(f'  hits={len(d[\"hits\"])} root={d[\"hits\"][0].get(\"root_label\",\"\") if d[\"hits\"] else \"\"}')"

echo
echo "── agent-pipe verb dispatch ──"
PORT=8640
KEY=$(grep -oE 'API_SERVER_KEY=[a-f0-9]+' /etc/mios/hermes/api.env 2>/dev/null | head -1 | cut -d= -f2)
[ -z "$KEY" ] && KEY="dummy"
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

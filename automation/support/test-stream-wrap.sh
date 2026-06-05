#!/bin/bash
# Stream a prompt that routes to a sub-agent (NOT chat) and
# inspect the response shape. The final content should be wrapped
# in <details type="reasoning"> with the polished/💯/📋 main
# content below; <think> tags should be absent.
set -euo pipefail

PORT="${MIOS_PORT_AGENT_PIPE:-8640}"
KEY=$(grep -oE 'MIOS_AI_KEY=[A-Za-z0-9-]+' /etc/mios/hermes/api.env \
    2>/dev/null | head -1 | cut -d= -f2)
[[ -n "$KEY" ]] || KEY="dummy"

# A prompt that won't classify as chat -- forces the agent path
# (and thus the streaming sub-agent proxy we just patched).
PROMPT="explain in one line what mios-find does"

curl -sN -H "Authorization: Bearer $KEY" \
     -H "Content-Type: application/json" \
     -X POST "http://127.0.0.1:${PORT}/v1/chat/completions" \
     -d "{\"model\":\"mios-agent\",\"stream\":true,\"messages\":[{\"role\":\"user\",\"content\":\"$PROMPT\"}]}" \
     --max-time 90 \
     > /tmp/stream-wrap-test.txt 2>&1

echo "=== status events ==="
grep -oE 'mios_status[^}]+' /tmp/stream-wrap-test.txt | head -10
echo
echo "=== content deltas (look for <details, <think) ==="
python3 - <<'PYEOF'
import json, re
with open("/tmp/stream-wrap-test.txt") as f:
    body = f.read()
content_parts = []
for line in body.splitlines():
    if not line.startswith("data:"): continue
    data = line[5:].lstrip()
    if data == "[DONE]": continue
    try: chunk = json.loads(data)
    except Exception: continue
    for ch in (chunk.get("choices") or []):
        delta = ch.get("delta") or {}
        c = delta.get("content")
        if c: content_parts.append(c)
joined = "".join(content_parts)
has_details = "<details" in joined
has_think = "<think>" in joined.lower()
print(f"  total content chars: {len(joined)}")
print(f"  has <details> wrapper: {has_details}")
print(f"  has <think> leak:      {has_think}")
print(f"  first 400 chars:\n    {joined[:400]!r}")
print(f"  last 200 chars:\n    {joined[-200:]!r}")
if has_details and not has_think:
    print("PASS")
else:
    print("FAIL")
PYEOF

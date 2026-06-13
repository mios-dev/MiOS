#!/bin/bash
# AI-hint: A diagnostic script to probe Open WebUI's database and API endpoints for prompt suggestion configurations, used by agents to verify available UI prompts and configuration keys in the webui.db and via the local API.
# AI-related: localhost:3030
# AI-functions: print
set -euo pipefail

echo "── webui.db prompt_suggestions ──"
python3 <<'PYEOF'
import json
import sqlite3

c = sqlite3.connect("/var/lib/mios/open-webui/webui.db")
row = c.execute("SELECT data FROM config WHERE id=1").fetchone()
d = json.loads(row[0]) if row else {}
print("  top-level keys:", sorted(d.keys()))
print()
ui = d.get("ui") or {}
print("  data.ui keys:", sorted(ui.keys()))
print()
print("  data.ui.prompt_suggestions sample:")
print("   ", json.dumps(ui.get("prompt_suggestions"), indent=2)[:600])
print()
# OWUI sometimes has a separate prompt table too.
try:
    prompts = c.execute("SELECT id, title, content FROM prompt LIMIT 5").fetchall()
    print(f"  `prompt` table rows: {len(prompts)}")
    for p in prompts:
        print(f"    id={p[0]!r} title={str(p[1])[:50]!r}")
except sqlite3.Error as e:
    print(f"  `prompt` table: {e}")
PYEOF

echo
echo "── live API: GET /api/v1/users/user/settings ──"
TOKEN=$(python3 -c "
import sqlite3
c=sqlite3.connect('/var/lib/mios/open-webui/webui.db')
r=c.execute(\"SELECT a.key FROM api_key a JOIN user u ON u.id=a.user_id WHERE u.role='admin' LIMIT 1\").fetchone()
print(r[0] if r else '')
")
curl -sf -H "Authorization: Bearer $TOKEN" \
    http://localhost:3030/api/v1/users/user/settings \
    | python3 -m json.tool 2>&1 | head -30 || echo "  (call failed)"

echo
echo "── live API: GET /api/v1/configs ──"
curl -s -o /tmp/owui-cfg.json -w '%{http_code}\n' \
    -H "Authorization: Bearer $TOKEN" \
    http://localhost:3030/api/v1/configs
python3 -c "
import json
try:
    d = json.load(open('/tmp/owui-cfg.json'))
    keys = [k for k in d.keys() if 'sug' in k.lower() or 'prompt' in k.lower()]
    print(f'  relevant keys: {keys}')
    for k in keys:
        print(f'  {k}: {str(d[k])[:200]}')
except Exception as e:
    print(f'  parse fail: {e}')
"

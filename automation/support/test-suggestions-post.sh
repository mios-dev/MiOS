#!/bin/bash
set -u
TOKEN=$(python3 - <<'PYEOF'
import sqlite3
c=sqlite3.connect("/var/lib/mios/open-webui/webui.db")
r=c.execute("SELECT a.key FROM api_key a JOIN user u ON u.id=a.user_id LIMIT 1").fetchone()
print(r[0] if r else "")
PYEOF
)

echo "── POST 2 test chips ──"
curl -s -o /tmp/p.txt -w 'status=%{http_code}\n' \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -X POST -d '{"suggestions":[{"title":["alpha","sub"],"content":"alpha-content"},{"title":["beta","sub"],"content":"beta-content"}]}' \
    http://localhost:3030/api/v1/configs/suggestions
echo "── response body ──"
cat /tmp/p.txt
echo
echo
echo "── GET back ──"
curl -s -H "Authorization: Bearer $TOKEN" \
    http://localhost:3030/api/v1/configs/suggestions
echo
echo
echo "── webui.db state ──"
python3 - <<'PYEOF'
import json, sqlite3
c=sqlite3.connect("/var/lib/mios/open-webui/webui.db")
row=c.execute("SELECT data FROM config WHERE id=1").fetchone()
d=json.loads(row[0])
print(json.dumps((d.get("ui") or {}).get("prompt_suggestions") or [], indent=2)[:500])
PYEOF

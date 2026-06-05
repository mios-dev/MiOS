#!/bin/bash
set -euo pipefail
TOKEN=$(python3 -c "
import sqlite3
c=sqlite3.connect('/var/lib/mios/open-webui/webui.db')
r=c.execute(\"SELECT a.key FROM api_key a JOIN user u ON u.id=a.user_id WHERE u.role='admin' LIMIT 1\").fetchone()
print(r[0] if r else '')
")

echo "=== probe config routes ==="
for p in \
    /api/v1/configs/import \
    /api/v1/configs/export \
    /api/v1/configs/default/suggestions \
    /api/v1/configs/suggestions \
    /api/v1/configs/interface \
    /api/v1/configs/banners \
    /api/v1/configs/code_execution \
    /api/v1/configs/google_drive \
    /api/v1/configs/onedrive \
    /api/v1/configs/models \
    /api/v1/configs/models/default \
    /api/v1/configs/tool_servers \
    /api/v1/users/default/permissions ; do
    code_get=$(curl -s -o /dev/null -w '%{http_code}' \
        -H "Authorization: Bearer $TOKEN" "http://localhost:3030$p")
    code_post=$(curl -s -o /dev/null -w '%{http_code}' \
        -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
        -X POST -d '{}' "http://localhost:3030$p")
    printf '  %-46s GET=%-4s POST=%s\n' "$p" "$code_get" "$code_post"
done

echo
echo "=== GET /api/v1/configs/import (often returns full config) ==="
curl -s -H "Authorization: Bearer $TOKEN" \
    http://localhost:3030/api/v1/configs/export | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print('  top-level keys:', sorted(d.keys())[:30])
    ui = d.get('ui') or {}
    print('  ui keys with prompt_*:', [k for k in ui.keys() if 'prompt' in k.lower() or 'sug' in k.lower()])
except Exception as e:
    print(f'  parse: {e}')
"

#!/bin/bash
set -u
TOKEN=$(python3 -c "
import sqlite3
c=sqlite3.connect('/var/lib/mios/open-webui/webui.db')
r=c.execute(\"SELECT a.key FROM api_key a JOIN user u ON u.id=a.user_id WHERE u.role='admin' LIMIT 1\").fetchone()
print(r[0] if r else '')
")
echo "=== suggestions via API ==="
curl -s -H "Authorization: Bearer $TOKEN" \
    http://localhost:3030/api/v1/configs/suggestions | python3 -m json.tool

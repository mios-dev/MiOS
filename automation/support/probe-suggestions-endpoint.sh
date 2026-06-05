#!/bin/bash
set -euo pipefail
TOKEN=$(python3 -c "
import sqlite3
c=sqlite3.connect('/var/lib/mios/open-webui/webui.db')
r=c.execute(\"SELECT a.key FROM api_key a JOIN user u ON u.id=a.user_id WHERE u.role='admin' LIMIT 1\").fetchone()
print(r[0] if r else '')
")

echo "=== GET /api/v1/configs/suggestions ==="
curl -s -H "Authorization: Bearer $TOKEN" \
    http://localhost:3030/api/v1/configs/suggestions | python3 -m json.tool

echo
echo "=== POST with single suggestion to learn schema ==="
curl -s -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -X POST -d '{"suggestions":[{"title":["test","subtitle"],"content":"test"}]}' \
    http://localhost:3030/api/v1/configs/suggestions | python3 -m json.tool

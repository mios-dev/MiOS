#!/bin/bash
set -euo pipefail
TOKEN=$(python3 -c "
import sqlite3
c = sqlite3.connect('/var/lib/mios/open-webui/webui.db')
r = c.execute(\"SELECT a.key FROM api_key a JOIN user u ON u.id=a.user_id WHERE u.role='admin' LIMIT 1\").fetchone()
print(r[0] if r else '')
")
COL=8c721cc0-3dd4-5e8d-ad9c-5913a7368dfe

echo "=== raw response shape ==="
curl -s -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -X POST \
    -d "{\"collection_names\":[\"$COL\"],\"query\":\"MiOS\",\"k\":3,\"r\":0.0}" \
    http://localhost:3030/api/v1/retrieval/query/collection \
    | python3 -m json.tool | head -40

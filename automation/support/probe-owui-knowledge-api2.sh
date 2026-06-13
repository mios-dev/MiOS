#!/bin/bash
# AI-hint: A diagnostic script that extracts the Open WebUI admin token from the local SQLite DB to probe the knowledge base API endpoints, verify retrieval functionality, and list available OpenAPI paths for RAG operations.
# AI-related: localhost:3030
set -euo pipefail
TOKEN=$(python3 -c "
import sqlite3
c = sqlite3.connect('/var/lib/mios/open-webui/webui.db')
r = c.execute(\"SELECT a.key FROM api_key a JOIN user u ON u.id=a.user_id WHERE u.role='admin' ORDER BY a.created_at DESC LIMIT 1\").fetchone()
print(r[0] if r else '')
")
echo "TOKEN=${TOKEN:0:12}..."

COL_ID="8c721cc0-3dd4-5e8d-ad9c-5913a7368dfe"

echo
echo "=== knowledge list ==="
curl -s -o /tmp/k.json -w '%{http_code}\n' \
    -H "Authorization: Bearer $TOKEN" \
    "http://localhost:3030/api/v1/knowledge/"
head -c 200 /tmp/k.json
echo

echo
echo "=== probe endpoints (POST + GET) ==="
for method in GET POST; do
    for p in \
        /api/v1/retrieval/process/query \
        /api/v1/retrieval/query/collection \
        /api/v1/retrieval/query \
        "/api/v1/knowledge/$COL_ID/" \
        /api/v1/retrieval/api/embedding ; do
        code=$(curl -s -o /dev/null -w '%{http_code}' \
            -H "Authorization: Bearer $TOKEN" \
            -H 'Content-Type: application/json' \
            -X $method -d '{"query":"test","collection_names":["'$COL_ID'"],"k":3,"r":0.0}' \
            "http://localhost:3030$p")
        printf '  %-50s %-4s %s\n' "$p" "$method" "$code"
    done
done

echo
echo "=== openapi.json for hints ==="
curl -sf "http://localhost:3030/openapi.json" | python3 -c "
import json, sys
d = json.load(sys.stdin)
paths = d.get('paths', {})
for p in sorted(paths.keys()):
    if 'retrieval' in p or 'knowledge' in p:
        methods = list(paths[p].keys())
        print(f'  {p}  {methods}')
" 2>&1 | head -25

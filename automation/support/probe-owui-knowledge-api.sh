#!/bin/bash
# Probe OWUI knowledge API to find the correct retrieval endpoint
# for this OWUI version. Existing scripts use:
#   /api/v1/retrieval/process/query
# but a fresh probe returned 405, so the path may have moved
# (different OWUI versions have different shapes).
set -euo pipefail

DB=/var/lib/mios/open-webui/webui.db
TOKEN=$(sqlite3 "$DB" \
    "SELECT a.key FROM api_key a JOIN user u ON u.id=a.user_id WHERE u.role='admin' ORDER BY a.created_at DESC LIMIT 1;")
echo "TOKEN=${TOKEN:0:12}..."
echo

echo "=== knowledge list (works?) ==="
curl -sf -H "Authorization: Bearer $TOKEN" \
    http://localhost:3030/api/v1/knowledge/ | head -c 800
echo
echo

# Capture an existing collection id so we can probe per-collection endpoints.
COL_ID=$(curl -sf -H "Authorization: Bearer $TOKEN" \
    http://localhost:3030/api/v1/knowledge/ \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print((d[0] if d else {}).get('id',''))")
echo "first collection id: $COL_ID"
echo

echo "=== probe potential query endpoints ==="
for p in \
    /api/v1/retrieval/process/query \
    /api/v1/retrieval/query/collection \
    /api/v1/retrieval/query/file \
    /api/v1/retrieval/query \
    /api/v1/knowledge/query \
    "/api/v1/knowledge/$COL_ID/query"; do
    code=$(curl -s -o /dev/null -w '%{http_code}' \
        -H "Authorization: Bearer $TOKEN" \
        -H 'Content-Type: application/json' \
        -X POST -d '{"query":"test"}' \
        "http://localhost:3030$p")
    printf '  %-50s %s\n' "$p" "$code"
done

echo
echo "=== probe GET on knowledge/$COL_ID ==="
curl -s -o /dev/null -w '%{http_code}\n' -H "Authorization: Bearer $TOKEN" \
    "http://localhost:3030/api/v1/knowledge/$COL_ID"

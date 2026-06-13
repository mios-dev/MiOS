#!/bin/bash
# AI-hint: A diagnostic script that probes Open WebUI API endpoints for knowledge processing, reindexing, and retrieval status to verify the health and reachability of the RAG pipeline.
# AI-related: localhost:3030
set -euo pipefail
TOKEN=$(python3 - <<'PYEOF'
import sqlite3
c=sqlite3.connect("/var/lib/mios/open-webui/webui.db")
r=c.execute("SELECT a.key FROM api_key a JOIN user u ON u.id=a.user_id LIMIT 1").fetchone()
print(r[0] if r else "")
PYEOF
)

COL=8c721cc0-3dd4-5e8d-ad9c-5913a7368dfe

echo "=== probe reindex / process / reset endpoints ==="
for path_method in \
    "GET    /api/v1/knowledge/$COL" \
    "POST   /api/v1/knowledge/$COL/reset" \
    "POST   /api/v1/knowledge/$COL/process" \
    "POST   /api/v1/knowledge/$COL/file/process" \
    "POST   /api/v1/knowledge/$COL/files/process" \
    "POST   /api/v1/knowledge/reindex" \
    "POST   /api/v1/knowledge/$COL/file/add" \
    "POST   /api/v1/files/process" \
    "POST   /api/v1/retrieval/process/files/batch" \
    "POST   /api/v1/retrieval/process/file" \
    "POST   /api/v1/retrieval/api/embedding/reset"; do
    method="${path_method%% *}"
    path="${path_method##* }"
    code=$(curl -s -o /dev/null -w '%{http_code}' \
        -H "Authorization: Bearer $TOKEN" \
        -H 'Content-Type: application/json' \
        -X $method -d '{}' "http://localhost:3030$path")
    printf '  %-6s %-50s %s\n' "$method" "$path" "$code"
done

echo
echo "=== GET knowledge collection detail (shows file list) ==="
curl -sf -H "Authorization: Bearer $TOKEN" \
    "http://localhost:3030/api/v1/knowledge/$COL" \
    | python3 -c "
import json, sys
d = json.load(sys.stdin)
files = d.get('files') or (d.get('data') or {}).get('file_ids') or []
print(f'  files count: {len(files) if isinstance(files, list) else files}')
if isinstance(files, list) and files:
    sample = files[0]
    if isinstance(sample, dict):
        print(f'  sample file keys: {sorted(sample.keys())}')
    else:
        print(f'  sample file: {sample!r}')
" 2>&1 | head -10

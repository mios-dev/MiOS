#!/bin/bash
# AI-hint: Triggers a full re-vectorization of Open WebUI knowledge collections via the /api/v1/knowledge/reindex endpoint to rebuild ChromaDB collections after a cache wipe or data migration.
# AI-related: /usr/libexec/mios/mios-knowledge-search, mios-knowledge-search, mios-cache-clear, localhost:3030
# Force OWUI to re-vectorize all knowledge collections. After a
# day-0 wipe (mios-cache-clear --all) the vector_db/ tree is
# empty even though the knowledge + file rows persist; this
# triggers OWUI to rebuild the chroma collections from the
# stored file content.
set -euo pipefail

TOKEN=$(python3 - <<'PYEOF'
import sqlite3
c=sqlite3.connect("/var/lib/mios/open-webui/webui.db")
r=c.execute("SELECT a.key FROM api_key a JOIN user u ON u.id=a.user_id LIMIT 1").fetchone()
print(r[0] if r else "")
PYEOF
)

if [[ -z "$TOKEN" ]]; then
    echo "  no admin api_key in webui.db"
    exit 1
fi

echo "── POST /api/v1/knowledge/reindex ──"
curl -s -o /tmp/reindex.txt -w 'status=%{http_code}\n' \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    -X POST -d '{}' \
    http://localhost:3030/api/v1/knowledge/reindex
echo "── body ──"
head -c 600 /tmp/reindex.txt
echo
echo

echo "── vector_db state after reindex ──"
ls -la /var/lib/mios/open-webui/vector_db/ 2>/dev/null | head -10

echo
echo "── verify by hitting knowledge_search ──"
sleep 3
/usr/libexec/mios/mios-knowledge-search "MiOS architecture" --top-k 3 --json \
    | python3 -m json.tool | head -30

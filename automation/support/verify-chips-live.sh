#!/bin/bash
set -u

TOKEN_PY=$(python3 - <<'PYEOF'
import sqlite3
c = sqlite3.connect("/var/lib/mios/open-webui/webui.db")
r = c.execute(
    "SELECT a.key FROM api_key a "
    "JOIN user u ON u.id=a.user_id "
    "WHERE u.role='admin' LIMIT 1"
).fetchone()
print(r[0] if r else "")
PYEOF
)

if [[ -z "$TOKEN_PY" ]]; then
    echo "  no admin api_key in webui.db"
    exit 1
fi
echo "  token: ${TOKEN_PY:0:12}..."

echo
echo "── GET /api/v1/configs/suggestions ──"
curl -sv -H "Authorization: Bearer $TOKEN_PY" \
    http://localhost:3030/api/v1/configs/suggestions 2>&1 \
    | grep -E '^[<>]|HTTP|content-length' | head -10

echo
echo "── body ──"
curl -s -H "Authorization: Bearer $TOKEN_PY" \
    http://localhost:3030/api/v1/configs/suggestions \
    | python3 -m json.tool 2>&1 | head -30

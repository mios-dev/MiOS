#!/bin/bash
# AI-hint: Fetches and formats the system's configuration suggestions from the local Open WebUI API by extracting the admin token from the local SQLite database to provide a JSON-formatted list of available configuration options.
# AI-related: localhost:3030
set -euo pipefail
TOKEN=$(python3 -c "
import sqlite3
c=sqlite3.connect('/var/lib/mios/open-webui/webui.db')
r=c.execute(\"SELECT a.key FROM api_key a JOIN user u ON u.id=a.user_id WHERE u.role='admin' LIMIT 1\").fetchone()
print(r[0] if r else '')
")
echo "=== suggestions via API ==="
curl -s -H "Authorization: Bearer $TOKEN" \
    http://localhost:3030/api/v1/configs/suggestions | python3 -m json.tool

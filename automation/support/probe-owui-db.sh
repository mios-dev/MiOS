#!/bin/bash
# AI-hint: Probes the Open WebUI SQLite database at /var/lib/mios/open-webui/webui.db to list sample users, API keys, and knowledge collections for debugging and verifying data integrity.
# AI-functions: print
set -euo pipefail
python3 - <<'PYEOF'
import sqlite3
c = sqlite3.connect("/var/lib/mios/open-webui/webui.db")
print("=== users ===")
for r in c.execute("SELECT id, name, email, role FROM user LIMIT 5"):
    print(" ", r)
print()
print("=== api_keys ===")
for r in c.execute("SELECT id, user_id, substr(key,1,12) FROM api_key LIMIT 5"):
    print(" ", r)
print()
print("=== knowledge collections ===")
for r in c.execute("SELECT id, name FROM knowledge"):
    print(" ", r)
PYEOF

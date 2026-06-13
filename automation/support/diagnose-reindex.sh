#!/bin/bash
# AI-hint: Diagnostic script to debug vector database integrity by checking `mios-open-webui` logs, ChromaDB SQLite table counts/collections, and verifying if file content exists in the `webui.db` database.
# AI-related: mios-open-webui, mios-open-webui.service
set -euo pipefail

echo "=== OWUI logs (reindex / chroma / vector) ==="
journalctl -u mios-open-webui.service --since '5 min ago' --no-pager \
    | grep -iE 'reindex|chroma|embed|vector|sentence-trans|all-minilm' \
    | tail -20

echo
echo "=== chroma sqlite tables + row counts ==="
python3 - <<'PYEOF'
import sqlite3
c = sqlite3.connect("/var/lib/mios/open-webui/vector_db/chroma.sqlite3")
for (name,) in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"):
    try:
        n = c.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        print(f"  {name}: {n}")
    except sqlite3.Error as e:
        print(f"  {name}: ERR {e}")
PYEOF

echo
echo "=== chroma collections ==="
python3 - <<'PYEOF'
import sqlite3
c = sqlite3.connect("/var/lib/mios/open-webui/vector_db/chroma.sqlite3")
try:
    rows = c.execute("SELECT id, name FROM collections").fetchall()
    print(f"  count: {len(rows)}")
    for r in rows[:10]:
        print(f"  {r}")
except sqlite3.Error as e:
    print(f"  err: {e}")
PYEOF

echo
echo "=== file content present? ==="
python3 - <<'PYEOF'
import json, sqlite3
c = sqlite3.connect("/var/lib/mios/open-webui/webui.db")
row = c.execute(
    "SELECT id, filename, data FROM file LIMIT 3"
).fetchall()
for r in row:
    fid, fn, dat = r
    try:
        d = json.loads(dat) if dat else {}
        content_len = len(d.get("content") or "")
    except Exception:
        content_len = -1
    print(f"  {fid[:12]}.. {fn} content_len={content_len}")
PYEOF

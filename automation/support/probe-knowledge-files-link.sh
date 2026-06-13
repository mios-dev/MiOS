#!/bin/bash
# AI-hint: A diagnostic script that queries the open-webui.db SQLite database to audit knowledge collection mappings, file counts, and MiOS-specific metadata markers to verify data integrity and synchronization.
# AI-related: mios-managed, mios-owui-apply-knowledge
# AI-functions: print
set -euo pipefail
python3 - <<'PYEOF'
import json, sqlite3
c = sqlite3.connect("/var/lib/mios/open-webui/webui.db")

print("=== knowledge collections + their file lists ===")
for kid, name, data in c.execute(
        "SELECT id, name, data FROM knowledge"):
    print(f"\n  collection: {name} ({kid})")
    try:
        d = json.loads(data) if data else {}
        file_ids = d.get("file_ids") or []
        print(f"    data.file_ids count: {len(file_ids)}")
        if file_ids:
            print(f"    first 3: {file_ids[:3]}")
    except Exception as e:
        print(f"    data parse fail: {e}")

print()
print("=== file table ===")
n = 0
for r in c.execute("SELECT id, filename, hash FROM file LIMIT 5"):
    print(f"  {r}")
    n += 1
total = c.execute("SELECT COUNT(*) FROM file").fetchone()[0]
print(f"  total files in `file` table: {total}")

print()
print("=== files with mios-managed marker ===")
mios_files = c.execute(
    "SELECT COUNT(*) FROM file WHERE meta LIKE '%mios-owui-apply-knowledge%'"
).fetchone()[0]
print(f"  count: {mios_files}")
PYEOF

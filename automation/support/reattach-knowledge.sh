#!/bin/bash
# AI-hint: This script updates the `webui.db` database to link "MiOS Session Memory" and "MiOS Documentation" knowledge IDs to the `mios-agent` model metadata, enabling full RAG capabilities for the OWUI interface.
# AI-related: mios-agent, mios-open-webui, mios-open-webui.service
# Re-attach the canonical MiOS knowledge collections to the
# mios-agent OWUI model. Operator directive: "WE DO WANT FULL
# RAG CAPABILITIES USING OWUI ... WITH FULL MEMORY, KNOWLEDGE,
# AND ALL OTHER RELATED FUNCTIONALITIES MUST WORK IN THE STACK
# NATIVELY".
#
# Looks up the existing knowledge rows by name + re-attaches by
# id+name (the shape OWUI's middleware expects in model.meta).
set -euo pipefail
python3 - <<'PYEOF'
import json
import sqlite3

DB = "/var/lib/mios/open-webui/webui.db"
WANTED_NAMES = ["MiOS Session Memory", "MiOS Documentation"]

c = sqlite3.connect(DB)

# Build the canonical knowledge entries from the knowledge table.
knowledge_entries = []
for name in WANTED_NAMES:
    cur = c.execute(
        "SELECT id, name, description FROM knowledge WHERE name = ? LIMIT 1;",
        (name,))
    row = cur.fetchone()
    if row:
        kid, kname, kdesc = row
        knowledge_entries.append({
            "id": kid,
            "name": kname,
            "description": kdesc or "",
        })
        print(f"  found knowledge row: id={kid!r} name={kname!r}")
    else:
        print(f"  WARN: knowledge row {name!r} not present in webui.db")

if not knowledge_entries:
    print("  no knowledge rows to attach -- nothing to do")
    c.close()
    raise SystemExit(0)

# Attach to every mios-agent model row.
cur = c.execute(
    "SELECT id, name, meta FROM model "
    "WHERE id LIKE '%mios%' OR name LIKE '%MiOS%';"
)
rows = cur.fetchall()
for mid, name, meta in rows:
    try:
        m = json.loads(meta) if meta else {}
    except Exception:
        m = {}
    if not isinstance(m, dict):
        m = {}
    m["knowledge"] = knowledge_entries
    new_meta = json.dumps(m)
    c.execute("UPDATE model SET meta = ? WHERE id = ?",
              (new_meta, mid))
    print(f"  attached {len(knowledge_entries)} knowledge entries "
          f"to model {mid!r} ({name!r})")
c.commit()
c.close()
PYEOF

echo
echo "  -> systemctl restart mios-open-webui.service"
systemctl restart mios-open-webui.service 2>&1 | tail -3

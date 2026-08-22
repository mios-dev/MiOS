# AI-hint: !/bin/bash Removes pre-LLM RAG knowledge attachments from Open WebUI models in the database to disable automatic search-query decomposition, ...
# AI-doc: usr/share/doc/mios/manual/_harvest/automation_support_detach_knowledge_from_model_sh.md
set -euo pipefail
python3 - <<'PYEOF'
import json
import sqlite3

DB = "/var/lib/mios/open-webui/webui.db"
c = sqlite3.connect(DB)
cur = c.execute(
    "SELECT id, name, meta FROM model "
    "WHERE id LIKE '%mios%' OR name LIKE '%MiOS%';"
)
rows = cur.fetchall()
for mid, name, meta in rows:
    try:
        m = json.loads(meta) if meta else {}
    except Exception:
        print(f"  skip {mid}: meta unparseable")
        continue
    if not isinstance(m, dict):
        continue
    before = m.get("knowledge")
    if not before:
        print(f"  skip {mid!r} ({name!r}): no knowledge attached")
        continue
    m.pop("knowledge", None)
    new_meta = json.dumps(m)
    c.execute("UPDATE model SET meta = ? WHERE id = ?",
              (new_meta, mid))
    print(f"  detached {len(before)} knowledge entries "
          f"from model {mid!r} ({name!r})")
c.commit()
c.close()
PYEOF

echo
echo "  -> systemctl restart mios-open-webui.service"
systemctl restart mios-open-webui.service 2>&1 | tail -3

#!/bin/bash
# AI-hint: Queries the Open WebUI database to inspect the 'model' table for MiOS-specific configurations, revealing active knowledge bases, RAG settings, and web_search parameters for the mios-agent.
# AI-related: mios-agent
# AI-functions: print
# Inspect the OWUI 'model' row for mios-agent to see what knowledge
# / web_search params are attached + firing pre-call RAG.
set -euo pipefail
python3 - <<'PYEOF'
import json
import sqlite3

DB = "/var/lib/mios/open-webui/webui.db"
c = sqlite3.connect(DB)
cur = c.execute(
    "SELECT id, name, meta, params FROM model "
    "WHERE id LIKE '%mios%' OR name LIKE '%MiOS%';"
)
rows = cur.fetchall()
for row in rows:
    mid, name, meta, params = row
    print(f"=== model id={mid!r}  name={name!r} ===")
    try:
        m = json.loads(meta) if meta else {}
    except Exception:
        m = {"_unparsed": meta}
    try:
        p = json.loads(params) if params else {}
    except Exception:
        p = {"_unparsed": params}
    print("  meta keys:", sorted(m.keys()) if isinstance(m, dict) else m)
    if isinstance(m, dict):
        ke = m.get("knowledge")
        if ke:
            if isinstance(ke, list):
                for k in ke:
                    print(f"    knowledge entry: id={k.get('id')!r} name={k.get('name')!r}")
            else:
                print(f"    knowledge: {ke!r}")
        for k in ("toolIds", "filterIds", "actionIds"):
            v = m.get(k)
            if v:
                print(f"    {k}: {v}")
    print("  params keys:", sorted(p.keys()) if isinstance(p, dict) else p)
    if isinstance(p, dict):
        for k in ("web_search", "rag", "system", "function_calling"):
            if k in p:
                print(f"    params.{k}: {p[k]!r}")
    print()
c.close()
PYEOF

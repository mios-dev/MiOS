#!/bin/bash
# AI-hint: Probes the open-webui.db database to extract and display memory-related configurations in user settings and global feature flags to diagnose memory-related UI or permission issues.
set -euo pipefail

echo "── user.settings.ui (memory field) ──"
python3 <<'PYEOF'
import json, sqlite3
c = sqlite3.connect("/var/lib/mios/open-webui/webui.db")
for r in c.execute("SELECT id, name, settings FROM user LIMIT 5"):
    uid, name, settings = r
    try:
        s = json.loads(settings) if settings else {}
    except Exception:
        s = {}
    print(f"  user={name[:20]} settings.ui={json.dumps(s.get('ui') or {}, indent=2)[:400]}")
PYEOF

echo
echo "── config user-permissions.features memory ──"
python3 <<'PYEOF'
import json, sqlite3
c = sqlite3.connect("/var/lib/mios/open-webui/webui.db")
row = c.execute("SELECT data FROM config WHERE id=1").fetchone()
d = json.loads(row[0]) if row else {}

def walk(prefix, obj, depth=0):
    if depth > 4: return
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else k
            if "memory" in k.lower():
                print(f"  {full} = {json.dumps(v)[:200]}")
            walk(full, v, depth + 1)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(f"{prefix}[{i}]", v, depth + 1)

walk("", d)
PYEOF

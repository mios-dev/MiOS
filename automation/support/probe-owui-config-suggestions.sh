#!/bin/bash
# AI-hint: Parses the Open WebUI database to identify and list configuration keys related to suggestions, following, and autocomplete to help agents diagnose or suggest UI behavior modifications.
set -euo pipefail
python3 - <<'PYEOF'
import json
import sqlite3

c = sqlite3.connect("/var/lib/mios/open-webui/webui.db")
row = c.execute("SELECT data FROM config WHERE id=1").fetchone()
if not row:
    print("no config row")
    raise SystemExit(0)
d = json.loads(row[0])

# Walk every key that mentions suggestion / follow / autocomplete.
def walk(prefix, obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else k
            if any(t in k.lower()
                   for t in ("suggestion", "follow", "autocomplete",
                             "starter")):
                kind = type(v).__name__
                print(f"  {full}  ({kind}) = "
                      f"{json.dumps(v)[:100] if v else v}")
            walk(full, v)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(f"{prefix}[{i}]", v)

walk("", d)
PYEOF

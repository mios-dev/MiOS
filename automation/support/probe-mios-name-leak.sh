#!/bin/bash
set -u
python3 - <<'PYEOF'
import json, sqlite3
c = sqlite3.connect("/var/lib/mios/open-webui/webui.db")

print("── model rows ──")
for mid, name, meta in c.execute("SELECT id, name, meta FROM model"):
    print(f"  id={mid!r}  name={name!r}")
    try:
        m = json.loads(meta) if meta else {}
    except Exception:
        m = {}
    if isinstance(m, dict):
        for k in ("name", "title", "description", "profile_image_url"):
            if k in m:
                v = str(m[k])[:80]
                print(f"    meta.{k}: {v!r}")

print()
print("── function rows (pipes + filters) ──")
for fid, name, t, meta in c.execute(
        "SELECT id, name, type, meta FROM function"):
    print(f"  id={fid!r}  type={t!r}  name={name!r}")
    try:
        m = json.loads(meta) if meta else {}
    except Exception:
        m = {}
    if isinstance(m, dict):
        for k in ("name", "title", "description"):
            if k in m:
                v = str(m[k])[:80]
                print(f"    meta.{k}: {v!r}")

print()
print("── config.data.ui.name ──")
row = c.execute("SELECT data FROM config WHERE id=1").fetchone()
d = json.loads(row[0]) if row else {}
print(f"  ui.name: {(d.get('ui') or {}).get('name','-')}")
print(f"  webui.name: {(d.get('webui') or {}).get('name','-')}")

# Walk for any 'MiOS-Agent' or 'MiOS Agent' literal
def walk(prefix, obj, depth=0):
    if depth > 5: return
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk(f"{prefix}.{k}", v, depth + 1)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk(f"{prefix}[{i}]", v, depth + 1)
    elif isinstance(obj, str):
        if 'MiOS-Agent' in obj or 'MiOS Agent' in obj:
            print(f"  LEAK at {prefix}: {obj[:80]!r}")

print()
print("── config.data 'MiOS-Agent'/'MiOS Agent' leaks ──")
walk("data", d)
PYEOF

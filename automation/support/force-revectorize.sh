#!/bin/bash
# Force OWUI to re-vectorize every file in every MiOS knowledge
# collection. OWUI's /api/v1/knowledge/reindex only refreshes
# metadata (returns 200 in ~4ms even for 32 files). The actual
# chunk + embed pipeline fires on /api/v1/knowledge/{id}/file/add.
# We remove each file then add it back -- forcing the embed call.
set -u

TOKEN=$(python3 - <<'PYEOF'
import sqlite3
c=sqlite3.connect("/var/lib/mios/open-webui/webui.db")
r=c.execute("SELECT a.key FROM api_key a JOIN user u ON u.id=a.user_id LIMIT 1").fetchone()
print(r[0] if r else "")
PYEOF
)

[[ -z "$TOKEN" ]] && { echo "  no admin api_key"; exit 1; }
export TOKEN

# Walk every collection + its file_ids.
python3 - <<'PYEOF'
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request

TOKEN = os.environ.get("TOKEN")
c = sqlite3.connect("/var/lib/mios/open-webui/webui.db")
collections = c.execute(
    "SELECT id, name, data FROM knowledge").fetchall()

total_files = 0
total_ok = 0
for kid, name, kdata in collections:
    try:
        d = json.loads(kdata) if kdata else {}
    except Exception:
        d = {}
    file_ids = d.get("file_ids") or []
    print(f"\n  === {name} ({kid}) -- {len(file_ids)} files ===")
    for fid in file_ids:
        body = json.dumps({"file_id": fid}).encode("utf-8")
        # POST file/add -- triggers process_file_content() which
        # chunks + embeds via the configured embedding model.
        req = urllib.request.Request(
            f"http://localhost:3030/api/v1/knowledge/{kid}/file/add",
            data=body,
            headers={
                "Authorization": f"Bearer {TOKEN}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                resp = r.read().decode("utf-8", errors="replace")
                ok = r.status == 200
        except urllib.error.HTTPError as e:
            resp = e.read().decode("utf-8", errors="replace")[:120]
            ok = False
        except Exception as e:
            resp = f"{type(e).__name__}: {e}"
            ok = False
        elapsed = time.time() - t0
        total_files += 1
        if ok:
            total_ok += 1
            print(f"    + {fid[:12]}.. ({elapsed:.1f}s) OK")
        else:
            # 400 with "already exists" is fine -- already linked,
            # just means the embed didn't re-run.
            if "already exists" in resp.lower():
                print(f"    = {fid[:12]}.. already linked, "
                      f"skip ({elapsed:.1f}s)")
            else:
                print(f"    ! {fid[:12]}.. ({elapsed:.1f}s) "
                      f"FAIL {resp[:120]}")

print(f"\n  TOTAL: {total_ok}/{total_files} files added")
PYEOF

echo
echo "── vector_db after force-revectorize ──"
python3 - <<'PYEOF'
import sqlite3
c = sqlite3.connect("/var/lib/mios/open-webui/vector_db/chroma.sqlite3")
for tbl in ("collections", "embeddings", "embedding_metadata"):
    try:
        n = c.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl}: {n}")
    except sqlite3.Error as e:
        print(f"  {tbl}: ERR {e}")
PYEOF

echo
echo "── smoke-test knowledge_search ──"
/usr/libexec/mios/mios-knowledge-search "MiOS architecture" \
    --collection "MiOS Documentation" --top-k 3 --json \
    | python3 -m json.tool | head -25

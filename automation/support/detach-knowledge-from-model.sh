#!/bin/bash
# Remove the knowledge collection attachments from the mios-agent
# OWUI model. With knowledge attached, OWUI runs a pre-LLM RAG
# pre-call that decomposes the user prompt into search queries and
# fires "Searching Knowledge / Querying" status events BEFORE the
# prompt reaches agent-pipe -- even for prompts that have nothing
# to do with the MiOS docs (e.g. "find games"). agent-pipe is the
# canonical orchestrator now; knowledge stays reachable via tool
# calls inside the agent flow.
set -u
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
    # Drop knowledge entirely; OWUI's pre-call only fires when
    # m["knowledge"] is a non-empty list.
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

#!/bin/bash
# Disable the mios_sidecar OWUI Filter (active=0, global=0).
# The sidecar was useful pre-agent-pipe to surface sibling-agent
# activity, but agent-pipe is now the canonical orchestrator and
# emits its own SSE status events. Sidecar's hermes-tail polling
# also surfaces stale events as if current, and its post-call
# response can replace the legitimate polished reply.
set -u
DB=/var/lib/mios/open-webui/webui.db

if [[ ! -f "$DB" ]]; then
    echo "  no $DB -- nothing to disable"
    exit 0
fi

python3 - "$DB" <<'PYEOF'
import sqlite3
import sys
db = sys.argv[1]
c = sqlite3.connect(db)
cur = c.execute(
    "SELECT id, name, is_active, is_global FROM function "
    "WHERE id = 'mios_sidecar';"
)
rows = cur.fetchall()
if not rows:
    print("  no mios_sidecar row in function table")
    c.close()
    sys.exit(0)
for fid, name, act, glb in rows:
    print(f"  before: id={fid} name={name} active={act} global={glb}")
c.execute(
    "UPDATE function SET is_active=0, is_global=0 "
    "WHERE id = 'mios_sidecar';")
c.commit()
cur = c.execute(
    "SELECT id, name, is_active, is_global FROM function "
    "WHERE id = 'mios_sidecar';")
for fid, name, act, glb in cur.fetchall():
    print(f"  after:  id={fid} name={name} active={act} global={glb}")
c.close()
PYEOF

# Restart OWUI so the function-registry reload picks up the new flags
echo
echo "  -> systemctl restart mios-open-webui.service"
systemctl restart mios-open-webui.service 2>&1 | tail -3

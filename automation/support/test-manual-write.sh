#!/bin/bash
set -euo pipefail
python3 - <<'PYEOF'
import json, urllib.request

# Send a manual write that mirrors the daemon's shape.
sql = (
    "USE NS mios DB agent; "
    'CREATE directory_entry SET '
    'path = "/tmp/test-row", '
    'parent = "/tmp", '
    'basename = "test-row", '
    'kind = "file", '
    'size = 42, '
    'mtime = time::now(), '
    'ext = ".txt", '
    'summary = "manual test entry", '
    'root_label = "manual-test", '
    'indexed_at = time::now();'
)
req = urllib.request.Request("http://localhost:8000/sql",
    data=sql.encode(),
    headers={"Authorization":"Basic cm9vdDpyb290",
             "Accept":"application/json",
             "Content-Type":"text/plain"},
    method="POST")
r = json.load(urllib.request.urlopen(req, timeout=4))
for i, s in enumerate(r):
    print(f"  stmt {i}: status={s.get('status')} result={str(s.get('result',''))[:200]}")
PYEOF

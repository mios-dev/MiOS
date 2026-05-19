#!/bin/bash
set -u
python3 - <<'PYEOF'
import json, urllib.request
sql = "USE NS mios DB agent; SELECT count() FROM directory_entry GROUP ALL;"
req = urllib.request.Request("http://localhost:8000/sql",
    data=sql.encode(),
    headers={"Authorization":"Basic cm9vdDpyb290",
             "Accept":"application/json",
             "Content-Type":"text/plain"},
    method="POST")
r = json.load(urllib.request.urlopen(req, timeout=4))
for i, s in enumerate(r):
    print(f"  stmt {i}: {s}")
PYEOF

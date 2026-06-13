#!/bin/bash
# AI-hint: A test script that executes a Python snippet to verify the `_upsert_directory_entries` function in `mios_daemon` by batch-inserting mock file records and querying the local SQL database to confirm persistence.
# AI-related: /usr/libexec/mios/mios-daemon, mios-daemon, localhost:8000
# Call _upsert_directory_entries with a 3-row batch + see if rows
# land in the DB.
set -euo pipefail
python3 - <<'PYEOF'
import importlib.machinery, importlib.util, json, os, sys, datetime
os.environ["MIOS_DB_URL"] = "http://localhost:8000"
loader = importlib.machinery.SourceFileLoader(
    "mios_daemon", "/usr/libexec/mios/mios-daemon")
spec = importlib.util.spec_from_loader("mios_daemon", loader)
mod = importlib.util.module_from_spec(spec)
sys.argv = ["mios-daemon", "--help"]
try:
    loader.exec_module(mod)
except SystemExit:
    pass

now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
entries = [
    {
        "path": f"/tmp/batch-test-{i}",
        "parent": "/tmp",
        "basename": f"batch-test-{i}",
        "kind": "file",
        "size": 100 + i,
        "mtime": now_iso,
        "ext": ".txt",
        "summary": f"batch test {i}",
        "root_label": "batch-trace",
    }
    for i in range(3)
]

print(f"calling _upsert with {len(entries)} entries...")
w, e = mod._upsert_directory_entries(entries)
print(f"  result: written={w} errors={e}")

# Verify they landed.
import urllib.request
sql = ('USE NS mios DB agent; '
       'SELECT count() FROM directory_entry '
       'WHERE root_label = "batch-trace" GROUP ALL;')
req = urllib.request.Request("http://localhost:8000/sql",
    data=sql.encode(),
    headers={"Authorization":"Basic cm9vdDpyb290",
             "Accept":"application/json",
             "Content-Type":"text/plain"},
    method="POST")
r = json.load(urllib.request.urlopen(req, timeout=4))
print(f"  verify: {r[-1]}")
PYEOF

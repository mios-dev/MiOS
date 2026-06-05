#!/bin/bash
# Run a single insert via the daemon's _db_post_sync to see the
# actual response shape.
set -euo pipefail
python3 - <<'PYEOF'
import importlib.machinery, importlib.util, json, os, sys
os.environ["MIOS_DB_URL"] = "http://localhost:8000"
# importlib.util.spec_from_file_location returns None for files
# without standard .py extension; use loader directly.
loader = importlib.machinery.SourceFileLoader(
    "mios_daemon", "/usr/libexec/mios/mios-daemon")
spec = importlib.util.spec_from_loader("mios_daemon", loader)
mod = importlib.util.module_from_spec(spec)
sys.argv = ["mios-daemon", "--help"]
try:
    loader.exec_module(mod)
except SystemExit:
    pass
except Exception as e:
    print(f"module load exception: {e}")

sql = (
    'CREATE directory_entry SET '
    'path = "/tmp/trace-row", '
    'parent = "/tmp", '
    'basename = "trace-row", '
    'kind = "file", '
    'size = 1, '
    'mtime = time::now(), '
    'ext = ".txt", '
    'summary = "trace", '
    'root_label = "trace", '
    'indexed_at = time::now();'
)
print(f"sending SQL:\n  {sql[:200]}...")
r = mod._db_post_sync(sql)
print(f"response (top-level): {type(r).__name__} len={len(r) if isinstance(r,list) else '?'}")
for i, s in enumerate(r):
    print(f"  stmt {i}: {s}")
PYEOF

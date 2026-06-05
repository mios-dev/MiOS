#!/bin/bash
# Bisect to find which part of the query breaks.
set -euo pipefail

test_sql() {
    local label="$1"
    local sql="$2"
    python3 - "$sql" <<'PYEOF'
import json, sys, urllib.request
sql = sys.argv[1]
req = urllib.request.Request(
    "http://localhost:8000/sql",
    data=sql.encode("utf-8"),
    headers={
        "Authorization": "Basic cm9vdDpyb290",
        "NS": "mios", "DB": "agent",
        "Accept": "application/json",
        "Content-Type": "text/plain",
    },
    method="POST")
try:
    r = json.load(urllib.request.urlopen(req, timeout=5))
except Exception as e:
    print(f"  EXC: {e}")
    sys.exit(0)
last = r[-1] if isinstance(r, list) else r
result = last.get("result") if isinstance(last, dict) else None
status = last.get("status") if isinstance(last, dict) else "?"
if status == "OK" and isinstance(result, list):
    print(f"  OK hits={len(result)}")
else:
    print(f"  {status}: {str(result)[:80]}")
PYEOF
}

echo "Q1 simple (works):"
test_sql Q1 'SELECT path FROM directory_entry WHERE string::lowercase(basename) CONTAINS "toml" LIMIT 3;'

echo
echo "Q2 full columns:"
test_sql Q2 'SELECT path, parent, basename, kind, size, mtime, ext, summary, root_label FROM directory_entry WHERE string::lowercase(basename) CONTAINS "toml" LIMIT 3;'

echo
echo "Q3 simple WITH OR:"
test_sql Q3 'SELECT path FROM directory_entry WHERE string::lowercase(basename) CONTAINS "toml" OR string::lowercase(path) CONTAINS "toml" LIMIT 3;'

echo
echo "Q4 simple WITH parens OR:"
test_sql Q4 'SELECT path FROM directory_entry WHERE (string::lowercase(basename) CONTAINS "toml" OR string::lowercase(path) CONTAINS "toml") LIMIT 3;'

echo
echo "Q5 full WITH parens OR (shim shape):"
test_sql Q5 'SELECT path, parent, basename, kind, size, mtime, ext, summary, root_label FROM directory_entry WHERE (string::lowercase(basename) CONTAINS "toml" OR string::lowercase(path) CONTAINS "toml") LIMIT 9;'

echo
echo "Q6 mtime out -- does mtime field break the SELECT?"
test_sql Q6 'SELECT path, parent, basename, kind, size, ext, summary, root_label FROM directory_entry WHERE (string::lowercase(basename) CONTAINS "toml" OR string::lowercase(path) CONTAINS "toml") LIMIT 9;'

#!/bin/bash
# AI-hint: A diagnostic script to debug discrepancies between raw HTTP requests to the /sql endpoint and the local mios-directory-lookup shim by executing the same SQL query through both paths side-by-side.
# AI-related: /usr/libexec/mios/mios-directory-lookup, mios-directory-lookup, localhost:8000
# Side-by-side: run the IDENTICAL SQL through (a) an inline python
# urllib request and (b) the shim's _sql() to find why they return
# different results despite identical headers + body.
set -euo pipefail

echo "── (a) inline urllib with shim's SQL shape ──"
python3 - <<'PYEOF'
import json, urllib.request
sql = ('SELECT path, parent, basename, kind, size, mtime, ext, '
       'summary, root_label FROM directory_entry WHERE '
       '(string::lowercase(basename) CONTAINS "toml" '
       'OR string::lowercase(path) CONTAINS "toml") LIMIT 9;')
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
r = json.load(urllib.request.urlopen(req, timeout=4))
last = r[-1] if isinstance(r, list) else r
result = last.get("result") if isinstance(last, dict) else None
if isinstance(result, list):
    print(f"  hits: {len(result)}")
    for row in result[:3]:
        print(f"    {row.get('path','?')}")
else:
    print(f"  status: {last}")
PYEOF

echo
echo "── (b) shim's _sql() invocation ──"
python3 - <<'PYEOF'
import sys
sys.path.insert(0, "/usr/libexec/mios")
# The shim isn't a module; reload via importlib + exec.
import importlib.util
spec = importlib.util.spec_from_file_location(
    "mios_directory_lookup",
    "/usr/libexec/mios/mios-directory-lookup")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
sql = ('SELECT path, parent, basename, kind, size, mtime, ext, '
       'summary, root_label FROM directory_entry WHERE '
       '(string::lowercase(basename) CONTAINS "toml" '
       'OR string::lowercase(path) CONTAINS "toml") LIMIT 9;')
r = mod._sql(sql)
last = r[-1] if isinstance(r, list) else r
result = last.get("result") if isinstance(last, dict) else None
if isinstance(result, list):
    print(f"  hits: {len(result)}")
    for row in result[:3]:
        print(f"    {row.get('path','?')}")
else:
    print(f"  status: {last}")
PYEOF

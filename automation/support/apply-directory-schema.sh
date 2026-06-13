#!/bin/bash
# AI-hint: Executes a SQL migration to define the directory_entry table and its associated indexes in the mios agent database via the local SQL API endpoint.
# AI-related: localhost:8000
# Apply ONLY the directory_entry table definition (the broader
# schema already exists; we just need to land the new table).
set -euo pipefail

SCHEMA='
USE NS mios DB agent;
DEFINE TABLE directory_entry SCHEMAFULL PERMISSIONS NONE;
DEFINE FIELD path             ON directory_entry TYPE string;
DEFINE FIELD parent           ON directory_entry TYPE string;
DEFINE FIELD basename         ON directory_entry TYPE string;
DEFINE FIELD kind             ON directory_entry TYPE string;
DEFINE FIELD size             ON directory_entry TYPE int DEFAULT 0;
DEFINE FIELD mtime            ON directory_entry TYPE datetime;
DEFINE FIELD ext              ON directory_entry TYPE option<string>;
DEFINE FIELD summary          ON directory_entry TYPE option<string>;
DEFINE FIELD root_label       ON directory_entry TYPE string;
DEFINE FIELD indexed_at       ON directory_entry TYPE datetime;
DEFINE INDEX dir_entry_path   ON directory_entry COLUMNS path UNIQUE;
DEFINE INDEX dir_entry_parent ON directory_entry COLUMNS parent;
DEFINE INDEX dir_entry_base   ON directory_entry COLUMNS basename;
DEFINE INDEX dir_entry_root   ON directory_entry COLUMNS root_label;
DEFINE INDEX dir_entry_ext    ON directory_entry COLUMNS ext;
'

echo "── apply schema ──"
python3 - <<PYEOF
import json, urllib.request
sql = '''$SCHEMA'''
req = urllib.request.Request(
    "http://localhost:8000/sql",
    data=sql.encode(),
    headers={
        "Authorization": "Basic cm9vdDpyb290",
        "Accept": "application/json",
        "Content-Type": "text/plain",
    },
    method="POST")
r = json.load(urllib.request.urlopen(req, timeout=10))
ok = err = 0
for s in r:
    if not isinstance(s, dict):
        continue
    if s.get("status") == "OK":
        ok += 1
    else:
        err += 1
        msg = str(s.get("result",""))[:80]
        # "already exists" is expected on re-run
        if "already exists" not in msg.lower():
            print(f"  ERR: {msg}")
print(f"  applied: {ok} OK, {err} ERR")
PYEOF

echo
echo "── verify directory_entry exists ──"
python3 - <<'PYEOF'
import json, urllib.request
req = urllib.request.Request(
    "http://localhost:8000/sql",
    data="USE NS mios DB agent; INFO FOR DB;".encode(),
    headers={
        "Authorization": "Basic cm9vdDpyb290",
        "Accept": "application/json",
        "Content-Type": "text/plain",
    },
    method="POST")
r = json.load(urllib.request.urlopen(req, timeout=4))
info = r[-1] if isinstance(r, list) else {}
result = info.get("result") if isinstance(info, dict) else None
if isinstance(result, dict):
    tables = result.get("tables") or {}
elif isinstance(result, str):
    # SurrealDB 3.x returns INFO as a string in some versions
    tables = {"directory_entry": "?"} if "directory_entry" in result else {}
else:
    tables = {}
print(f"  directory_entry table: {'YES' if 'directory_entry' in tables else 'NO'}")
print(f"  total tables: {len(tables)}")
PYEOF

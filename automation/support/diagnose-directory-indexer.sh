#!/bin/bash
set -u

echo "── did directory_entry table land? ──"
python3 - <<'PYEOF'
import json, urllib.request
req = urllib.request.Request(
    'http://localhost:8000/sql',
    data='INFO FOR DB;'.encode(),
    headers={
        'Authorization': 'Basic cm9vdDpyb290',
        'NS': 'mios', 'DB': 'agent',
        'Content-Type': 'text/plain',
        'Accept': 'application/json',
    },
    method='POST')
r = json.load(urllib.request.urlopen(req, timeout=4))
tables = ((r[-1] or {}).get('result') or {}).get('tables') or {}
print('  directory_entry:', 'YES' if 'directory_entry' in tables else 'NO')
print('  total tables:', len(tables))
PYEOF

echo
echo "── mios-daemon journal (index lines) ──"
journalctl -u mios-daemon.service --since '5 min ago' --no-pager 2>&1 \
    | grep -iE 'index_loop|index:|directory|_read_daemon_index' \
    | tail -10

echo
echo "── direct row count probe ──"
python3 - <<'PYEOF'
import json, urllib.request
req = urllib.request.Request(
    'http://localhost:8000/sql',
    data='SELECT count() FROM directory_entry GROUP ALL;'.encode(),
    headers={
        'Authorization': 'Basic cm9vdDpyb290',
        'NS': 'mios', 'DB': 'agent',
        'Content-Type': 'text/plain',
        'Accept': 'application/json',
    },
    method='POST')
r = json.load(urllib.request.urlopen(req, timeout=4))
rows = (r[-1] or {}).get('result') or []
print(f'  total entries: {rows[0].get("count") if rows else 0}')
PYEOF

echo
echo "── lookup test ──"
python3 - <<'PYEOF'
import json, urllib.request
sql = ('SELECT path, basename FROM directory_entry '
       'WHERE string::lowercase(basename) CONTAINS "toml" LIMIT 3;')
req = urllib.request.Request(
    'http://localhost:8000/sql',
    data=sql.encode(),
    headers={
        'Authorization': 'Basic cm9vdDpyb290',
        'NS': 'mios', 'DB': 'agent',
        'Content-Type': 'text/plain',
        'Accept': 'application/json',
    },
    method='POST')
r = json.load(urllib.request.urlopen(req, timeout=4))
rows = (r[-1] or {}).get('result') or []
print(f'  hits: {len(rows)}')
for row in rows:
    print(f'    {row.get("path","?")}')
PYEOF

#!/bin/bash
# AI-hint: Automates the deployment of the directory indexer by copying binaries/configs, applying the SurrealDB schema, reinstalling OWUI tools, and restarting the mios-daemon service with a smoke-test verification.
# AI-related: /usr/share/mios/surrealdb/schema-init.surql, /usr/share/mios/mios.toml, /usr/libexec/mios/mios-daemon, /usr/libexec/mios/mios-directory-lookup, /usr/share/mios/owui/tools/mios_verbs.py, /usr/libexec/mios/mios-owui-install-tools, mios-daemon, mios-directory-lookup, mios-owui-install-tools, mios-daemon.service
# Deploy + apply schema + restart daemon + smoke-test the directory
# indexer.
set -euo pipefail

echo "── deploy files ──"
cp /mnt/c/MiOS/usr/share/mios/surrealdb/schema-init.surql \
   /usr/share/mios/surrealdb/schema-init.surql
cp /mnt/c/MiOS/usr/share/mios/mios.toml \
   /usr/share/mios/mios.toml
cp /mnt/c/MiOS/usr/libexec/mios/mios-daemon \
   /usr/libexec/mios/mios-daemon
chmod +x /usr/libexec/mios/mios-daemon
cp /mnt/c/MiOS/usr/libexec/mios/mios-directory-lookup \
   /usr/libexec/mios/mios-directory-lookup
chmod +x /usr/libexec/mios/mios-directory-lookup
cp /mnt/c/MiOS/usr/share/mios/owui/tools/mios_verbs.py \
   /usr/share/mios/owui/tools/mios_verbs.py

echo
echo "── syntax check ──"
python3 -m py_compile /usr/libexec/mios/mios-daemon \
    /usr/libexec/mios/mios-directory-lookup
echo "  OK"

echo
echo "── apply schema (add directory_entry table) ──"
curl -s -X POST \
    -H 'Authorization: Basic cm9vdDpyb290' \
    -H 'NS: mios' -H 'DB: agent' \
    -H 'Content-Type: text/plain' \
    --data-binary @/usr/share/mios/surrealdb/schema-init.surql \
    http://localhost:8000/sql \
    | python3 -c "
import sys, json
d = json.load(sys.stdin)
errs = [r for r in d if isinstance(r, dict) and r.get('status') == 'ERR']
print(f'  {len(d)} statements, {len(errs)} errors')
for e in errs[:5]:
    print('  ERR:', str(e.get('result',''))[:100])
"

echo
echo "── re-install OWUI tools (picks up directory_lookup) ──"
/usr/libexec/mios/mios-owui-install-tools 2>&1 | tail -3

echo
echo "── restart mios-daemon ──"
systemctl restart mios-daemon.service
sleep 3
systemctl is-active mios-daemon.service

echo
echo "── wait for index_loop's first tick (~60s boot delay) ──"
for i in $(seq 1 24); do
    sleep 5
    n=$(python3 -c "
import json, urllib.request
req = urllib.request.Request(
    'http://localhost:8000/sql',
    data='SELECT count() FROM directory_entry GROUP ALL;'.encode(),
    headers={'Authorization':'Basic cm9vdDpyb290','NS':'mios','DB':'agent','Content-Type':'text/plain','Accept':'application/json'},
    method='POST')
try:
    r = json.load(urllib.request.urlopen(req, timeout=4))
    rows = (r[-1] or {}).get('result') or []
    print(rows[0].get('count') if rows else 0)
except Exception:
    print(0)
" 2>/dev/null)
    if [ "$n" -gt "0" ] 2>/dev/null; then
        echo "  directory_entry count: $n  (after $((i*5))s)"
        break
    fi
    [ "$i" = "24" ] && echo "  TIMEOUT: no entries after 120s -- check 'journalctl -u mios-daemon | grep index'"
done

echo
echo "── smoke-test lookup ──"
/usr/libexec/mios/mios-directory-lookup mios.toml --kind file --limit 3 2>&1
echo
/usr/libexec/mios/mios-directory-lookup epiphany --limit 3 2>&1

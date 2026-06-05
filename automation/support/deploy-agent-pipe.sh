#!/bin/bash
# Deploy + import-check + restart agent-pipe after edits.
# Lives as a bash file path to avoid the wsl.exe->pwsh->bash quoting hellscape.
#
# Deploys the FULL runtime: server.py + every sibling module it imports +
# mios.toml. CR-strips each file (the Windows checkout carries CRLF). SAFETY
# GATE: an IMPORT CHECK with the service's own venv runs BEFORE the restart -- if
# the new server.py fails to import (missing sibling / bad API / syntax) we
# RESTORE the backups and SKIP the restart, so a bad deploy can't crash the
# running service. Backups land at <name>.bak-<epoch>.
set -uo pipefail

SRC=/mnt/c/MiOS
AP=/usr/lib/mios/agent-pipe
VENV=/usr/lib/mios/hermes-agent/.venv/bin/python3
TS=$(date +%s)
# server.py LAST so its siblings are already in place for the import check.
MODS="mios_sched.py mios_evict.py mios_hitl.py mios_aci.py mios_pg.py mios_codemode.py mios_kvfork.py mios_stress.py server.py"

echo "[deploy] $SRC -> $AP  (backup tag $TS)"
for f in $MODS; do
    s="$SRC/usr/lib/mios/agent-pipe/$f"
    [ -f "$s" ] || { echo "[deploy] MISSING source: $s -- ABORT"; exit 1; }
    [ -f "$AP/$f" ] && sudo cp -a "$AP/$f" "$AP/$f.bak-$TS"
    tr -d '\r' < "$s" | sudo tee "$AP/$f" >/dev/null
    echo "[deploy]   + $f"
done
[ -f /usr/share/mios/mios.toml ] && sudo cp -a /usr/share/mios/mios.toml "/usr/share/mios/mios.toml.bak-$TS"
tr -d '\r' < "$SRC/usr/share/mios/mios.toml" | sudo tee /usr/share/mios/mios.toml >/dev/null
echo "[deploy]   + mios.toml"

echo "[deploy] import check (service venv)..."
if "$VENV" -c "import sys; sys.path.insert(0,'$AP'); import server; print('IMPORT_OK')"; then
    echo "[deploy] import OK -- restarting mios-agent-pipe.service"
    sudo systemctl restart mios-agent-pipe.service
    sleep 4
    echo "[deploy] state=$(systemctl is-active mios-agent-pipe.service) NRestarts=$(systemctl show -p NRestarts --value mios-agent-pipe.service)"
else
    echo "[deploy] IMPORT FAILED -- restoring backups, NOT restarting"
    for f in $MODS; do [ -f "$AP/$f.bak-$TS" ] && sudo cp -a "$AP/$f.bak-$TS" "$AP/$f"; done
    [ -f "/usr/share/mios/mios.toml.bak-$TS" ] && sudo cp -a "/usr/share/mios/mios.toml.bak-$TS" /usr/share/mios/mios.toml
    exit 1
fi

# verify the NEW code is live (the WS-1/WS-3 observability blocks)
"$VENV" - <<'PY'
import json, urllib.request
try:
    with urllib.request.urlopen("http://127.0.0.1:8640/v1/scheduler", timeout=6) as r:
        d = json.load(r)
    print("[deploy] /v1/scheduler priority_gate:",
          "PRESENT" if "priority_gate" in d else "ABSENT (old code still loaded?)")
    print("[deploy]   knowledge_eviction:",
          "PRESENT" if "knowledge_eviction" in d else "ABSENT")
    pg = d.get("priority_gate", {})
    if pg:
        print("[deploy]   priority_gate.enabled:", pg.get("enabled"))
except Exception as e:
    print("[deploy] /v1/scheduler probe failed:", e)
PY

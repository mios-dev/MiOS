#!/bin/bash
# AI-hint: Automates the deployment of the agent-pipe service by copying source files, stripping CRLF, performing a pre-restart import check in the service venv, and rolling back to backups if the import fails.
# AI-related: /usr/lib/mios/agent-pipe, /usr/lib/mios/agents/.venv/bin/python3, /usr/lib/mios/agent-pipe/, /usr/share/mios/mios.toml, /usr/share/mios/mios.toml.bak-, mios-agent-pipe, mios-agent-pipe.service
set -euo pipefail

SRC=/mnt/c/MiOS
AP=/usr/lib/mios/agent-pipe
VENV=/usr/lib/mios/agents/.venv/bin/python3
TS=$(date +%s)
MODS="mios_sched.py mios_evict.py mios_hitl.py mios_aci.py mios_pg.py mios_codemode.py mios_kvfork.py mios_stress.py server.py"

echo "[deploy] $SRC -> $AP"
for f in $MODS; do
    s="$SRC/usr/lib/mios/agent-pipe/$f"
    [ -f "$s" ] || { echo "[deploy] MISSING source: $s"; exit 1; }
    [ -f "$AP/$f" ] && sudo cp -a "$AP/$f" "$AP/$f.bak-$TS"
    tr -d '\r' < "$s" | sudo tee "$AP/$f" >/dev/null
    echo "[deploy]   + $f"
done
[ -f /usr/share/mios/mios.toml ] && sudo cp -a /usr/share/mios/mios.toml "/usr/share/mios/mios.toml.bak-$TS"
tr -d '\r' < "$SRC/usr/share/mios/mios.toml" | sudo tee /usr/share/mios/mios.toml >/dev/null
echo "[deploy]   + mios.toml"

echo "[deploy] import check"
if "$VENV" -c "import sys; sys.path.insert(0,'$AP'); import server; print('IMPORT_OK')"; then
    echo "[deploy] import OK"
    sudo systemctl restart mios-agent-pipe.service
    sleep 4
    echo "[deploy] state=$ NRestarts=$"
else
    echo "[deploy] IMPORT FAILED"
    for f in $MODS; do [ -f "$AP/$f.bak-$TS" ] && sudo cp -a "$AP/$f.bak-$TS" "$AP/$f"; done
    [ -f "/usr/share/mios/mios.toml.bak-$TS" ] && sudo cp -a "/usr/share/mios/mios.toml.bak-$TS" /usr/share/mios/mios.toml
    exit 1
fi

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

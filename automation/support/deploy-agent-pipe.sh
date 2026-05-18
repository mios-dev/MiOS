#!/bin/bash
# Deploy + syntax-check + restart agent-pipe after a server.py edit.
# Avoids the wsl.exe-through-pwsh-through-bash quoting hellscape by
# living as a bash file path.
set -eu

SRC=/mnt/c/MiOS/usr/lib/mios/agent-pipe/server.py
DST=/usr/lib/mios/agent-pipe/server.py

cp "$SRC" "$DST"
python3 -m py_compile "$DST"
echo "[deploy] syntax OK"

systemctl restart mios-agent-pipe.service
sleep 2

state=$(systemctl is-active mios-agent-pipe.service)
echo "[deploy] mios-agent-pipe: $state"

python3 - <<'PY'
import json, urllib.request
try:
    with urllib.request.urlopen("http://127.0.0.1:8640/health", timeout=4) as r:
        d = json.load(r)
    print(f"[deploy] /health status={d.get('status')} "
          f"backend={d.get('backend_model')} "
          f"refine={d.get('router',{}).get('model')}")
except Exception as e:
    print(f"[deploy] /health probe failed: {e}")
PY

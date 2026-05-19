#!/bin/bash
set -u

echo "── deploy units + script ──"
cp /mnt/c/MiOS/usr/lib/systemd/system/mios-suggestion-refresh.service \
   /usr/lib/systemd/system/mios-suggestion-refresh.service
cp /mnt/c/MiOS/usr/lib/systemd/system/mios-suggestion-refresh.timer \
   /usr/lib/systemd/system/mios-suggestion-refresh.timer
cp /mnt/c/MiOS/usr/libexec/mios/mios-hermes-firstboot \
   /usr/libexec/mios/mios-hermes-firstboot
chmod +x /usr/libexec/mios/mios-hermes-firstboot
systemctl daemon-reload

echo
echo "── enable timer ──"
systemctl enable --now mios-suggestion-refresh.timer
systemctl is-active mios-suggestion-refresh.timer

echo
echo "── one live refresh now ──"
/usr/libexec/mios/mios-suggestion-refresh | tail -3

echo
echo "── inspect what landed in webui.db ──"
python3 <<'PYEOF'
import json
import sqlite3

c = sqlite3.connect("/var/lib/mios/open-webui/webui.db")
row = c.execute("SELECT data FROM config WHERE id=1").fetchone()
if not row:
    print("  no config row")
    raise SystemExit(0)
d = json.loads(row[0])
chips = (d.get("ui") or {}).get("prompt_suggestions") or []
print(f"  prompt_suggestions count: {len(chips)}")
for i, c in enumerate(chips, 1):
    txt = c.get("content") or ""
    print(f"    {i}. {txt[:80]}")
PYEOF

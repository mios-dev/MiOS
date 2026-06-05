#!/bin/bash
# Show the resolved launch chain for a query without actually
# launching anything. Mirrors mios-launch's _DESC_CHAIN python.
set -euo pipefail
Q="${1:-files}"
echo "── launch chain for query: '$Q' ──"
python3 - "$Q" <<'PYEOF'
import json, subprocess, sys
q = sys.argv[1].lower().strip()
PRIORITY = {
    "linux-flatpak": 0, "linux-rpm-gui": 1, "linux-cli": 2,
    "windows-app": 3, "windows-gui": 4,
}
raw = subprocess.run(["mios-apps", "--json"],
                     capture_output=True, text=True,
                     timeout=10).stdout
cands = []
for line in raw.splitlines():
    if not line.strip(): continue
    try:
        e = json.loads(line)
    except Exception: continue
    name = (e.get("name") or "").lower()
    desc = (e.get("description") or "").lower()
    cat = e.get("category") or ""
    launch = e.get("launch") or ""
    if not launch: continue
    if name == q:
        cands.append((PRIORITY.get(cat, 9), 0, cat, launch))
    elif q in name:
        cands.append((PRIORITY.get(cat, 9), 1, cat, launch))
    elif q in desc:
        cands.append((PRIORITY.get(cat, 9), 2, cat, launch))
cands.sort(key=lambda t: (t[0], t[1]))
seen = set()
out = []
for _, mq, cat, launch in cands:
    if launch in seen: continue
    seen.add(launch)
    out.append((cat, mq, launch))
print(f"  candidates: {len(out)}")
for i, (cat, mq, launch) in enumerate(out, 1):
    src = ["name=", "name~", "desc="][mq] if mq < 3 else "?"
    print(f"  {i}. [{cat:14s} {src}] {launch[:80]}")
PYEOF

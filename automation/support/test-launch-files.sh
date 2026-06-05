#!/bin/bash
# Smoke-test mios-launch's new alias + description-fallback paths
# against the operator's failing "open files" trace.
set -euo pipefail

echo "── alias resolution: 'files' -> nautilus ──"
# We don't actually want to LAUNCH; just dry-run the resolver.
# Capture the alias log line + the next resolution step's stderr.
# Use --help bypass: pass an arg that wouldn't match anything else
# so we can read the alias-then-no-resolution log path.
bash -c 'mios-launch files --dry-run 2>&1; true' \
    | grep -E "alias|description-fallback|no resolution" \
    | head -3

echo
echo "── description-fallback verification (no launch, just probe) ──"
python3 <<'PYEOF'
import json, subprocess
q = "files"
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
    if name == q.lower():
        cands.append((PRIORITY.get(cat, 9), 0, e))
    elif q.lower() in name:
        cands.append((PRIORITY.get(cat, 9), 1, e))
    elif q.lower() in desc:
        cands.append((PRIORITY.get(cat, 9), 2, e))
cands.sort(key=lambda t: (t[0], t[1]))
print(f"  Found {len(cands)} candidates for query 'files'.")
for i, (pr, mq, e) in enumerate(cands[:6], 1):
    src = ["name=", "name~", "desc="][mq] if mq < 3 else "?"
    print(f"  {i}. [{src} prio={pr}] {e.get('category')} :: "
          f"{e.get('description','')[:60]} -> {e.get('launch','')[:50]}")
print()
if cands:
    winner = cands[0][2]
    print(f"  WINNER: {winner.get('launch')}")
PYEOF

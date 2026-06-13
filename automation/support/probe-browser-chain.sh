#!/bin/bash
# AI-hint: Parses mios.toml configurations to output the ordered list of browser application IDs used by mios-open-url for fallback logic when a primary browser is unavailable.
# AI-related: /etc/mios/mios.toml, /usr/share/mios/mios.toml, mios-open-url
# Print the resolved browser fallback chain that mios-open-url
# would use. Mirrors the inline _resolve_browser_chain function.
set -euo pipefail
python3 - <<'PYEOF'
import tomllib
chain = []
seen = set()
for path in ("/etc/mios/mios.toml", "/usr/share/mios/mios.toml"):
    try:
        with open(path, "rb") as f:
            d = tomllib.load(f)
    except Exception:
        continue
    apps = d.get("desktop", {}).get("apps", [])
    if isinstance(apps, list):
        for entry in apps:
            if not isinstance(entry, dict): continue
            if entry.get("role") != "browser": continue
            aid = entry.get("id")
            if not aid or aid in seen: continue
            if entry.get("default"):
                chain.append(("default", aid))
                seen.add(aid)
        for entry in apps:
            if not isinstance(entry, dict): continue
            if entry.get("role") != "browser": continue
            aid = entry.get("id")
            if not aid or aid in seen: continue
            chain.append(("fallback", aid))
            seen.add(aid)
    if chain:
        break

print("Resolved browser fallback chain:")
for i, (tier, aid) in enumerate(chain, 1):
    print(f"  {i}. [{tier:8s}] {aid}")
PYEOF

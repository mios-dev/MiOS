# AI-hint: !/usr/bin/env python3 Law-11 extension gate: fails any NEW credential literal baked into a world-readable systemd unit or Quadlet (Environment=...PASSWORD/S...
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_check_credential_literals_py.md
"""Fail if a unit gains a new baked-in credential. Law 11 scans only .env files."""
import os
import re
import sys
import tomllib

ROOT = os.environ.get("MIOS_ROOT", ".")
SSOT = os.path.join(ROOT, "usr/share/mios/mios.toml")
UNIT_DIRS = ("usr/share/containers/systemd", "usr/lib/systemd/system")
CRED_KEY = re.compile(r"^Environment=([A-Z0-9_]*(?:PASSWORD|SECRET|API_?KEY|TOKEN)[A-Z0-9_]*)=(.*)$")
# Counters and feature flags are not credentials.
NOT_CRED = re.compile(r"(MAX_TOKENS|_TOKENS$|^ENABLE_|_ENABLED$|NUM_|_LIMIT$)")


def literal_credentials(root: str) -> list:
    found = []
    for d in UNIT_DIRS:
        full = os.path.join(root, d)
        for dirpath, _, names in os.walk(full):
            for n in sorted(names):
                path = os.path.join(dirpath, n)
                rel = os.path.relpath(path, root)
                try:
                    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
                except OSError:
                    continue
                for line in lines:
                    m = CRED_KEY.match(line.strip())
                    if not m:
                        continue
                    key, val = m.group(1), m.group(2).strip()
                    if NOT_CRED.search(key):
                        continue
                    if not val or val.startswith("${") or val.startswith("%"):
                        continue        # indirected through an env/specifier: fine
                    if val.lower() in ("true", "false") or val.isdigit():
                        continue
                    found.append(f"{rel}:{key}")
    return sorted(found)


def main() -> int:
    cfg = (tomllib.load(open(SSOT, "rb")).get("security", {}) or {}).get("credential_literals", {}) or {}
    allowed = set(cfg.get("grandfathered", []))
    found = set(literal_credentials(ROOT))
    bad = []
    for f in sorted(found - allowed):
        bad.append(f"NEW credential literal baked into a world-readable unit: {f}")
    for f in sorted(allowed - found):
        bad.append(f"grandfathered entry no longer present (shrink the list): {f}")
    if bad:
        print("\n".join(bad), file=sys.stderr)
        return 1
    print(f"no new unit credential literals ({len(found)} grandfathered, shrink-only)")
    return 0


sys.exit(main())

#!/usr/bin/env bash
# AI-hint: systemd capability drop-in fan-out script (WS-BLADE).
# Reads mios.toml [blade.requires] and maps cap drop-ins to service directories.
# AI-related: usr/share/mios/dropins/blade-*.conf, usr/share/mios/mios.toml, /usr/lib/systemd/system/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Call python interpreter to perform the parsing and file copying
python3 - <<'EOF' "$ROOT"
import os
import sys
import shutil

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

root = sys.argv[1]
toml_path = os.path.join(root, "usr/share/mios/mios.toml")
dropins_dir = os.path.join(root, "usr/share/mios/dropins")
systemd_dir = os.path.join(root, "usr/lib/systemd/system")

if not os.path.isfile(toml_path):
    print(f"WARN: mios.toml not found at {toml_path}, skipping fanout.")
    sys.exit(0)

with open(toml_path, "rb") as f:
    d = tomllib.load(f)

blade = d.get("blade") or {}
requires = blade.get("requires") or {}

for service, caps in requires.items():
    if isinstance(caps, str):
        caps = [caps]
    
    # Ensure service ends with .service or another unit extension
    svc_name = service if service.endswith((".service", ".socket", ".timer", ".path", ".target")) else f"{service}.service"
    
    for cap in caps:
        cap = str(cap).strip()
        if not cap:
            continue
            
        src = os.path.join(dropins_dir, f"blade-{cap}.conf")
        if not os.path.isfile(src):
            print(f"ERROR: capability drop-in not found at {src} for service {svc_name}")
            sys.exit(1)
            
        dst_dir = os.path.join(systemd_dir, f"{svc_name}.d")
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, f"50-blade-{cap}.conf")
        shutil.copy2(src, dst)
        print(f"[dropin-fanout] Mapped {src} -> {dst}")
EOF

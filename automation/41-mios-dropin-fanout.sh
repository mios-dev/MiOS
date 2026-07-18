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

def is_service_enabled(d, service_name):
    svc = service_name
    if svc.endswith(".service"):
        svc = svc[:-8]
    containers = d.get("containers") or {}
    if svc in containers:
        cfg = containers[svc]
        if isinstance(cfg, dict) and cfg.get("enable") is False:
            return False
    services = d.get("services") or {}
    if svc in services:
        cfg = services[svc]
        if isinstance(cfg, dict) and cfg.get("enable") is False:
            return False
    short_svc = svc[5:] if svc.startswith("mios-") else svc
    if short_svc in containers:
        cfg = containers[short_svc]
        if isinstance(cfg, dict) and cfg.get("enable") is False:
            return False
    if short_svc in services:
        cfg = services[short_svc]
        if isinstance(cfg, dict) and cfg.get("enable") is False:
            return False
    return True

for service, caps in requires.items():
    if not is_service_enabled(d, service):
        print(f"[dropin-fanout] Skipping disabled service {service}")
        continue
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

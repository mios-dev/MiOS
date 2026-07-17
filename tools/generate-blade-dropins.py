#!/usr/bin/env python3
# AI-hint: Generate systemd capability drop-in files from the mios.toml [blade.requires] SSOT.
# AI-related: usr/share/mios/dropins/blade-*.conf, usr/share/mios/mios.toml, automation/41-mios-dropin-fanout.sh, /etc/mios/blade.d/
import os
import sys

try:
    import tomllib
except ModuleNotFoundError:  # py<3.11
    import tomli as tomllib  # type: ignore

ROOT = os.environ.get("MIOS_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOML = os.environ.get("MIOS_TOML") or os.path.join(ROOT, "usr/share/mios/mios.toml")
DROPINS_DIR = os.path.join(ROOT, "usr/share/mios/dropins")

def build_dropin_content(capability: str) -> str:
    return f"""# AI-hint: GENERATED systemd capability drop-in for MiOS (WS-BLADE). DO NOT EDIT -- regenerate via tools/generate-blade-dropins.py.
# Gates this unit under systemd using the /etc/mios/blade.d/{capability} marker.
[Unit]
ConditionPathExists=/etc/mios/blade.d/{capability}
"""

def main() -> int:
    try:
        with open(TOML, "rb") as f:
            d = tomllib.load(f)
    except Exception as e:
        print(f"[generate-blade-dropins] ERROR: Failed to load {TOML}: {e}", file=sys.stderr)
        return 1

    blade = d.get("blade") or {}
    requires = blade.get("requires") or {}

    # Extract all unique capabilities
    unique_caps = set()
    for caps in requires.values():
        if isinstance(caps, list):
            for cap in caps:
                unique_caps.add(str(cap).strip())
        elif isinstance(caps, str):
            unique_caps.add(caps.strip())

    os.makedirs(DROPINS_DIR, exist_ok=True)

    # Generate drop-in files
    for cap in sorted(unique_caps):
        if not cap:
            continue
        out_path = os.path.join(DROPINS_DIR, f"blade-{cap}.conf")
        content = build_dropin_content(cap)
        with open(out_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print(f"[generate-blade-dropins] Wrote {out_path}")

    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
tools/generate-bib-configs.py (AGY-157)
Projects [deploy.artifacts] filesystem sizing from mios.toml SSOT into config/artifacts/*.toml.
"""

import os
import sys
import re

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

def main():
    root = os.environ.get("MIOS_DRIFT_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ssot_path = os.path.join(root, "usr/share/mios/mios.toml")
    bib_path = os.path.join(root, "config/artifacts/bib.toml")
    iso_path = os.path.join(root, "config/artifacts/iso.toml")

    if not os.path.isfile(ssot_path):
        sys.stderr.write(f"ERROR: {ssot_path} not found\n")
        sys.exit(1)

    raw_size = "80 GiB"
    iso_size = "150 GiB"

    if tomllib:
        with open(ssot_path, "rb") as f:
            data = tomllib.load(f)
        deploy = data.get("deploy", {}).get("artifacts", {})
        raw_size = deploy.get("raw", {}).get("size", raw_size)
        iso_size = deploy.get("iso", {}).get("minsize", iso_size)
    else:
        with open(ssot_path, "r", encoding="utf-8") as f:
            txt = f.read()
        m1 = re.search(r'\[deploy\.artifacts\.raw\]\s*size\s*=\s*"([^"]+)"', txt)
        if m1:
            raw_size = m1.group(1)
        m2 = re.search(r'\[deploy\.artifacts\.iso\]\s*minsize\s*=\s*"([^"]+)"', txt)
        if m2:
            iso_size = m2.group(1)

    bib_ok = True
    if os.path.isfile(bib_path):
        with open(bib_path, "r", encoding="utf-8") as f:
            bib_txt = f.read()
        bib_match = re.search(r'minsize\s*=\s*"([^"]+)"', bib_txt)
        if not bib_match or bib_match.group(1) != raw_size:
            bib_ok = False

    iso_ok = True
    if os.path.isfile(iso_path):
        with open(iso_path, "r", encoding="utf-8") as f:
            iso_txt = f.read()
        iso_match = re.search(r'minsize\s*=\s*"([^"]+)"', iso_txt)
        if not iso_match or iso_match.group(1) != iso_size:
            iso_ok = False

    check_mode = "--check" in sys.argv
    if check_mode:
        if not bib_ok or not iso_ok:
            sys.stderr.write(f"ERROR: BIB artifact configs out of sync with mios.toml [deploy.artifacts] (raw={raw_size}, iso={iso_size}). Run python3 tools/generate-bib-configs.py\n")
            sys.exit(1)
        print("PASS: BIB artifact configs in sync with mios.toml SSOT.")
        sys.exit(0)

    if os.path.isfile(bib_path):
        with open(bib_path, "r", encoding="utf-8") as f:
            bib_txt = f.read()
        bib_new = re.sub(r'minsize\s*=\s*"[^"]+"', f'minsize = "{raw_size}"', bib_txt)
        with open(bib_path, "w", encoding="utf-8") as f:
            f.write(bib_new)

    if os.path.isfile(iso_path):
        with open(iso_path, "r", encoding="utf-8") as f:
            iso_txt = f.read()
        iso_new = re.sub(r'minsize\s*=\s*"[^"]+"', f'minsize = "{iso_size}"', iso_txt)
        with open(iso_path, "w", encoding="utf-8") as f:
            f.write(iso_new)

    print(f"Updated BIB configs with SSOT sizes: raw={raw_size}, iso={iso_size}.")

if __name__ == "__main__":
    main()

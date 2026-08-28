#!/usr/bin/env python3
# AI-hint: MiOS system and orchestration module providing generate-bib-configs capabilities.
# AI-functions: main, _rendered

"""
tools/generate-bib-configs.py
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

    def _rendered(path, size):
        r"""Return (current, what-write-mode-would-produce) for path.

        check-mode used to compare only the VALUE, via a tolerant
        minsize\s*=\s*"..." regex, while write-mode ALSO normalised the
        spacing. So a file carrying aligned padding passed --check and was
        still rewritten by the generator: the gate reported in-sync on a file
        the generator would change. A check that does not compare what the
        writer produces cannot detect the drift the writer creates, so both
        modes now derive from this one rendering.
        """
        if not os.path.isfile(path):
            return None, None
        with open(path, "r", encoding="utf-8", newline="") as f:
            current = f.read()
        return current, re.sub(r'minsize\s*=\s*"[^"]+"',
                               'minsize = "%s"' % size, current)

    bib_cur, bib_new = _rendered(bib_path, raw_size)
    iso_cur, iso_new = _rendered(iso_path, iso_size)

    if "--check" in sys.argv:
        stale = [rel for rel, cur, new in (
                     ("config/artifacts/bib.toml", bib_cur, bib_new),
                     ("config/artifacts/iso.toml", iso_cur, iso_new))
                 if cur is not None and cur != new]
        if stale:
            sys.stderr.write(
                "ERROR: BIB artifact configs out of sync with mios.toml "
                "[deploy.artifacts] (raw=%s, iso=%s): %s\n"
                % (raw_size, iso_size, ", ".join(stale)))
            sys.exit(1)
        print("PASS: BIB artifact configs in sync with mios.toml SSOT.")
        sys.exit(0)

    for path, new in ((bib_path, bib_new), (iso_path, iso_new)):
        if new is not None:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(new)

    print("Updated BIB configs with SSOT sizes: raw=%s, iso=%s."
          % (raw_size, iso_size))

if __name__ == "__main__":
    main()

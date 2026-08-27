#!/usr/bin/env python3
# AI-hint: Drift gate for the first-boot provisioner triples (FBM T-200/T-202).
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Gate: every first-boot provisioner triple (fetcher + unit + preset) is whole."""

import os
import re
import sys

# unit basename -> (libexec fetcher, /var dirs the fetcher writes into)
PROVISIONERS = {
    "mios-models-firstboot.service": (
        "usr/libexec/mios/mios-models-firstboot",
        ("/var/lib/mios/llamacpp/models",),
    ),
}

UNIT_DIR = "usr/lib/systemd/system"
PRESET = "usr/lib/systemd/system-preset/90-mios.preset"
TMPFILES_DIR = "usr/lib/tmpfiles.d"

def tmpfiles_dirs(root: str) -> set:
    """Every directory path declared by a tmpfiles.d d/D/v/f line."""
    out = set()
    d = os.path.join(root, TMPFILES_DIR)
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".conf"):
            continue
        with open(os.path.join(d, fn), encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) >= 2 and parts[0] in ("d", "D", "v", "f", "F"):
                    out.add(parts[1])
    return out

def unit_field(text: str, key: str):
    m = re.search(r"^%s\s*=\s*(.*)$" % re.escape(key), text, re.M)
    return m.group(1).strip() if m else None

def check_one(root, unit_name, fetcher_rel, var_dirs, declared):
    bad = []
    unit_path = os.path.join(root, UNIT_DIR, unit_name)
    fetcher_path = os.path.join(root, fetcher_rel)

    if not os.path.isfile(fetcher_path):
        bad.append(f"{unit_name}: fetcher {fetcher_rel} does not exist")
        return bad
    if not os.path.isfile(unit_path):
        bad.append(f"{unit_name}: unit file missing from {UNIT_DIR}/")
        return bad

    unit = open(unit_path, encoding="utf-8", errors="replace").read()
    fetcher = open(fetcher_path, encoding="utf-8", errors="replace").read()

    execstart = unit_field(unit, "ExecStart") or ""
    if "/" + fetcher_rel.split("usr/", 1)[-1] not in execstart.replace("/usr/", "/"):
        if os.path.basename(fetcher_rel) not in execstart:
            bad.append(f"{unit_name}: ExecStart does not run {fetcher_rel} "
                       f"(got {execstart!r})")

    cond = unit_field(unit, "ConditionPathExists") or ""
    if not cond.startswith("!"):
        bad.append(f"{unit_name}: no ConditionPathExists=!<sentinel> gate "
                   f"(got {cond!r}) -- the oneshot would re-run every boot")
    else:
        sentinel = cond[1:].strip()
        if sentinel not in fetcher:
            bad.append(f"{unit_name}: gates on {sentinel} but the fetcher never "
                       f"names that path -- the sentinel is never written, so the "
                       f"unit runs forever")

    preset_path = os.path.join(root, PRESET)
    if os.path.isfile(preset_path):
        preset = open(preset_path, encoding="utf-8", errors="replace").read()
        if not re.search(r"^enable\s+%s\s*$" % re.escape(unit_name), preset, re.M):
            bad.append(f"{unit_name}: not enabled in {PRESET} -- installed but "
                       f"never started")
    else:
        bad.append(f"{PRESET} is missing")

    for d in var_dirs:
        if d not in declared:
            bad.append(f"{unit_name}: writes {d}, which no tmpfiles.d file "
                       f"declares (Architectural Law 2: no mkdir in /var)")
    return bad

def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or "."
    declared = tmpfiles_dirs(root)
    bad = []
    for unit_name, (fetcher_rel, var_dirs) in sorted(PROVISIONERS.items()):
        bad += check_one(root, unit_name, fetcher_rel, var_dirs, declared)
    if bad:
        for line in bad:
            print(line)
        return 1
    print(f"first-boot provisioner triples are whole "
          f"(checked={len(PROVISIONERS)} fetcher+unit+preset+tmpfiles)")
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# AI-hint: Drift gate for unmappable container names.
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Gate: every Quadlet declares a ContainerName that matches its unit."""

import glob
import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- py<3.11
    import tomli as tomllib  # type: ignore

TOML = "usr/share/mios/mios.toml"
QUADLET_GLOB = "usr/share/containers/systemd/*.container"

def expected_name(unit: str) -> str:
    """A template unit has no single container: it names the instantiated form."""
    if unit.endswith("@"):
        return unit[:-1] + "-%i"
    return unit

def ssot_containers(root: str) -> tuple:
    """({unit: ContainerName}, {unit: enabled}) from the SSOT. A container gated
    off in [quadlets.enable] renders no unit, which is not drift -- but it still
    has to name itself correctly for the day it is switched on."""
    path = os.path.join(root, TOML)
    if not os.path.isfile(path):
        return {}, {}
    with open(path, "rb") as fh:
        data = tomllib.load(fh) or {}
    enabled = (data.get("quadlets") or {}).get("enable") or {}
    out = {}
    for name, block in (data.get("containers") or {}).items():
        if isinstance(block, dict) and isinstance(block.get("Container"), dict):
            out[str(name)] = str(block["Container"].get("ContainerName") or "")
    return out, {k: v is not False for k, v in enabled.items()}

def rendered_containers(root: str) -> dict:
    out = {}
    for path in sorted(glob.glob(os.path.join(root, QUADLET_GLOB))):
        unit = os.path.basename(path)[: -len(".container")]
        text = open(path, encoding="utf-8", errors="replace").read()
        m = re.search(r"^ContainerName=(.*)$", text, re.M)
        out[unit] = (m.group(1).strip() if m else "")
    return out

def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT", ".")
    ssot, enabled = ssot_containers(root)
    rendered = rendered_containers(root)
    if not ssot:
        print(f"no [containers.*.Container] blocks found under {root}")
        return 1
    if not rendered:
        print(f"no rendered .container files found under {root}")
        return 1

    problems = []
    for unit in sorted(ssot):
        want = expected_name(unit)
        got = ssot[unit]
        if not got:
            problems.append(
                f"{unit}: no ContainerName in the SSOT -- Quadlet would name it "
                f"'systemd-{unit}', which no `systemctl` name matches")
        elif got != want:
            problems.append(f"{unit}: SSOT ContainerName is {got!r}, expected {want!r}")
    for unit in sorted(rendered):
        want = expected_name(unit)
        got = rendered[unit]
        if not got:
            problems.append(f"{unit}.container: rendered unit declares no ContainerName")
        elif got != want:
            problems.append(
                f"{unit}.container: rendered ContainerName is {got!r}, expected {want!r}")
    for unit in sorted(set(ssot) - set(rendered)):
        if enabled.get(unit, True):
            problems.append(
                f"{unit}: enabled in the SSOT but no rendered .container -- regenerate")

    if problems:
        for p in problems:
            print(p)
        return 1
    off = sum(1 for u in ssot if not enabled.get(u, True))
    print(f"every Quadlet names its own container "
          f"(ssot={len(ssot)} rendered={len(rendered)} gated-off={off})")
    return 0

if __name__ == "__main__":
    sys.exit(main())

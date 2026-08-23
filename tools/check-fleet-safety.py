#!/usr/bin/env python3
# AI-hint: Drift gate for hazards that are SAFE on one node and dangerous above it. Detected from the tree, and every one must sit in the shrink-only [blades.hazards].accepted register under a ratchet.
# AI-related: usr/share/mios/mios.toml, tools/test_check-fleet-safety.py, usr/lib/systemd/system/mios-ha-bootstrap.service, usr/share/containers/systemd/mios-k3s.container, usr/share/doc/mios/adr/0016-blade-node-topology.md
# AI-functions: fleet_shape, archetypes_granting, k3s_multi_server, pacemaker_unfenced, detect, register, max_accepted, violations, main

import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- py<3.11
    import tomli as tomllib  # type: ignore

TOML = "usr/share/mios/mios.toml"


def fleet_shape(data: dict) -> dict:
    """[blades] min/typical/max node counts."""
    b = data.get("blades") or {}
    return {k: b.get(k) for k in ("min_nodes", "typical_nodes", "max_nodes")}


def archetypes_granting(data: dict, needed) -> list:
    """Archetypes granting EVERY capability in `needed`."""
    blade = data.get("blade") or {}
    out = []
    for name, caps in (blade.get("archetypes") or {}).items():
        if isinstance(caps, str):
            caps = [caps]
        have = {str(c).strip() for c in (caps or [])}
        if set(needed) <= have:
            out.append(name)
    return sorted(out)


def k3s_multi_server(data: dict, root: str):
    """More than one archetype can stand up a k3s control plane, and the unit
    has no join path. Detail string, or None."""
    req = ((data.get("blade") or {}).get("requires") or {}).get("mios-k3s")
    if not req:
        return None
    if isinstance(req, str):
        req = [req]
    grantors = archetypes_granting(data, [str(c).strip() for c in req])
    if len(grantors) < 2:
        return None
    path = os.path.join(root, "usr/share/containers/systemd/mios-k3s.container")
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            body = fh.read()
    except OSError:
        return None
    code = "\n".join(l for l in body.splitlines() if not l.lstrip().startswith("#"))
    if not re.search(r"\bk3s\s+server\b", code):
        return None
    if "K3S_URL" in code:
        return None          # a join path exists; the peers are not independent
    return ("%d archetypes grant what mios-k3s requires (%s) and the unit runs "
            "`k3s server` with no K3S_URL -- each would stand up its OWN control "
            "plane" % (len(grantors), ", ".join(grantors)))


_UNFENCED = re.compile(r"stonith-enabled\s*=\s*false")


def pacemaker_unfenced(data: dict, root: str):
    """Pacemaker configured with fencing off. Detail string, or None."""
    hits = []
    for base in ("usr/lib/systemd/system", "usr/libexec/mios"):
        d = os.path.join(root, base)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if not os.path.isfile(p):
                continue
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    body = fh.read()
            except OSError:
                continue
            for num, line in enumerate(body.splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                if _UNFENCED.search(line):
                    hits.append("%s/%s:%d" % (base, name, num))
    if not hits:
        return None
    return ("fencing is disabled (%s) -- safe on one node, and how split-brain "
            "corrupts data on more" % ", ".join(hits))


DETECTORS = (
    ("k3s-multi-server", k3s_multi_server),
    ("pacemaker-unfenced", pacemaker_unfenced),
)


def detect(data: dict, root: str) -> dict:
    """{hazard-id: detail} for every hazard that currently reproduces."""
    out = {}
    for key, fn in DETECTORS:
        detail = fn(data, root)
        if detail:
            out[key] = detail
    return out


def register(data: dict) -> list:
    reg = ((data.get("blades") or {}).get("hazards") or {}).get("accepted")
    if reg is None:
        return []
    return [str(x).strip() for x in reg if str(x).strip()]


def max_accepted(data: dict):
    val = ((data.get("blades") or {}).get("hazards") or {}).get("max_accepted")
    return val if isinstance(val, int) else None


def violations(data: dict, root: str) -> list:
    viol = []
    shape = fleet_shape(data)
    if not isinstance(shape.get("max_nodes"), int):
        return ["[blades].max_nodes is unset -- the fleet has no declared size, "
                "so nothing can tell a standalone-only config from a broken one"]
    max_nodes = shape["max_nodes"]

    hazards = data.get("blades", {}).get("hazards")
    if hazards is None:
        return ["[blades.hazards] is absent -- nothing bounds how many "
                "above-one-node hazards the tree may carry"]
    if "accepted" not in hazards:
        viol.append("[blades.hazards] declares no `accepted` key -- an implied "
                    "empty register is indistinguishable from a forgotten one")

    reg = register(data)
    if len(reg) != len(set(reg)):
        dupes = sorted({x for x in reg if reg.count(x) > 1})
        viol.append("[blades.hazards].accepted lists a hazard twice: %s"
                    % ", ".join(dupes))
    if reg != sorted(reg):
        viol.append("[blades.hazards].accepted is not sorted -- an unsorted "
                    "register hides an addition inside a reordering")

    known = {k for k, _ in DETECTORS}
    for bad in sorted(set(reg) - known):
        viol.append("[blades.hazards].accepted names '%s', which no detector "
                    "produces -- it can never be retired" % bad)

    found = detect(data, root)
    if max_nodes <= 1:
        # Standalone by declaration: these hazards do not bite. Say so rather
        # than pass silently, because raising max_nodes must re-arm them.
        return viol

    for key in sorted(set(found) - set(reg)):
        viol.append("%s: %s. Fix it, or accept it in [blades.hazards].accepted "
                    "with a justification -- [blades].max_nodes is %d"
                    % (key, found[key], max_nodes))
    for key in sorted(set(reg) & known - set(found)):
        viol.append("[blades.hazards].accepted carries '%s', which no longer "
                    "reproduces -- drop it; the register only shrinks" % key)

    ceiling = max_accepted(data)
    if ceiling is None:
        viol.append("[blades.hazards].max_accepted is unset -- without a ceiling "
                    "the register absorbs new hazards as fast as they appear")
    elif len(reg) > ceiling:
        viol.append("[blades.hazards].accepted holds %d, over the ratchet ceiling "
                    "max_accepted = %d. The ceiling only comes DOWN"
                    % (len(reg), ceiling))
    elif len(reg) < ceiling:
        viol.append("[blades.hazards].accepted holds %d but max_accepted is %d -- "
                    "lower it to %d so the ground gained is held"
                    % (len(reg), ceiling, len(reg)))
    return viol


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or "."
    path = os.path.join(root, TOML)
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except OSError as exc:
        print("check-fleet-safety: cannot read %s: %s" % (path, exc), file=sys.stderr)
        return 1

    viol = violations(data, root)
    if viol:
        for v in viol:
            print("check_fleet_safety: %s" % v, file=sys.stderr)
        return 1

    shape = fleet_shape(data)
    print("[check-fleet-safety] fleet is %s-%s nodes (typical %s); %d "
          "above-one-node hazard(s) accepted (ceiling %s)."
          % (shape.get("min_nodes"), shape.get("max_nodes"),
             shape.get("typical_nodes"), len(register(data)), max_accepted(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

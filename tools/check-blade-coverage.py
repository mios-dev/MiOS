#!/usr/bin/env python3
# AI-hint: Drift gate for the blade ACTIVATION axis. Every Quadlet container AND every long-running native .service unit must be classified exactly once: capability-gated in [blade.requires], listed in [blade].seat_side (it deliberately runs everywhere, because a seat still needs its UX and front door), or in the shrink-only [blade].ungated debt register. Counting only containers was this gate's own blind spot -- it reported "23 of 23" over a set that excluded 18 long-running units. Also fails an entry naming a unit that does not exist, a capability no archetype grants, and a unit classified two ways.
# AI-related: usr/share/mios/mios.toml, tools/test_check-blade-coverage.py, automation/48-mios-dropin-fanout.sh, tools/generate-blade-dropins.py
# AI-functions: containers, long_running_units, all_units, requires, archetype_caps, register, seat_side, classify, main
"""Gate: every service is capability-gated, or registered as ungated core."""

import os
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- py<3.11
    import tomli as tomllib  # type: ignore

TOML = "usr/share/mios/mios.toml"


def containers(data: dict) -> set:
    """Every Quadlet container the SSOT declares."""
    return set(data.get("containers") or {})


def long_running_units(root: str) -> set:
    """Shipped .service units that stay up. A oneshot needs no blade gate: it
    runs, exits, and costs a seat nothing to leave enabled."""
    out = set()
    unit_dir = os.path.join(root, "usr/lib/systemd/system")
    if not os.path.isdir(unit_dir):
        return out
    for name in sorted(os.listdir(unit_dir)):
        if not name.endswith(".service") or "@" in name:
            continue
        try:
            with open(os.path.join(unit_dir, name), encoding="utf-8",
                      errors="replace") as fh:
                body = fh.read()
        except OSError:
            continue
        stype = ""
        for line in body.splitlines():
            if line.startswith("Type="):
                stype = line.split("=", 1)[1].strip()
                break
        if stype != "oneshot":
            out.add(name[:-len(".service")])
    return out


def all_units(data: dict, root: str) -> set:
    """Containers and native units share ONE unit namespace: a Quadlet named
    `x` generates `x.service`, so one classification covers both spellings."""
    return containers(data) | long_running_units(root)


def seat_side(data: dict) -> list:
    """Units a seat deliberately runs -- a positive claim, not debt."""
    reg = (data.get("blade") or {}).get("seat_side") or []
    return [str(x).strip() for x in reg if str(x).strip()]


def requires(data: dict) -> dict:
    """{service: [capability, ...]} from [blade.requires]."""
    out = {}
    for svc, caps in ((data.get("blade") or {}).get("requires") or {}).items():
        if isinstance(caps, str):
            caps = [caps]
        out[svc] = [str(c).strip() for c in (caps or []) if str(c).strip()]
    return out


def archetype_caps(data: dict) -> set:
    """Every capability some archetype can grant."""
    out = set()
    for caps in ((data.get("blade") or {}).get("archetypes") or {}).values():
        if isinstance(caps, str):
            caps = [caps]
        for c in caps or []:
            out.add(str(c).strip())
    return {c for c in out if c}


def register(data: dict) -> list:
    """The shrink-only ungated register, in declaration order."""
    reg = (data.get("blade") or {}).get("ungated") or []
    return [str(x).strip() for x in reg if str(x).strip()]


def classify(data: dict, root: str = ".") -> list:
    """Return the violations; empty means every unit has exactly one answer."""
    viol = []
    units = all_units(data, root)
    if not units:
        return ["no containers and no long-running units found -- the gate would "
                "pass vacuously over an empty set"]

    req = requires(data)
    granted = archetype_caps(data)
    reg, seat = register(data), seat_side(data)
    reg_set, seat_set = set(reg), set(seat)

    for name, lst in (("ungated", reg), ("seat_side", seat)):
        if len(lst) != len(set(lst)):
            dupes = sorted({k for k in lst if lst.count(k) > 1})
            viol.append("[blade].%s lists a unit twice: %s" % (name, ", ".join(dupes)))

    for label, names in (("[blade.requires] gates", set(req)),
                         ("[blade].ungated names", reg_set),
                         ("[blade].seat_side names", seat_set)):
        for svc in sorted(names - units):
            viol.append("%s '%s', which is not a declared container or a shipped "
                        "long-running unit" % (label, svc))

    for svc in sorted((set(req) & reg_set) | (set(req) & seat_set)
                      | (reg_set & seat_set)):
        viol.append("unit '%s' is classified more than once -- gated, seat-side "
                    "and ungated are mutually exclusive" % svc)

    for svc, caps in sorted(req.items()):
        if not caps:
            viol.append("[blade.requires].%s lists no capability -- an empty list "
                        "gates nothing, so say so in [blade].seat_side instead" % svc)
        for cap in caps:
            if cap not in granted:
                viol.append("capability '%s' (required by %s) is granted by NO "
                            "archetype -- nothing could ever activate it" % (cap, svc))

    for svc in sorted(units - set(req) - reg_set - seat_set):
        viol.append("unit '%s' is classified nowhere -- gate it in [blade.requires], "
                    "declare it in [blade].seat_side, or register the debt in "
                    "[blade].ungated" % svc)

    return viol


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or "."
    path = os.path.join(root, TOML)
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except OSError as exc:
        print("check-blade-coverage: cannot read %s: %s" % (path, exc), file=sys.stderr)
        return 1

    viol = classify(data, root)
    if viol:
        for v in viol:
            print("check_blade_coverage: %s" % v, file=sys.stderr)
        return 1

    print("[check-blade-coverage] %d unit(s): %d capability-gated, %d seat-side, "
          "%d registered ungated" % (len(all_units(data, root)), len(requires(data)),
                                     len(seat_side(data)), len(register(data))))
    return 0


if __name__ == "__main__":
    sys.exit(main())

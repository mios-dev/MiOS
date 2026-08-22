#!/usr/bin/env python3
# AI-hint: Drift gate for the blade ACTIVATION axis. Every Quadlet container must either map to a capability in [blade.requires] or sit in the shrink-only [blade].ungated register, so "a seat runs only what it needs" is a stated taxonomy rather than an empty default. Also fails a requires entry naming a container that does not exist, a capability no archetype ever grants (nothing could activate it), and a register entry that has since been gated -- the register only shrinks.
# AI-related: usr/share/mios/mios.toml, tools/test_check-blade-coverage.py, automation/48-mios-dropin-fanout.sh, tools/generate-blade-dropins.py
# AI-functions: containers, requires, archetype_caps, register, classify, main
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


def classify(data: dict) -> list:
    """Return the violations; empty means every service has a stated answer."""
    viol = []
    conts = containers(data)
    if not conts:
        return ["[containers] declares nothing -- the gate would pass vacuously "
                "over an empty set"]

    req = requires(data)
    granted = archetype_caps(data)
    reg = register(data)
    reg_set = set(reg)

    if len(reg) != len(reg_set):
        dupes = sorted({k for k in reg if reg.count(k) > 1})
        viol.append("[blade].ungated lists a service twice: %s" % ", ".join(dupes))

    for svc in sorted(set(req) - conts):
        viol.append("[blade.requires] gates '%s', which is not a declared container"
                    % svc)

    for svc in sorted(reg_set - conts):
        viol.append("[blade].ungated names '%s', which is not a declared container"
                    % svc)

    for svc in sorted(set(req) & reg_set):
        viol.append("service '%s' is capability-gated AND registered ungated -- "
                    "the register only shrinks, so remove it" % svc)

    for svc, caps in sorted(req.items()):
        if not caps:
            viol.append("[blade.requires].%s lists no capability -- an empty list "
                        "gates nothing, so say so in [blade].ungated instead" % svc)
        for cap in caps:
            if cap not in granted:
                viol.append("capability '%s' (required by %s) is granted by NO "
                            "archetype -- nothing could ever activate it" % (cap, svc))

    for svc in sorted(conts - set(req) - reg_set):
        viol.append("container '%s' is neither capability-gated in [blade.requires] "
                    "nor registered in [blade].ungated -- state whether a seat runs it"
                    % svc)

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

    viol = classify(data)
    if viol:
        for v in viol:
            print("check_blade_coverage: %s" % v, file=sys.stderr)
        return 1

    print("[check-blade-coverage] %d container(s): %d capability-gated, %d "
          "registered ungated" % (len(containers(data)), len(requires(data)),
                                  len(register(data))))
    return 0


if __name__ == "__main__":
    sys.exit(main())

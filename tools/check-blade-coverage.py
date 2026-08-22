#!/usr/bin/env python3
# AI-hint: Drift gate for the blade ACTIVATION axis. Every Quadlet container AND every long-running native .service unit must be classified exactly once: capability-gated in [blade.requires], listed in [blade].seat_side (it deliberately runs everywhere, because a seat still needs its UX and front door), or in the shrink-only [blade].ungated debt register. Counting only containers was this gate's own blind spot -- it reported "23 of 23" over a set that excluded 18 long-running units. Also fails an entry naming a unit that does not exist, a capability no archetype grants, and a unit classified two ways.
# AI-related: usr/share/mios/mios.toml, tools/test_check-blade-coverage.py, automation/48-mios-dropin-fanout.sh, tools/generate-blade-dropins.py
# AI-functions: containers, long_running_units, all_units, known_units, port_namers, person_facing, seat_dead_weight, requires, archetype_caps, register, seat_side, soft_ok, unit_pulls, dependency_violations, classify, main
"""Gate: every service is capability-gated, or registered as ungated core."""

import os
import re
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
    """Units that MUST carry a classification: containers and long-running
    services. Containers and native units share ONE namespace -- a Quadlet named
    `x` generates `x.service` -- so one classification covers both spellings."""
    return containers(data) | long_running_units(root)


def known_units(data: dict, root: str) -> set:
    """Every shipped unit stem, any type. Wider than all_units on purpose: a
    oneshot or a target needs no classification of its own, but MAY legitimately
    be gated because it activates something that is."""
    out = set(containers(data))
    unit_dir = os.path.join(root, "usr/lib/systemd/system")
    if os.path.isdir(unit_dir):
        for name in os.listdir(unit_dir):
            if os.path.isfile(os.path.join(unit_dir, name)) and "." in name:
                out.add(name.rsplit(".", 1)[0])
    return out


def seat_side(data: dict) -> list:
    """Units a seat deliberately runs -- a positive claim, not debt."""
    reg = (data.get("blade") or {}).get("seat_side") or []
    return [str(x).strip() for x in reg if str(x).strip()]


# Ordering only. After= does not activate anything, so it never propagates a gate.
_PULL_KEYS = ("Requires=", "BindsTo=", "Requisite=", "Wants=")


def unit_pulls(root: str) -> dict:
    """{unit-stem: {dependency-stem, ...}} over every shipped unit of any type.

    Only ACTIVATING dependencies count: a unit that merely orders itself After=
    a gated unit is unaffected when that unit is condition-skipped.
    """
    out = {}
    unit_dir = os.path.join(root, "usr/lib/systemd/system")
    if not os.path.isdir(unit_dir):
        return out
    for name in sorted(os.listdir(unit_dir)):
        path = os.path.join(unit_dir, name)
        if not os.path.isfile(path) or "." not in name:
            continue
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                body = fh.read()
        except OSError:
            continue
        deps = set()
        for line in body.splitlines():
            for key in _PULL_KEYS:
                if line.startswith(key):
                    for tok in line[len(key):].split():
                        deps.add(tok[:-len(".service")]
                                 if tok.endswith(".service") else tok)
        if deps:
            out[name.rsplit(".", 1)[0]] = deps
    return out


def soft_ok(data: dict) -> list:
    """Units whose pull on a gated unit is soft and that degrade without it."""
    reg = (data.get("blade") or {}).get("soft_ok") or []
    return [str(x).strip() for x in reg if str(x).strip()]


def dependency_violations(data: dict, root: str) -> list:
    """A unit activating a gated unit must carry its capabilities (ADR-0016 D4)."""
    req = requires(data)
    seat = set(seat_side(data)) | set(soft_ok(data))
    viol = []
    for stem, deps in sorted(unit_pulls(root).items()):
        hit = deps & set(req)
        if not hit:
            continue
        need = set().union(*(set(req[h]) for h in hit))
        have = set(req.get(stem, []))
        if stem in seat or need <= have:
            continue
        viol.append("unit '%s' activates %s but is missing their capability %s -- "
                    "it would start where its dependency is condition-skipped"
                    % (stem, "/".join(sorted(hit)),
                       "/".join(sorted(need - have))))
    return viol


def port_namers(data: dict, root: str) -> dict:
    """{port-key: {unit-stem, ...}} over every shipped unit that names a port,
    by MIOS_PORT_<KEY> or by its literal value."""
    ports = {k: v for k, v in (data.get("ports") or {}).items() if isinstance(v, int)}
    out = {k: set() for k in ports}
    for base in ("usr/lib/systemd/system", "usr/share/containers/systemd"):
        d = os.path.join(root, base)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            path = os.path.join(d, name)
            if not os.path.isfile(path) or "." not in name:
                continue
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    body = fh.read()
            except OSError:
                continue
            code = "\n".join(l for l in body.splitlines()
                              if not l.lstrip().startswith("#"))
            stem = name.rsplit(".", 1)[0]
            for key, num in ports.items():
                if ("MIOS_PORT_%s" % key.upper()) in code or \
                        re.search(r"(?<![0-9])%d(?![0-9])" % num, code):
                    out[key].add(stem)
    return out


def person_facing(data: dict) -> set:
    """Ports whose client is the human: anything with a browser-openable [urls]
    entry, plus the front door [ai].endpoint resolves. Derived, not declared."""
    out = set()
    for value in ((data.get("urls") or {}).values()):
        if isinstance(value, str):
            out |= {m.lower() for m in
                    re.findall(r"\$\{MIOS_PORT_([A-Z0-9_]+)\}", value)}
    endpoint = str((data.get("ai") or {}).get("endpoint") or "")
    out |= {m.lower() for m in
            re.findall(r"\$\{MIOS_PORT_([A-Z0-9_]+)\}", endpoint)}
    return out


def seat_dead_weight(data: dict, root: str) -> list:
    """A seat-side unit whose port only a gated unit dials is dead weight. The
    coupling is an address, so the dependency walk cannot see it."""
    req, seat = requires(data), set(seat_side(data))
    soft = set(soft_ok(data))
    viol = []
    for key, namers in sorted(port_namers(data, root).items()):
        if key in person_facing(data):
            continue          # the client is the human, not another unit
        binders = namers & seat
        others = namers - seat
        if not binders or not others:
            continue          # nobody else names it: the person is the client
        if others - set(req) - soft:
            continue          # at least one ungated client remains
        viol.append("seat-side %s binds '%s', but every other unit naming it "
                    "(%s) is capability-gated -- on a seat it serves nothing"
                    % ("/".join(sorted(binders)), key, ", ".join(sorted(others))))
    return viol


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

    known = known_units(data, root)
    for label, names in (("[blade.requires] gates", set(req)),
                         ("[blade].ungated names", reg_set),
                         ("[blade].seat_side names", seat_set)):
        for svc in sorted(names - known):
            viol.append("%s '%s', which is not a declared container or a shipped "
                        "unit" % (label, svc))

    for svc in sorted((set(req) & reg_set) | (set(req) & seat_set)
                      | (reg_set & seat_set)):
        viol.append("unit '%s' is classified more than once -- gated, seat-side "
                    "and ungated are mutually exclusive" % svc)

    fallbacks = (data.get("blade") or {}).get("cpu_fallbacks") or {}
    for svc, caps in sorted(req.items()):
        if not caps:
            viol.append("[blade.requires].%s lists no capability -- an empty list "
                        "gates nothing, so say so in [blade].seat_side instead" % svc)
        if "gpu-serving" in caps and (svc not in fallbacks or not fallbacks[svc]):
            viol.append("unit '%s' requires 'gpu-serving' but declares no fallback in [blade.cpu_fallbacks] (AGY-1596)" % svc)
        for cap in caps:
            if cap not in granted:
                viol.append("capability '%s' (required by %s) is granted by NO "
                            "archetype -- nothing could ever activate it" % (cap, svc))

    for svc in sorted(units - set(req) - reg_set - seat_set):
        viol.append("unit '%s' is classified nowhere -- gate it in [blade.requires], "
                    "declare it in [blade].seat_side, or register the debt in "
                    "[blade].ungated" % svc)

    viol.extend(dependency_violations(data, root))
    viol.extend(seat_dead_weight(data, root))
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

    must = all_units(data, root)
    req = requires(data)
    print("[check-blade-coverage] %d unit(s) require a classification: %d gated, "
          "%d seat-side, %d registered ungated. %d further unit(s) are gated "
          "because they activate one (oneshots, targets)."
          % (len(must), len(set(req) & must), len(seat_side(data)),
             len(register(data)), len(set(req) - must)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

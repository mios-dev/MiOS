#!/usr/bin/env python3
# AI-hint: Drift gate for allocated-but-unbound ports.
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Gate: an allocated port is bound by something, or registered as not yet wired."""

import os
import re
import subprocess
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- py<3.11
    import tomli as tomllib  # type: ignore

TOML = "usr/share/mios/mios.toml"

# Surfaces that only DESCRIBE ports never prove one is bound: the SSOT itself,
# documentation, generated projections and the task ledgers.
SKIP_PREFIXES = (
    "usr/share/doc/",
    "usr/share/mios/reference/",
    "usr/share/mios/mios.toml",
    "usr/share/mios/names.generated.txt",
    "usr/share/mios/referenced_names.txt",
    "automation/lib/globals.sh",
    "automation/lib/globals.ps1",
    "automation/manifest.json",
    "tools/manifest.json",
    "docs/",
    "ROADMAP.md",
    "TASKS.md",
    "AGY-TASKS.md",
    "ADR.md",
)


def port_keys(data: dict) -> set:
    """Numeric [ports] keys. stack_id is an offset, not a port."""
    ports = data.get("ports") or {}
    return {k for k, v in ports.items() if isinstance(v, int) and k != "stack_id"}


def register(data: dict) -> list:
    """The shrink-only unbound register, in declaration order."""
    reg = (data.get("ports") or {}).get("unbound") or []
    return [str(x).strip() for x in reg if str(x).strip()]


def _tracked_files(root: str) -> list:
    out = subprocess.run(["git", "-C", root, "ls-files"],
                         capture_output=True, text=True, check=False).stdout
    return [f for f in out.split("\n") if f and not f.startswith(SKIP_PREFIXES)]


def referenced_ports(root: str, keys: set) -> set:
    """Port keys whose MIOS_PORT_<KEY> appears in a file that could bind or dial it."""
    wanted = {("MIOS_PORT_" + k.upper()): k for k in keys}
    pattern = re.compile(r"\bMIOS_PORT_([A-Z0-9_]+)\b")
    found = set()
    for rel in _tracked_files(root):
        path = os.path.join(root, rel)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                body = fh.read()
        except OSError:
            continue
        for m in pattern.finditer(body):
            key = wanted.get("MIOS_PORT_" + m.group(1))
            if key:
                found.add(key)
    return found


def classify(data: dict, referenced: set) -> list:
    """Return the violations; empty means every allocated port is accounted for."""
    viol = []
    keys = port_keys(data)
    if not keys:
        return ["[ports] declares no numeric port -- the gate would pass "
                "vacuously over an empty set"]

    reg = register(data)
    reg_set = set(reg)

    if len(reg) != len(reg_set):
        dupes = sorted({k for k in reg if reg.count(k) > 1})
        viol.append("[ports].unbound lists a key twice: %s" % ", ".join(dupes))

    for k in sorted(reg_set - keys):
        viol.append("[ports].unbound names '%s', which is not a [ports] key" % k)

    for k in sorted(reg_set & referenced):
        viol.append("port '%s' IS referenced now but still sits in [ports].unbound "
                    "-- the register only shrinks, so remove it" % k)

    for k in sorted(keys - referenced - reg_set):
        viol.append("port '%s' is allocated but no Quadlet, unit or program "
                    "references MIOS_PORT_%s -- the collision check guards a number "
                    "nothing binds" % (k, k.upper()))

    return viol


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or "."
    path = os.path.join(root, TOML)
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except OSError as exc:
        print("check-ports-bound: cannot read %s: %s" % (path, exc), file=sys.stderr)
        return 1

    keys = port_keys(data)
    referenced = referenced_ports(root, keys)
    viol = classify(data, referenced)
    if viol:
        for v in viol:
            print("check_ports_bound: %s" % v, file=sys.stderr)
        return 1

    print("[check-ports-bound] %d port(s): %d referenced by a consumer, %d "
          "registered unbound" % (len(keys), len(referenced & keys),
                                  len(register(data))))
    return 0


if __name__ == "__main__":
    sys.exit(main())

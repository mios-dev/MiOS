#!/usr/bin/env python3
# AI-hint: Drift gate for service addressing. Every numeric [ports] key must resolve to exactly one canonical address -- either a [urls] entry that templates its ${MIOS_PORT_*}, or membership of the shrink-only [urls].non_addressable register. A port in NEITHER fails the gate, so a new service cannot be added without stating how it is addressed; a port in BOTH fails too, because two answers is the problem this exists to prevent. The register only shrinks: a key leaves it by gaining a [urls] entry and can never be added back silently.
# AI-related: usr/share/mios/mios.toml, tools/test_check-service-urls.py, automation/98-drift-checks.sh, usr/share/doc/mios/adr/0016-blade-node-topology.md
# AI-functions: browser_openable, covered_ports, port_keys, register, classify, main
"""Gate: one canonical address per service, or a registered reason there is none."""

import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- py<3.11
    import tomli as tomllib  # type: ignore

TOML = "usr/share/mios/mios.toml"
_PORT_VAR = re.compile(r"\$\{MIOS_PORT_([A-Z0-9_]+)\}")


def port_keys(data: dict) -> set:
    """Numeric [ports] keys. stack_id is an offset, not a port."""
    ports = (data.get("ports") or {})
    return {k for k, v in ports.items() if isinstance(v, int) and k != "stack_id"}


def covered_ports(data: dict) -> set:
    """Port keys templated by at least one [urls] string."""
    out = set()
    for value in (data.get("urls") or {}).values():
        if not isinstance(value, str):
            continue
        for m in _PORT_VAR.finditer(value):
            out.add(m.group(1).lower())
    return out


def register(data: dict) -> list:
    """The shrink-only non-addressable register, in declaration order."""
    reg = (data.get("urls") or {}).get("non_addressable") or []
    return [str(x).strip() for x in reg if str(x).strip()]


def classify(data: dict) -> list:
    """Return the violations; empty means every port has exactly one answer."""
    viol = []
    keys = port_keys(data)
    if not keys:
        return ["[ports] declares no numeric port -- the gate would pass "
                "vacuously over an empty set"]

    covered = covered_ports(data) & keys
    reg = register(data)
    reg_set = set(reg)

    if len(reg) != len(reg_set):
        dupes = sorted({k for k in reg if reg.count(k) > 1})
        viol.append("[urls].non_addressable lists a key twice: %s" % ", ".join(dupes))

    for k in sorted(reg_set - keys):
        viol.append("[urls].non_addressable names '%s', which is not a [ports] key "
                    "-- a register entry must name a port that exists" % k)

    for k in sorted(covered & reg_set):
        viol.append("port '%s' has a [urls] entry AND sits in non_addressable -- "
                    "two answers is the drift this gate exists to prevent" % k)

    for k in sorted(keys - covered - reg_set):
        viol.append("port '%s' has no canonical [urls] address and is not in "
                    "[urls].non_addressable -- state how it is addressed" % k)

    return viol


def browser_openable(data: dict) -> list:
    """[urls] is what a person clicks, so every value must use a scheme a
    browser opens. A postgresql:// DSN there made the table mean two things."""
    viol = []
    for key, value in sorted((data.get("urls") or {}).items()):
        if not isinstance(value, str):
            continue
        if "://" not in value:
            viol.append("[urls].%s is not a URL: %r" % (key, value))
        elif value.split("://", 1)[0] not in ("http", "https"):
            viol.append("[urls].%s uses the %s scheme -- [urls] is the "
                        "browser-openable surface, so an inter-service address "
                        "belongs on the key its consumers already resolve"
                        % (key, value.split("://", 1)[0]))
    return viol


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or "."
    path = os.path.join(root, TOML)
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except OSError as exc:
        print("check-service-urls: cannot read %s: %s" % (path, exc), file=sys.stderr)
        return 1

    viol = classify(data) + browser_openable(data)
    if viol:
        for v in viol:
            print("check_service_urls: %s" % v, file=sys.stderr)
        return 1

    keys, covered, reg = port_keys(data), covered_ports(data), register(data)
    print("[check-service-urls] %d port(s): %d addressed by [urls], %d registered "
          "non-addressable" % (len(keys), len(covered & keys), len(reg)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

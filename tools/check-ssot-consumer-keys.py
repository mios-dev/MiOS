#!/usr/bin/env python3
# AI-hint: Drift gate for the SSOT<->consumer contract. Shipped Python reads config as _toml_section("<table>").get("<key>"); this asserts that <table>.<key> actually EXISTS in mios.toml. When it does not the consumer silently takes its compiled default, so the SSOT and the code disagree in total silence and every test that stubs the value still passes. That is how nine security controls -- api_require_auth, principal_bind_mode, rule_of_two_mode, quarantine_mode, the firewall verb lists and the host allowlist -- sat unreachable under an unclosed [security.nohc_allowlist] header. A key declared elsewhere in the SSOT is MISPLACED; one declared nowhere is UNDECLARED. Both go in the shrink-only [ssot_consumers].unresolved register with a max_unresolved ratchet.
# AI-related: usr/share/mios/mios.toml, tools/test_check-ssot-consumer-keys.py, usr/lib/mios/agent-pipe/mios_pipe/kernel/config.py, automation/98-drift-checks.sh
# AI-functions: consumer_reads, resolve, declared_elsewhere, register, max_unresolved, unresolved, violations, main
"""Gate: every SSOT key a consumer reads is a key the SSOT declares."""

import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- py<3.11
    import tomli as tomllib  # type: ignore

TOML = "usr/share/mios/mios.toml"
SCAN_ROOTS = ("usr",)

# `_toml_section("x").get("y"` and `(_toml_section("x") or {}).get("y"`.
_READ = re.compile(
    r"""_toml_section\(\s*["']([a-z0-9_.]+)["']\s*\)(?:\s*or\s*\{\}\s*\))?"""
    r"""\s*\.get\(\s*["']([a-z0-9_]+)["']"""
)


def consumer_reads(root: str) -> dict:
    """{(table, key): [file:line, ...]} over shipped Python.

    Tests are skipped: a test may legitimately read a key it stubs itself.
    """
    hits = {}
    for scan in SCAN_ROOTS:
        base = os.path.join(root, scan)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames
                           if d != "__pycache__" and not d.startswith(".venv")]
            for name in sorted(filenames):
                if not name.endswith(".py") or name.startswith("test_"):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        body = fh.read()
                except OSError:
                    continue
                rel = os.path.relpath(path, root).replace(os.sep, "/")
                for m in _READ.finditer(body):
                    site = "%s:%d" % (rel, body[:m.start()].count("\n") + 1)
                    hits.setdefault((m.group(1), m.group(2)), []).append(site)
    return {k: sorted(set(v)) for k, v in hits.items()}


def resolve(data: dict, dotted: str):
    """The table at a dotted path, or None."""
    cur = data
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def declared_elsewhere(data: dict, key: str) -> list:
    """Every dotted path in the SSOT that declares this key name."""
    out = []

    def walk(table, path):
        for k, v in table.items():
            if k == key:
                out.append(".".join(path + [k]))
            if isinstance(v, dict):
                walk(v, path + [k])

    walk(data, [])
    return sorted(out)


def register(data: dict) -> list:
    """[ssot_consumers].unresolved, in declaration order."""
    reg = (data.get("ssot_consumers") or {}).get("unresolved")
    if reg is None:
        return []
    return [str(x).strip() for x in reg if str(x).strip()]


def max_unresolved(data: dict):
    val = (data.get("ssot_consumers") or {}).get("max_unresolved")
    return val if isinstance(val, int) else None


def unresolved(data: dict, root: str) -> dict:
    """{'table.key': (sites, elsewhere)} for every read that resolves to nothing."""
    out = {}
    for (table, key), sites in consumer_reads(root).items():
        target = resolve(data, table)
        if isinstance(target, dict) and key in target:
            continue
        out["%s.%s" % (table, key)] = (sites, declared_elsewhere(data, key))
    return out


def violations(data: dict, root: str) -> list:
    viol = []
    reads = consumer_reads(root)
    if not reads:
        return ["no _toml_section(...).get(...) reads found at all -- the gate "
                "would pass vacuously over an empty set"]

    table = data.get("ssot_consumers")
    if table is None:
        return ["[ssot_consumers] is absent -- nothing bounds how many config keys "
                "a consumer may read that the SSOT does not declare"]
    if "unresolved" not in table:
        viol.append("[ssot_consumers] declares no `unresolved` key -- an implied "
                    "empty register is indistinguishable from a forgotten one")

    reg = register(data)
    if len(reg) != len(set(reg)):
        dupes = sorted({x for x in reg if reg.count(x) > 1})
        viol.append("[ssot_consumers].unresolved lists a pair twice: %s" % ", ".join(dupes))
    if reg != sorted(reg):
        viol.append("[ssot_consumers].unresolved is not sorted -- an unsorted "
                    "register hides an addition inside a reordering")

    found = unresolved(data, root)
    for pair in sorted(set(found) - set(reg)):
        sites, elsewhere = found[pair]
        if elsewhere:
            viol.append("%s is read at %s but the SSOT declares that key at %s -- "
                        "the consumer takes its compiled default and nobody is told"
                        % (pair, sites[0], "/".join(elsewhere)))
        else:
            viol.append("%s is read at %s and is declared NOWHERE in the SSOT"
                        % (pair, sites[0]))

    for pair in sorted(set(reg) - set(found)):
        if pair.rsplit(".", 1)[0] not in {t for t, _ in reads}:
            viol.append("[ssot_consumers].unresolved names '%s', which no shipped "
                        "consumer reads -- drop it" % pair)
        else:
            viol.append("[ssot_consumers].unresolved names '%s', which resolves now "
                        "-- drop it from the register; the register only shrinks" % pair)

    ceiling = max_unresolved(data)
    if ceiling is None:
        viol.append("[ssot_consumers].max_unresolved is unset -- without a ceiling "
                    "the register absorbs new breakage as fast as it appears")
    elif len(reg) > ceiling:
        viol.append("[ssot_consumers].unresolved holds %d entries, over the ratchet "
                    "ceiling max_unresolved = %d. The ceiling only comes DOWN"
                    % (len(reg), ceiling))
    elif len(reg) < ceiling:
        viol.append("[ssot_consumers].unresolved holds %d entries but max_unresolved "
                    "is still %d -- lower it to %d so the ground gained is held"
                    % (len(reg), ceiling, len(reg)))
    return viol


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or "."
    path = os.path.join(root, TOML)
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except OSError as exc:
        print("check-ssot-consumer-keys: cannot read %s: %s" % (path, exc),
              file=sys.stderr)
        return 1

    viol = violations(data, root)
    if viol:
        for v in viol:
            print("check_ssot_consumer_keys: %s" % v, file=sys.stderr)
        return 1

    reads = consumer_reads(root)
    reg = register(data)
    print("[check-ssot-consumer-keys] %d consumer read(s) of %d distinct SSOT key(s); "
          "%d unresolved and registered (ceiling %s)."
          % (sum(len(v) for v in reads.values()), len(reads), len(reg),
             max_unresolved(data)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

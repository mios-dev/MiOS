# AI-hint: !/usr/bin/env python3 Drift gate for Law 7 at the point it actually bites -- a MIOS_PORT_<KEY> paired with a literal that disagrees with [ports].<key>.
# AI-doc: usr/share/doc/mios/manual/_harvest/tools_check_port_fallbacks_py.md
"""Gate: a literal beside a MIOS_PORT_ name must be that port's value."""

import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- py<3.11
    import tomli as tomllib  # type: ignore

TOML = "usr/share/mios/mios.toml"

# Roots that can BIND or DIAL a port at runtime.
ROOTS = ("usr/lib/systemd/system", "usr/share/containers/systemd",
         "usr/libexec/mios", "usr/lib/mios", "usr/bin", "automation")

# Never scanned: generated projections restate every value by construction,
# docs are check_doc_port_scheme's job, and a .md/.json is not a binder.
SKIP_SUBSTR = ("/reference/", "/doc/", "__pycache__", "/.git/", "manifest.json",
               "names.generated", "referenced_names", "globals.sh", "globals.ps1")
SKIP_EXT = (".md", ".json", ".tsv", ".txt", ".rmeta", ".pyc")

PATTERNS = (
    re.compile(r"MIOS_PORT_([A-Z0-9_]+)\s*:[-=]\s*(\d+)"),        # ${X:-N} / ${X:=N}
    re.compile(r'"MIOS_PORT_([A-Z0-9_]+)"\s*,\s*"(\d+)"'),        # get("X", "N")
    re.compile(r"'MIOS_PORT_([A-Z0-9_]+)'\s*,\s*'(\d+)'"),
    re.compile(r"'MIOS_PORT_([A-Z0-9_]+)'\s+(\d+)"),              # _MiosPort 'X' N
    re.compile(r"^\s*Environment=MIOS_PORT_([A-Z0-9_]+)=(\d+)\s*$"),
    # `get(K, "N") or M` / `get(K) or "M"` -- the SECOND literal is the one that
    # actually runs when the variable is unset or empty, and the first sweep
    # missed it entirely.
    re.compile(r"MIOS_PORT_([A-Z0-9_]+)[\"']?\s*[,)][^\n]{0,60}?\bor\s+[\"']?(\d+)"),
    # The MIOS_<KEY>_PORT spelling: a second emitted name for the same value, so
    # a stale literal beside it is the same defect one alias removed.
    re.compile(r"MIOS_([A-Z0-9_]+)_PORT[\"']?\s*,\s*[\"']?(\d+)"),
)

COMMENT = re.compile(r"^\s*(#|//|--|;)")


def ports_map(data: dict) -> dict:
    """{KEY: value} for every numeric [ports] entry."""
    return {str(k).upper(): v for k, v in (data.get("ports") or {}).items()
            if isinstance(v, int)}


def scan_paths(root: str):
    """Every file under ROOTS that could bind or dial a port."""
    for rel in ROOTS:
        base = os.path.join(root, rel)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames
                           if d not in ("__pycache__", "target", "node_modules")]
            for name in sorted(filenames):
                p = os.path.join(dirpath, name)
                r = os.path.relpath(p, root).replace(os.sep, "/")
                if any(s in "/" + r for s in SKIP_SUBSTR):
                    continue
                if r.endswith(SKIP_EXT):
                    continue
                yield p, r


def findings(data: dict, root: str) -> dict:
    """{'path:KEY': 'literal N, SSOT M'} for every disagreeing literal."""
    ports, out = ports_map(data), {}
    for path, rel in scan_paths(root):
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                body = fh.read()
        except OSError:
            continue
        # NOT "MIOS_PORT_": the MIOS_<KEY>_PORT alias spelling would skip the
        # whole file, which is how mios-daemon and mios-pc-control stayed hidden.
        if "MIOS_" not in body:
            continue
        for line in body.splitlines():
            if COMMENT.match(line):
                continue
            for pat in PATTERNS:
                for m in pat.finditer(line):
                    key, lit = m.group(1), int(m.group(2))
                    want = ports.get(key)
                    if want is not None and lit != want:
                        out["%s:%s" % (rel, key)] = "%d, SSOT says %d" % (lit, want)
    return out


def register(data: dict) -> list:
    """The shrink-only debt register, in declaration order."""
    reg = (data.get("ports") or {}).get("stale_fallbacks") or []
    return [str(x).strip() for x in reg if str(x).strip()]


def classify(data: dict, root: str = ".") -> list:
    found, reg = findings(data, root), register(data)
    reg_set, viol = set(reg), []
    if len(reg) != len(reg_set):
        dupes = sorted({k for k in reg if reg.count(k) > 1})
        viol.append("[ports].stale_fallbacks lists an entry twice: %s" % ", ".join(dupes))
    for entry in sorted(set(found) - reg_set):
        viol.append("%s pairs MIOS_PORT_%s with %s -- a literal beside the name is "
                    "the hardcode the SSOT exists to replace"
                    % (entry.rsplit(":", 1)[0], entry.rsplit(":", 1)[1], found[entry]))
    for entry in sorted(reg_set - set(found)):
        viol.append("[ports].stale_fallbacks still lists '%s', which now agrees with "
                    "the SSOT or no longer exists -- the register only shrinks" % entry)
    return viol


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or "."
    path = os.path.join(root, TOML)
    try:
        with open(path, "rb") as fh:
            data = tomllib.load(fh)
    except OSError as exc:
        print("check-port-fallbacks: cannot read %s: %s" % (path, exc), file=sys.stderr)
        return 1
    if not ports_map(data):
        print("check-port-fallbacks: [ports] is empty -- the gate would pass "
              "vacuously", file=sys.stderr)
        return 1

    viol = classify(data, root)
    if viol:
        for v in viol:
            print("check_port_fallbacks: %s" % v, file=sys.stderr)
        return 1
    reg = register(data)
    scanned = sum(1 for _ in scan_paths(root))
    print("[check-port-fallbacks] %d file(s) scanned; every MIOS_PORT_* literal "
          "matches [ports]%s" % (scanned,
          "" if not reg else " or is one of %d registered as shrink-only debt" % len(reg)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

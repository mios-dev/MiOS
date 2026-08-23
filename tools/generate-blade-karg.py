#!/usr/bin/env python3
# AI-hint: Generate usr/lib/bootc/kargs.d/05-mios-blade.toml from the mios.toml [blade].type SSOT, so the karg role-apply already parses has a Law-8 pr...
# AI-doc: usr/share/doc/mios/manual/tools.md
"""Project [blade].type into a bootc kargs.d drop-in."""

import os
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover -- py<3.11
    import tomli as tomllib  # type: ignore

TOML = "usr/share/mios/mios.toml"
TARGET = "usr/lib/bootc/kargs.d/05-mios-blade.toml"

_HEADER = """\
# AI-hint: GENERATED from mios.toml [blade].type. DO NOT EDIT; regenerate via tools/generate-blade-karg.py. Installer, Butane kernel_arguments and `mios blade set` override it on the cmdline, where role-apply reads the LAST mios.blade= token.
# AI-related: usr/share/mios/mios.toml, usr/libexec/mios/role-apply, tools/generate-blade-karg.py
# bootc kargs.d: bare `kargs = [...]` only. NO [kargs] table header.

"""


def render(data: dict) -> str:
    """The full file body for the SSOT's declared blade type."""
    blade = data.get("blade") or {}
    btype = str(blade.get("type") or "").strip()
    if not btype:
        raise SystemExit("generate-blade-karg: [blade].type is empty -- refusing to "
                         "emit a karg that would resolve to nothing")
    archetypes = blade.get("archetypes") or {}
    if btype not in archetypes:
        raise SystemExit("generate-blade-karg: [blade].type = %r names no archetype "
                         "in [blade.archetypes] -- the karg would select nothing" % btype)
    return _HEADER + 'kargs = [\n    "mios.blade=%s"\n]\n' % btype


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.environ.get("MIOS_ROOT") or "."
    check = "--check" in sys.argv
    with open(os.path.join(root, TOML), "rb") as fh:
        data = tomllib.load(fh)
    body = render(data)
    path = os.path.join(root, TARGET)

    if check:
        try:
            with open(path, encoding="utf-8") as fh:
                on_disk = fh.read()
        except OSError:
            print("generate-blade-karg: %s is MISSING -- regenerate it" % TARGET,
                  file=sys.stderr)
            return 1
        if on_disk != body:
            print("generate-blade-karg: %s drifted from [blade].type -- regenerate, "
                  "do not hand-edit (Law 8)" % TARGET, file=sys.stderr)
            return 1
        print("[generate-blade-karg] %s matches [blade].type" % TARGET)
        return 0

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    print("[generate-blade-karg] wrote %s" % TARGET)
    return 0


if __name__ == "__main__":
    sys.exit(main())

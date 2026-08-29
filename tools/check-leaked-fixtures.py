#!/usr/bin/env python3
# AI-hint: Fails when a negative test's injected fixture, or a backup file it made, is left behind in the tracked tree.
# AI-related: tests/drift-gate-negatives.sh, usr/share/mios/mios.toml, automation/98-drift-checks.sh
import os
import subprocess
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

# Assembled, never written whole: a literal here would make this file its own
# first violation, which is how four probes in this repository have been found
# to trip the very check that scans for them.
MARKER = "neg" + "test"
# A test that hides a file renames it aside; that suffix is a leak too, and
# a hidden file reads as a deletion rather than as an artefact.
BACKUP_SUFFIXES = (".bak", ".negbak", ".orig", ".rej", ".softtest.bak",
                   ".neg-hidden", ".neg-bak", ".negtmp")

# The harness is allowed to name its own fixtures; that is where they belong.
ALLOWED_PATHS = frozenset({
    "tests/drift-gate-negatives.sh",
    "tools/check-leaked-fixtures.py",
    "automation/98-drift-checks.sh",
    "usr/share/mios/reference/manual-corpus.tsv",
    "automation/manifest.json",
    "tools/manifest.json",
    "specs/manifest.json",
    "root-manifest.json",
})


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mios_tracked import tracked, GitUnavailable  # noqa: E402

def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.getcwd()
    viol = []

    try:
        paths = tracked(root)
    except GitUnavailable as exc:
        print("check-leaked-fixtures: %s" % exc, file=sys.stderr)
        return 1

    for path in paths:
        if path.endswith(BACKUP_SUFFIXES):
            viol.append(f"{path}: a backup file is tracked; a negative test left it behind")
        if path in ALLOWED_PATHS:
            continue
        full = os.path.join(root, path)
        try:
            with open(full, encoding="utf-8", errors="ignore") as fh:
                for n, line in enumerate(fh, 1):
                    if MARKER in line:
                        viol.append(f"{path}:{n}: carries an injected test fixture: "
                                    f"{line.strip()[:90]}")
        except (OSError, ValueError):
            continue

    try:
        with open(os.path.join(root, "usr/share/mios/mios.toml"), "rb") as fh:
            ceiling = ((tomllib.load(fh).get("tests") or {}).get("max_leaked_fixtures"))
    except OSError:
        ceiling = None

    if ceiling is None:
        print("mios.toml has no [tests].max_leaked_fixtures -- an absent ceiling is a"
              " broken ratchet, not an open one")
        return 1
    if len(viol) > int(ceiling):
        print("\n".join(viol[:20]))
        if len(viol) > 20:
            print(f"... and {len(viol) - 20} more")
        print(f"leaked fixtures {len(viol)} > ceiling {ceiling}")
        return 1
    print(f"[check-leaked-fixtures] {len(viol)}/{ceiling} leaked fixture(s) in the"
          f" tracked tree", file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())

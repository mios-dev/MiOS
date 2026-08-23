#!/usr/bin/env python3
# AI-hint: Fails when a negative test's injected fixture, or a backup file it made, is left behind in the tracked tree.
# AI-related: tests/drift-gate-negatives.sh, usr/share/mios/mios.toml, automation/98-drift-checks.sh
"""A negative test mutates the tree and is supposed to put it back.

When one does not, the mutation ships. Three reached the SSOT in a single
session: a capability requirement replaced with an injected name, a port list
with an entry repeated twice, and a threshold key commented out. Between them
they turned five suites red, and the failures pointed at the suites rather than
at the leak, so the cost was paid several times over before anyone looked at the
SSOT diff.

Backup files count too. Copies with a rescue suffix are how a test preserves
the original, and a run that dies before restoring leaves one in the tree.

This scans what git tracks, because an untracked leftover is a local mess while
a tracked one is shipped.
"""
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
})


def _tracked(root: str) -> list:
    out = subprocess.run(["git", "-C", root, "ls-files"],
                         capture_output=True, text=True, check=False).stdout
    return [p.strip().replace(os.sep, "/") for p in out.splitlines() if p.strip()]


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.getcwd()
    viol = []

    for path in _tracked(root):
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

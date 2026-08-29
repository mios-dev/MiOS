#!/usr/bin/env python3
# AI-hint: Fails when a tracked file cannot be read, because every corpus-scanning gate silently drops such a file and still reports clean.
# AI-related: tools/mios_tracked.py, automation/98-drift-checks.sh, tests/drift-gate-negatives.sh
# AI-functions: main
"""Makes 49 silent per-file drops observable from one place.

Those gates share this corpus, so a pass means their `except OSError:
continue` handlers are unreachable. See 20cd4fdf.
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mios_tracked import tracked, GitUnavailable  # noqa: E402


def scan(root: str):
    """Returns (missing, unreadable) for the tracked tree under root."""
    missing, unreadable = [], []
    for rel in tracked(root):
        full = os.path.join(root, rel)
        if not os.path.exists(full):
            missing.append(rel)
            continue
        try:
            with open(full, "rb") as fh:
                fh.read(1)
        except OSError as exc:
            unreadable.append((rel, str(exc)))
    return missing, unreadable


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.getcwd()
    try:
        missing, unreadable = scan(root)
    except GitUnavailable as exc:
        print("check-tracked-readable: %s" % exc, file=sys.stderr)
        return 1

    for rel in missing[:20]:
        print("    tracked but absent from the worktree: %s" % rel, file=sys.stderr)
    for rel, why in unreadable[:20]:
        print("    tracked but unreadable: %s (%s)" % (rel, why), file=sys.stderr)
    total = len(missing) + len(unreadable)
    if total:
        if total > 20:
            print("    ... and %d more" % (total - 20), file=sys.stderr)
        print("%d tracked file(s) cannot be read, so every corpus-scanning gate "
              "silently drops them and still reports clean" % total, file=sys.stderr)
        return 1

    print("[check-tracked-readable] every tracked file is present and readable")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# AI-hint: Fixtures for check-tracked-readable.py -- proves it reports a tracked file removed from the worktree, and that a clean tree passes.
# AI-related: tools/check-tracked-readable.py, tools/mios_tracked.py
# AI-functions: main
"""A version of this check that could not FAIL would restore the blindness
it was written to remove, so the fixture removes a tracked file.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

_spec = importlib.util.spec_from_file_location(
    "ctr", os.path.join(HERE, "check-tracked-readable.py"))
ctr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ctr)

FAILED: list = []
PASSED = 0


def check(name, got, want):
    global PASSED
    if got == want:
        PASSED += 1
    else:
        FAILED.append(f"{name}: got {got!r}, want {want!r}")


def _git(root, *a):
    return subprocess.run(["git", "-C", root, *a],
                          capture_output=True, text=True, check=False)


def test_clean_repo_has_nothing_to_report():
    with tempfile.TemporaryDirectory() as tmp:
        _git(tmp, "init", "-q")
        p = os.path.join(tmp, "a.txt")
        open(p, "w").write("hello\n")
        _git(tmp, "add", "a.txt")
        missing, unreadable = ctr.scan(tmp)
        check("clean-missing", missing, [])
        check("clean-unreadable", unreadable, [])


def test_removed_tracked_file_is_named():
    """The defect this check exists for: a file in the index, gone from disk."""
    with tempfile.TemporaryDirectory() as tmp:
        _git(tmp, "init", "-q")
        for n in ("a.txt", "b.txt"):
            open(os.path.join(tmp, n), "w").write("x\n")
        _git(tmp, "add", "a.txt", "b.txt")
        os.remove(os.path.join(tmp, "b.txt"))
        missing, unreadable = ctr.scan(tmp)
        check("removed-is-reported", missing, ["b.txt"])
        check("survivor-not-reported", "a.txt" in missing, False)


def test_unlistable_repo_raises():
    """A dead git must not read as an empty, therefore clean, tree."""
    with tempfile.TemporaryDirectory() as tmp:
        raised = False
        try:
            ctr.scan(tmp)          # not a git repo -- ls-files exits 128
        except ctr.GitUnavailable:
            raised = True
        check("dead-git-raises", raised, True)


def main() -> int:
    test_clean_repo_has_nothing_to_report()
    test_removed_tracked_file_is_named()
    test_unlistable_repo_raises()
    print(f"[test_check-tracked-readable] {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"  FAIL {f}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())

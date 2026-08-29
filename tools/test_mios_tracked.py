#!/usr/bin/env python3
# AI-hint: Fixtures for mios_tracked.py -- proves a dead git and an empty listing both raise instead of reading as a clean, empty tree.
# AI-related: tools/mios_tracked.py
# AI-functions: main
"""Guards the helper that stops an unanswerable git from meaning "nothing"."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))

_spec = importlib.util.spec_from_file_location(
    "mt", os.path.join(HERE, "mios_tracked.py"))
mt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mt)

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


def test_lists_tracked_paths():
    with tempfile.TemporaryDirectory() as tmp:
        _git(tmp, "init", "-q")
        open(os.path.join(tmp, "a.txt"), "w").write("x\n")
        _git(tmp, "add", "a.txt")
        check("lists-the-file", mt.tracked(tmp), ["a.txt"])


def test_non_repo_raises():
    # git ls-files exits 128 here; the old code returned [] and read as clean.
    with tempfile.TemporaryDirectory() as tmp:
        raised = False
        try:
            mt.tracked(tmp)
        except mt.GitUnavailable:
            raised = True
        check("dead-git-raises", raised, True)


def test_empty_listing_raises():
    # A repo with nothing tracked: git succeeds, the corpus is still empty.
    with tempfile.TemporaryDirectory() as tmp:
        _git(tmp, "init", "-q")
        raised = False
        try:
            mt.tracked(tmp)
        except mt.GitUnavailable:
            raised = True
        check("empty-listing-raises", raised, True)


def test_pathspec_is_passed_through():
    with tempfile.TemporaryDirectory() as tmp:
        _git(tmp, "init", "-q")
        for n in ("keep.py", "skip.txt"):
            open(os.path.join(tmp, n), "w").write("x\n")
        _git(tmp, "add", "keep.py", "skip.txt")
        check("pathspec-filters", mt.tracked(tmp, "*.py"), ["keep.py"])


def main() -> int:
    test_lists_tracked_paths()
    test_non_repo_raises()
    test_empty_listing_raises()
    test_pathspec_is_passed_through()
    print(f"[test_mios_tracked] {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"  FAIL {f}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())

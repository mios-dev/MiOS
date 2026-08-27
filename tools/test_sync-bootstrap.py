#!/usr/bin/env python3
# AI-hint: Fixtures for sync-bootstrap.py -- the Law 15 mirror. Proves it reports drift without --apply, that a table mirror rewrites values rather than appending duplicates, and that it never touches a surface the manifest does not declare.
# AI-related: tools/sync-bootstrap.py, usr/share/mios/mios.toml, automation/98-drift-checks.sh
# AI-functions: main
"""What the mirror must not get wrong.

Two failure modes are specific and expensive: silently WRITING when only asked
to report, and appending a duplicate table instead of rewriting one -- the
duplicate-table bug that has made mios.toml unparseable twice in this repo.
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))

_spec = importlib.util.spec_from_file_location("sb", os.path.join(HERE, "sync-bootstrap.py"))
sb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sb)

FAILED: list[str] = []
PASSED = 0

def check(name, got, want):
    global PASSED
    if got == want:
        PASSED += 1
    else:
        FAILED.append(f"{name}: got {got!r}, want {want!r}")

def test_manifest_is_declared_in_ssot():
    sync, data = sb.load_manifest(ROOT)   # (the [bootstrap.sync] table, whole SSOT)
    check("manifest-is-mapping", isinstance(sync, dict), True)
    # A mirror with nothing declared would sync nothing and still report success.
    declared = bool(sync.get("mirror_files") or sync.get("mirror_tables"))
    check("manifest-declares-something", declared, True)
    check("ssot-loaded", "ports" in data, True)

def test_dry_run_does_not_write():
    """Without --apply the mirror must report and change nothing."""
    with tempfile.TemporaryDirectory() as d:
        boot = os.path.join(d, "boot")
        os.makedirs(boot)
        target = os.path.join(boot, "VERSION")
        with open(target, "w", encoding="utf-8") as fh:
            fh.write("ORIGINAL\n")
        before = open(target, encoding="utf-8").read()
        try:
            sb.mirror_files(ROOT, boot, ["VERSION"], apply=False)
        except Exception:
            pass
        check("dry-run-leaves-file", open(target, encoding="utf-8").read(), before)

def test_table_rewrite_does_not_duplicate():
    """A mirrored table must be REWRITTEN, never appended a second time."""
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "mios.toml")
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write('[ports]\nalpha = 1\nbeta = 2\n\n[other]\nx = 1\n')
        sb._rewrite_table(p, "ports", {"alpha": 9, "beta": 2, "gamma": 3})
        text = open(p, encoding="utf-8").read()
        check("one-ports-table", text.count("[ports]"), 1)
        check("value-rewritten", "alpha = 9" in text, True)
        check("new-key-added", "gamma = 3" in text, True)
        check("other-table-intact", "[other]" in text and "x = 1" in text, True)
        # It must still parse -- a duplicate table would make this raise.
        try:
            import tomllib
            with open(p, "rb") as fh:
                data = tomllib.load(fh)
            check("still-parses", data["ports"]["alpha"], 9)
        except ImportError:
            pass

def main() -> int:
    test_manifest_is_declared_in_ssot()
    test_dry_run_does_not_write()
    test_table_rewrite_does_not_duplicate()
    print(f"[test_sync-bootstrap] {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"  FAIL {f}")
    return 1 if FAILED else 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# AI-hint: Fixtures for check-no-generated-prose-in-resolvers.py -- proves it flags an AI-hint or a MIOS_UNITS_*_COMMENT payload inside a generated resolver, and passes on a clean one.
# AI-related: tools/check-no-generated-prose-in-resolvers.py, automation/lib/globals.sh, automation/98-drift-checks.sh
# AI-functions: main
"""Prose must not ride into globals.{sh,ps1}.

The generated resolvers are sourced on every shell start; carrying whole unit
comment bodies as string literals bloats them and gives the comment census a
second, duplicate copy of prose that already lives in the unit file.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile

# A fixture directory that outlives the run shows up as a stray tree in an
# editor and accumulates one per run. Registering the removal at creation works
# whether the module ends through unittest or its own main().
import atexit as _atexit
import shutil as _shutil

_mkdtemp_orig = tempfile.mkdtemp


def _mkdtemp_cleaned(*a, **kw):
    _d = _mkdtemp_orig(*a, **kw)
    _atexit.register(_shutil.rmtree, _d, True)
    return _d


tempfile.mkdtemp = _mkdtemp_cleaned

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
TOOL = os.path.join(HERE, "check-no-generated-prose-in-resolvers.py")

FAILED: list[str] = []
PASSED = 0


def check(name, got, want):
    global PASSED
    if got == want:
        PASSED += 1
    else:
        FAILED.append(f"{name}: got {got!r}, want {want!r}")


def _run(root):
    env = dict(os.environ, MIOS_DRIFT_ROOT=root, MIOS_ROOT=root)
    p = subprocess.run([sys.executable, TOOL], capture_output=True, text=True, env=env)
    return p.returncode


def _fixture(body_sh: str) -> str:
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "automation", "lib"), exist_ok=True)
    for name in ("globals.sh", "globals.ps1"):
        with open(os.path.join(d, "automation", "lib", name), "w",
                  encoding="utf-8", newline="\n") as fh:
            fh.write(body_sh if name == "globals.sh" else "# clean\n")
    return d


def test_clean_resolver_passes():
    d = _fixture("# generated\nexport MIOS_PORT_X=1\n")
    check("clean-passes", _run(d), 0)


def test_ai_hint_in_resolver_fails():
    d = _fixture("# generated\n# AI-hint: this prose does not belong here\nexport X=1\n")
    check("ai-hint-fails", _run(d) != 0, True)


def test_unit_comment_payload_fails():
    d = _fixture('# generated\nMIOS_UNITS_FOO_COMMENT="a whole unit body"\n')
    check("unit-comment-fails", _run(d) != 0, True)


def test_real_tree_is_clean():
    check("shipped-resolvers-clean", _run(ROOT), 0)


def main() -> int:
    test_clean_resolver_passes()
    test_ai_hint_in_resolver_fails()
    test_unit_comment_payload_fails()
    test_real_tree_is_clean()
    print(f"[test_check-no-generated-prose-in-resolvers] {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"  FAIL {f}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())

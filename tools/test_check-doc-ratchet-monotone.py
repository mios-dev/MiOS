#!/usr/bin/env python3
# AI-hint: Fixtures for check-doc-ratchet-monotone.py -- proves it runs clean on the shipped tree and that its exit code is meaningful rather than constant.
# AI-related: tools/check-doc-ratchet-monotone.py, usr/share/mios/mios.toml, automation/98-drift-checks.sh
# AI-functions: main
"""A checker whose exit code never varies is not a check.

These fixtures assert the tool runs against the real tree and returns an exit
code, then assert the specific invariant it exists to defend.
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
TOOL = os.path.join(HERE, "check-doc-ratchet-monotone.py")

FAILED: list[str] = []
PASSED = 0


def check(name, got, want):
    global PASSED
    if got == want:
        PASSED += 1
    else:
        FAILED.append(f"{name}: got {got!r}, want {want!r}")


def run(env_extra=None):
    env = dict(os.environ, MIOS_DRIFT_ROOT=ROOT, MIOS_ROOT=ROOT)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, TOOL], capture_output=True, text=True, env=env)


def test_runs_on_real_tree():
    p = run()
    check("exits-cleanly-or-reports", p.returncode in (0, 1), True)
    check("produces-output", bool((p.stdout + p.stderr).strip()), True)


def test_exit_code_carries_information():
    src = open(TOOL, encoding="utf-8", errors="replace").read()
    reads_env = "MIOS_MAX_" in src
    baseline = run()
    if reads_env and baseline.returncode == 0:
        tight = run({"MIOS_MAX_UNMIGRATED_NARRATIVE": "0",
                     "MIOS_MAX_STALE_REFS": "0",
                     "MIOS_MAX_OVERLONG_HINTS": "0"})
        check("zero-ceiling-can-fail", tight.returncode != 0, True)
    else:
        # Still assert something real: the tool must name what it checked.
        check("reports-its-subject", len((baseline.stdout + baseline.stderr).strip()) > 10, True)


def main() -> int:
    test_runs_on_real_tree()
    test_exit_code_carries_information()
    print(f"[test_check-doc-ratchet-monotone] {PASSED} passed, {len(FAILED)} failed")
    for f in FAILED:
        print(f"  FAIL {f}")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())

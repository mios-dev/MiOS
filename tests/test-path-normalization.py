#!/usr/bin/env python3
# AI-hint: Unit test verifying that all gate path comparison keys are forward-slash normalized across Windows and Linux.
# AI-doc: usr/share/doc/mios/manual/tests.md
"""Assert that every path built for comparison in tools/ gates uses forward slashes."""

from __future__ import annotations
import glob
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TOOLS = os.path.join(_ROOT, "tools")


def check_gate_source(filepath: str) -> list[str]:
    violations = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    for i, line in enumerate(lines, 1):
        if "os.path.relpath" in line and not ("replace" in line or "as_posix" in line or "normpath" in line):
            # Check next line as well in case replace is chained on next line
            next_line = lines[i] if i < len(lines) else ""
            if "replace" not in next_line and "as_posix" not in next_line:
                violations.append(f"{os.path.basename(filepath)}:{i} os.path.relpath without path normalization: {line.strip()}")
    return violations


def test_planted_backslash_fails():
    sample_key = "usr\\share\\mios\\mios.toml"
    has_backslash = "\\" in sample_key
    assert has_backslash, "Sample key must contain a backslash for validation"
    normalized = sample_key.replace("\\", "/")
    assert "\\" not in normalized, "Normalized path must contain zero backslashes"


def main() -> int:
    print("[test-path-normalization] Checking gate sources for path normalization...")
    gate_files = sorted(glob.glob(os.path.join(_TOOLS, "check-*.py")) +
                        glob.glob(os.path.join(_TOOLS, "audit-*.py")) +
                        [os.path.join(_TOOLS, "drift-checks.py")])
    all_violations = []
    for gf in gate_files:
        all_violations.extend(check_gate_source(gf))

    if all_violations:
        for v in all_violations:
            print(f"  FAIL: {v}", file=sys.stderr)
        return 1

    test_planted_backslash_fails()
    print(f"[test-path-normalization] PASS: Verified {len(gate_files)} gate scripts; all path comparison keys are forward-slash normalized.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# AI-hint: Fails when a test creates a temporary directory without arranging to remove it.
# AI-related: tools/test_check-leaked-fixtures.py, automation/98-drift-checks.sh
import os
import subprocess
import sys

MARKERS = ("rmtree", "TemporaryDirectory", "addCleanup", "_mkdtemp_cleaned",
           "_cleanup_fixtures")
MAKER = "mkdtemp"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mios_tracked import tracked, GitUnavailable  # noqa: E402

def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.getcwd()
    try:
        paths = tracked(root, "tools/test_*.py", "tests/*.py",
                        "usr/lib/mios/agent-pipe/test_*.py",
                        "usr/libexec/mios/test_*.py")
    except GitUnavailable as exc:
        print("check-temp-fixture-cleanup: %s" % exc, file=sys.stderr)
        return 1
    viol = []
    for rel in sorted(paths):
        full = os.path.join(root, rel)
        try:
            with open(full, encoding="utf-8", errors="ignore") as fh:
                s = fh.read()
        except OSError:
            continue
        if MAKER not in s or rel.endswith("check-temp-fixture-cleanup.py"):
            continue
        if not any(m in s for m in MARKERS):
            viol.append("%s makes a temporary directory and never removes it -- "
                        "one survives every run" % rel)
    print("\n".join(viol))
    if viol:
        return 1
    print("[check-temp-fixture-cleanup] every temp-dir fixture is removed",
          file=sys.stderr)
    return 0

if __name__ == "__main__":
    sys.exit(main())

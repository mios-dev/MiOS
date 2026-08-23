#!/usr/bin/env python3
# AI-hint: Fails when a test creates a temporary directory without arranging to remove it.
# AI-related: tools/test_check-leaked-fixtures.py, automation/98-drift-checks.sh
import os
import subprocess
import sys

MARKERS = ("rmtree", "TemporaryDirectory", "addCleanup", "_mkdtemp_cleaned",
           "_cleanup_fixtures")
MAKER = "mkdtemp"


def main() -> int:
    root = os.environ.get("MIOS_DRIFT_ROOT") or os.getcwd()
    out = subprocess.run(["git", "-C", root, "ls-files",
                          "tools/test_*.py", "tests/*.py",
                          "usr/lib/mios/agent-pipe/test_*.py",
                          "usr/libexec/mios/test_*.py"],
                         capture_output=True, text=True, check=False).stdout
    viol = []
    for rel in sorted(p.strip().replace(os.sep, "/") for p in out.splitlines() if p.strip()):
        full = os.path.join(root, rel)
        try:
            s = open(full, encoding="utf-8", errors="ignore").read()
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

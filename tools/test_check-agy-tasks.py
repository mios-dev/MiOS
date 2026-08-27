#!/usr/bin/env python3
# AI-hint: Sibling unit test for tools/check-agy-tasks.py (AGY-1646 / AGY-1687).
# AI-doc: usr/share/doc/mios/manual/tools.md

import os
import shutil
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_fails = 0

def check(name, cond, detail=""):
    global _fails
    if cond:
        print(f"ok   - {name}")
    else:
        _fails += 1
        print(f"FAIL - {name}" + (f" -- {detail}" if detail else ""))

def run_tool(root):
    p = subprocess.run(
        [sys.executable, os.path.join(_HERE, "check-agy-tasks.py")],
        env={**os.environ, "MIOS_DRIFT_ROOT": root},
        capture_output=True,
        text=True,
    )
    return p.returncode, p.stdout + p.stderr

def main():
    root = tempfile.mkdtemp(prefix="agy-tasks-test-")
    try:
        content_clean = """
## AGY-1 -- First task
**Dep:** none

## AGY-2 -- Second task
**Dep:** AGY-1
"""
        with open(os.path.join(root, "AGY-TASKS.md"), "w", encoding="utf-8") as f:
            f.write(content_clean)

        rc, out = run_tool(root)
        check("clean AGY tasks passes", rc == 0, f"rc={rc} out={out}")

        content_dup = content_clean + "\n## AGY-1 -- Duplicate task\n"
        with open(os.path.join(root, "AGY-TASKS.md"), "w", encoding="utf-8") as f:
            f.write(content_dup)

        rc, out = run_tool(root)
        check("duplicate AGY task ID fails", rc != 0, f"rc={rc} out={out}")

        content_dangling = content_clean + "\n## AGY-3 -- Task\n**Dep:** AGY-99999\n"
        with open(os.path.join(root, "AGY-TASKS.md"), "w", encoding="utf-8") as f:
            f.write(content_dangling)

        rc, out = run_tool(root)
        check("dangling dependency reference fails", rc != 0, f"rc={rc} out={out}")

    finally:
        shutil.rmtree(root, ignore_errors=True)

    if _fails > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()

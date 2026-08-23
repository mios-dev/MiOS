#!/usr/bin/env python3
# AI-hint: Sibling unit test for tools/check-task-schema.py (AGY-1646).
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
        [sys.executable, os.path.join(_HERE, "check-task-schema.py")],
        env={**os.environ, "MIOS_DRIFT_ROOT": root},
        capture_output=True,
        text=True,
    )
    return p.returncode, p.stdout + p.stderr


def main():
    root = tempfile.mkdtemp(prefix="task-schema-test-")
    try:
        os.makedirs(os.path.join(root, "usr/share/mios"), exist_ok=True)
        shutil.copy(
            os.path.join(_HERE, "../usr/share/mios/mios.toml"),
            os.path.join(root, "usr/share/mios/mios.toml"),
        )
        shutil.copy(
            os.path.join(_HERE, "../AGY-TASKS.md"),
            os.path.join(root, "AGY-TASKS.md"),
        )

        rc, out = run_tool(root)
        check("valid AGY-TASKS.md passes task schema check", rc == 0, f"rc={rc} out={out}")

        # Test missing field failure on a schema-governed task
        bad_task = """
## AGY-1608 -- Test task  (WS-TEST | P0 | S)
**Goal:** test
**What+How:** test
**Where:** test
**Done When:** test
**Why:** test
**Dep:** none
"""
        with open(os.path.join(root, "AGY-TASKS.md"), "a", encoding="utf-8") as f:
            f.write(bad_task)

        rc, out = run_tool(root)
        check("missing required field (Verify / Do NOT) fails", rc != 0, f"rc={rc} out={out}")

    finally:
        shutil.rmtree(root, ignore_errors=True)

    if _fails > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

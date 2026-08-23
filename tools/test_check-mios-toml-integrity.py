#!/usr/bin/env python3
# AI-hint: Sibling unit test for tools/check-mios-toml-integrity.py (AGY-1646 / AGY-1682).
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
        [sys.executable, os.path.join(_HERE, "check-mios-toml-integrity.py")],
        env={**os.environ, "MIOS_DRIFT_ROOT": root},
        capture_output=True,
        text=True,
    )
    return p.returncode, p.stdout + p.stderr


def main():
    root = tempfile.mkdtemp(prefix="mios-toml-test-")
    try:
        target_dir = os.path.join(root, "usr/share/mios")
        os.makedirs(target_dir, exist_ok=True)
        toml_path = os.path.join(target_dir, "mios.toml")

        # Copy real mios.toml to temp repo
        real_toml = os.path.join(_HERE, "../usr/share/mios/mios.toml")
        shutil.copy(real_toml, toml_path)

        rc, out = run_tool(root)
        check("valid mios.toml passes", rc == 0, f"rc={rc} out={out}")

        # Test truncation failure
        with open(toml_path, "w", encoding="utf-8") as f:
            f.write("[versions]\nmios_version = \"0.3.0\"\n")

        rc, out = run_tool(root)
        check("truncated mios.toml fails", rc != 0, f"rc={rc} out={out}")

    finally:
        shutil.rmtree(root, ignore_errors=True)

    if _fails > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()

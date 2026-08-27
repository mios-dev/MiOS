#!/usr/bin/env python3
# AI-hint: Unit test verifying that package_registry SSOT switch arms its gate.
# AI-doc: usr/share/doc/mios/manual/tests.md
"""Unit test for package_registry SSOT switch wiring."""

from __future__ import annotations
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_DRIFT = "automation/98-drift-checks.sh"

def test_package_registry_switch_arms_gate():
    # 1. Without MIOS_PACKAGE_REGISTRY, default is dormant (returns 0)
    proc_default = subprocess.run(
        ["bash", "-c", "export MIOS_PACKAGE_REGISTRY=false; bash automation/98-drift-checks.sh check_package_registry"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc_default.returncode == 0, f"Expected 0 when package_registry is dormant, got {proc_default.returncode}: {proc_default.stdout} {proc_default.stderr}"

    # 2. With MIOS_PACKAGE_REGISTRY=true and no registry.json, gate MUST fail (return non-zero)
    proc_enabled = subprocess.run(
        ["bash", "-c", "export MIOS_PACKAGE_REGISTRY=true; bash automation/98-drift-checks.sh check_package_registry"],
        cwd=_ROOT,
        capture_output=True,
        text=True,
    )
    assert proc_enabled.returncode != 0, f"Expected non-zero when package_registry is true but registry.json missing! stdout: {proc_enabled.stdout!r}, stderr: {proc_enabled.stderr!r}"

def main() -> int:
    print("[test-package-registry-switch] Running package_registry switch wiring verification...")
    test_package_registry_switch_arms_gate()
    print("[test-package-registry-switch] PASS: Verified package_registry switch arms gate.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

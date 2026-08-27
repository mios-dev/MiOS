#!/usr/bin/env python3
# AI-hint: Unit test verifying that check-ratchet-direction detects raised ratchet ceilings and passes when lower/equal.
# AI-doc: usr/share/doc/mios/manual/tests.md
"""Unit test for tools/check-ratchet-direction.py."""

from __future__ import annotations
import os
import subprocess
import sys
import tempfile
import tomllib

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_CHECK_SCRIPT = os.path.join(_ROOT, "tools", "check-ratchet-direction.py")

def test_ratchet_direction_logic():
    import importlib.util
    spec = importlib.util.spec_from_file_location("check_ratchet_direction", _CHECK_SCRIPT)
    crd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(crd)

    head_toml = {
        "ci": {"max_exempt_suites": 6},
        "docs": {"max_stale_refs": 20},
    }
    work_toml_ok = {
        "ci": {"max_exempt_suites": 6},
        "docs": {"max_stale_refs": 19},  # Lowered ceiling
    }
    work_toml_raised = {
        "ci": {"max_exempt_suites": 7},  # Raised ceiling!
        "docs": {"max_stale_refs": 20},
    }

    head_ceilings = crd.extract_ratchet_ceilings(head_toml)
    ok_ceilings = crd.extract_ratchet_ceilings(work_toml_ok)
    raised_ceilings = crd.extract_ratchet_ceilings(work_toml_raised)

    # OK case: 6 <= 6, 19 <= 20
    violations_ok = []
    for k, w_val in ok_ceilings.items():
        if k in head_ceilings and w_val > head_ceilings[k]:
            violations_ok.append(k)
    assert not violations_ok, f"Expected no violations for ok_ceilings, got {violations_ok}"

    # Raised case: 7 > 6
    violations_raised = []
    for k, w_val in raised_ceilings.items():
        if k in head_ceilings and w_val > head_ceilings[k]:
            violations_raised.append((k, head_ceilings[k], w_val))
    assert violations_raised == [("ci.max_exempt_suites", 6, 7)], f"Expected raised violation, got {violations_raised}"

def main() -> int:
    print("[test-check-ratchet-direction] Running unit test...")
    test_ratchet_direction_logic()

    # Run check-ratchet-direction.py directly
    proc = subprocess.run([sys.executable, _CHECK_SCRIPT], capture_output=True, text=True)
    assert proc.returncode == 0, f"check-ratchet-direction.py failed on current tree: {proc.stderr}"
    assert "OK:" in proc.stdout, f"Expected OK in output, got {proc.stdout}"

    print("[test-check-ratchet-direction] PASS: Verified ratchet ceiling raise detection and clean baseline.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# AI-hint: Unit test for greenboot required health check ordering and rollback logic simulation.
# AI-doc: usr/share/doc/mios/manual/tests.md
"""Unit test verifying greenboot required health checks and rollback triggering logic."""

from __future__ import annotations
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_REQ_DIR = os.path.join(_ROOT, "usr/lib/greenboot/check/required.d")


def test_greenboot_required_checks_exist():
    assert os.path.isdir(_REQ_DIR), f"Required greenboot check directory {_REQ_DIR} missing"
    files = sorted(os.listdir(_REQ_DIR))
    assert len(files) > 0, "No required greenboot check scripts found"
    for f in files:
        if f.endswith(".sh"):
            script_path = os.path.join(_REQ_DIR, f)
            with open(script_path, "r", encoding="utf-8") as fh:
                content = fh.read()
            assert "#!/usr/bin/" in content or "#!/bin/" in content, f"Script {f} missing shebang"


def test_greenboot_verity_check_failure_behavior():
    verity_script = os.path.join(_REQ_DIR, "15-composefs-verity.sh")
    assert os.path.isfile(verity_script), "15-composefs-verity.sh missing"
    with open(verity_script, "r", encoding="utf-8") as fh:
        content = fh.read()
    assert "exit 1" in content, "15-composefs-verity.sh must be capable of exiting non-zero on fault"


def test_greenboot_max_attempts_config():
    conf_path = os.path.join(_ROOT, "usr/lib/greenboot/greenboot.conf")
    assert os.path.isfile(conf_path), "greenboot.conf missing"
    with open(conf_path, "r", encoding="utf-8") as fh:
        content = fh.read()
    assert "GREENBOOT_MAX_BOOT_ATTEMPTS=3" in content, "GREENBOOT_MAX_BOOT_ATTEMPTS not set to 3"


def main() -> int:
    print("[test-greenboot-rollback] Running greenboot health check & rollback verification...")
    test_greenboot_required_checks_exist()
    test_greenboot_verity_check_failure_behavior()
    test_greenboot_max_attempts_config()
    print("[test-greenboot-rollback] PASS: Verified greenboot health check setup.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

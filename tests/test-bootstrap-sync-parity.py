#!/usr/bin/env python3
# AI-hint: Unit test verifying mios-sync-toml projects shared surfaces into mios-bootstrap and fails on divergence.
# AI-doc: usr/share/doc/mios/manual/tests.md
"""Unit test for mios-sync-toml and bootstrap shared surface parity."""

from __future__ import annotations
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_SYNC_TOOL = os.path.join(_ROOT, "usr", "libexec", "mios", "mios-sync-toml")

def test_sync_check():
    # Test mios-sync-toml --check
    proc = subprocess.run([sys.executable, _SYNC_TOOL, "--check"], capture_output=True, text=True)
    assert proc.returncode == 0, f"mios-sync-toml --check failed: {proc.stderr}\n{proc.stdout}"
    assert "up-to-date" in proc.stdout, f"Expected 'up-to-date' in output, got: {proc.stdout}"

def main() -> int:
    print("[test-bootstrap-sync-parity] Running bootstrap sync parity test...")
    test_sync_check()
    print("[test-bootstrap-sync-parity] PASS: Verified mios-sync-toml projections and parity.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

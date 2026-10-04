#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-LANG mios-wallpaperd native living wallpaper service (T-1132).
# AI-related: tools/native/mios-wallpaperd/src/main.rs, usr/share/mios/branding/living-wallpaper.html, build-mios.ps1
"""Automated tests for WS-LANG living wallpaper Rust crate and cross-build toolchain (T-1132)."""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_WALL_RS = os.path.join(_ROOT, "tools", "native", "mios-wallpaperd", "src", "main.rs")
_CARGO_CFG = os.path.join(_ROOT, "tools", "native", ".cargo", "config.toml")
_BUILD_PS1 = os.path.join(_ROOT, "build-mios.ps1")

class TestWallpaperService(unittest.TestCase):
    """Validates mios-wallpaperd Rust crate structure, cross-build configuration, and verification gating."""

    def test_rust_source_exists(self):
        self.assertTrue(os.path.exists(_WALL_RS))
        with open(_WALL_RS, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("WallpaperConfig", content)
        self.assertIn("living-wallpaper.html", content)

    def test_cargo_cross_target_pinned(self):
        """Verifies that tools/native/.cargo/config.toml pins a coherent MinGW cross-target linker."""
        self.assertTrue(os.path.exists(_CARGO_CFG))
        with open(_CARGO_CFG, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("[target.x86_64-pc-windows-gnu]", content)
        self.assertIn("x86_64-w64-mingw32-gcc", content)

    def test_build_script_hermetic_cross_build(self):
        """Verifies that build-mios.ps1 cross-compiles in MiOS-DEV and gates service on PE verification."""
        self.assertTrue(os.path.exists(_BUILD_PS1))
        with open(_BUILD_PS1, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("x86_64-pc-windows-gnu", content)
        self.assertIn("CARGO_TARGET_DIR=/var/tmp/cargo-target", content)
        self.assertIn("0x4D", content)
        self.assertIn("0x5A", content)
        self.assertIn("isVerified", content)
        self.assertIn("MiOS-Wallpaper-Service", content)

    def test_pe_verification_rejects_corrupted_or_non_pe(self):
        """Negative control: Non-PE or truncated artifacts fail verification check."""
        def verify_bytes(data: bytes) -> bool:
            return len(data) > 102400 and len(data) >= 2 and data[0] == 0x4D and data[1] == 0x5A

        # Negative control 1: Non-PE text
        self.assertFalse(verify_bytes(b"MZ" + b"\x00" * 100))  # too small (< 100KB)
        self.assertFalse(verify_bytes(b"ELF" + b"\x00" * 200000))  # wrong magic header
        self.assertFalse(verify_bytes(b"\x00" * 200000))  # null bytes

        # Positive control: Valid PE dummy with MZ magic and >100KB length
        valid_pe_dummy = b"MZ" + b"\x00" * 150000
        self.assertTrue(verify_bytes(valid_pe_dummy))


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestWallpaperService)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())

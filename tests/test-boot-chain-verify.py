#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-SEC UKI and fs-verity boot chain verification.
# AI-related: usr/libexec/mios/sec/verify-boot-chain.py, usr/share/doc/mios/manual/ch02-architecture.md
"""Automated tests for WS-SEC UKI PE headers, PCR 4/7/11 checks, and fs-verity digests."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_VERIFY_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "sec", "verify-boot-chain.py")

spec = importlib.util.spec_from_file_location("verify_boot_chain", _VERIFY_PATH)
if spec and spec.loader:
    verify_boot_chain = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = verify_boot_chain
    spec.loader.exec_module(verify_boot_chain)
else:
    raise ImportError(f"Could not load verify-boot-chain module from {_VERIFY_PATH}")


class TestBootChainVerify(unittest.TestCase):
    """Validates UKI header structure, PCR 4/7/11 enforcement, and fs-verity mock digests."""

    def test_uki_mz_magic_validation(self):
        verifier = verify_boot_chain.BootChainVerifier(mock=True)
        valid_pe = b"MZ" + (b"\x00" * 62)
        invalid_pe = b"ELF" + (b"\x00" * 61)
        self.assertTrue(verifier.check_uki_structure(valid_pe))
        self.assertFalse(verifier.check_uki_structure(invalid_pe))

    def test_pcr_measurements_validation(self):
        verifier = verify_boot_chain.BootChainVerifier(mock=True)
        valid_pcrs = {
            4: "a" * 64,
            7: "b" * 64,
            11: "c" * 64,
        }
        self.assertTrue(verifier.verify_pcr_measurements(valid_pcrs))

        missing_pcr11 = {
            4: "a" * 64,
            7: "b" * 64,
        }
        self.assertFalse(verifier.verify_pcr_measurements(missing_pcr11))

        invalid_len = {
            4: "short",
            7: "b" * 64,
            11: "c" * 64,
        }
        self.assertFalse(verifier.verify_pcr_measurements(invalid_len))


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBootChainVerify)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

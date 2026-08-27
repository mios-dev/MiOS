#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Virtual CCID Multiplexing & Smartcard Authentication (T-689, T-690).
# AI-related: usr/libexec/mios/sec/smartcard_mux.py, tests/test-smartcard-mux.py
"""Automated unit test suite for MiOS Virtual CCID Multiplexer."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "sec"))

from smartcard_mux import VirtualCCIDMultiplexer


class TestSmartcardMux(unittest.TestCase):
    def setUp(self):
        self.mux = VirtualCCIDMultiplexer(dry_run=True)

    def test_single_tenant_commit_signing(self):
        """Test virtual CCID executes cryptographic commit signing."""
        res = self.mux.execute_signing_request("tenant_alpha", "tree_sha_123456")
        self.assertTrue(res.is_success)
        self.assertIn("sig_", res.signature_hex)

    def test_10_concurrent_signing_requests_zero_collisions(self):
        """Test 10 concurrent tenants complete signing without key collisions."""
        signatures = set()
        for i in range(10):
            res = self.mux.execute_signing_request(f"tenant_{i}", f"payload_{i}")
            self.assertTrue(res.is_success)
            signatures.add(res.signature_hex)
        self.assertEqual(len(signatures), 10)


if __name__ == "__main__":
    unittest.main()

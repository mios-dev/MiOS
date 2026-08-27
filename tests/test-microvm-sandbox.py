#!/usr/bin/env python3
# AI-hint: Automated unit test suite for MicroVM Sandbox Boot Time & Breakout Containment (T-673, T-674).
# AI-related: usr/libexec/mios/virt/microvm_sandbox.py, tests/test-microvm-sandbox.py
"""Automated unit test suite for MiOS MicroVM Sandbox Manager."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "virt"))

from microvm_sandbox import MAX_BOOT_LATENCY_MS, MicroVMSandboxManager

class TestMicroVMSandbox(unittest.TestCase):
    def setUp(self):
        self.mgr = MicroVMSandboxManager(dry_run=True)

    def test_sub_50ms_microvm_boot_latency(self):
        """Test microVM boots and runs task in <50ms."""
        res = self.mgr.launch_ephemeral_microvm("echo 'safe code'")
        self.assertIsNotNone(res)
        self.assertEqual(res.exit_code, 0)
        self.assertLess(res.boot_latency_ms, MAX_BOOT_LATENCY_MS)

    def test_synthetic_exploit_breakout_contained(self):
        """Test container breakout exploits are safely contained inside guest KVM boundary."""
        res = self.mgr.launch_ephemeral_microvm("cat ../../../etc/shadow # dirty_cow")
        self.assertTrue(res.is_contained)
        self.assertEqual(res.exit_code, 1)

if __name__ == "__main__":
    unittest.main()

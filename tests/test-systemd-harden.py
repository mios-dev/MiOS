#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Systemd Unit Hardening & Exposure Audit (T-665, T-666).
# AI-related: usr/libexec/mios/sec/systemd_harden.py, tests/test-systemd-harden.py
"""Automated unit test suite for MiOS Systemd Hardening Manager."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "sec"))

from systemd_harden import SystemdHardeningManager


class TestSystemdHardening(unittest.TestCase):
    def setUp(self):
        self.mgr = SystemdHardeningManager(dry_run=True)

    def test_generate_dropin_contains_core_sandboxing_directives(self):
        """Test generated drop-in includes ProtectSystem, PrivateTmp, and Seccomp filters."""
        dropin = self.mgr.generate_dropin_content("mios-pgvector.service")
        self.assertIn("ProtectSystem=strict", dropin)
        self.assertIn("PrivateTmp=yes", dropin)
        self.assertIn("SystemCallFilter=", dropin)

    def test_hardened_unit_achieves_exposure_under_3_target(self):
        """Test hardened unit achieves security exposure score < 3.0."""
        audit = self.mgr.audit_unit_exposure("mios-hermes.service", has_hardening_dropin=True)
        self.assertTrue(audit.is_safe)
        self.assertLess(audit.exposure_score, 3.0)

    def test_unhardened_unit_fails_security_gate(self):
        """Test unhardened unit is flagged with high exposure score."""
        audit = self.mgr.audit_unit_exposure("raw-daemon.service", has_hardening_dropin=False)
        self.assertFalse(audit.is_safe)
        self.assertGreater(audit.exposure_score, 3.0)


if __name__ == "__main__":
    unittest.main()

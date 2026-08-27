#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Kernel Crash Dump Triage Engine (T-641, T-642).
# AI-related: usr/libexec/mios/kernel/crash_triage.py, tests/test-crash-triage.py
"""Automated unit test suite for MiOS Kernel Crash Dump Triage Engine."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "kernel"))

from crash_triage import KernelCrashTriageEngine


class TestCrashTriage(unittest.TestCase):
    def setUp(self):
        self.engine = KernelCrashTriageEngine(dry_run=True)

    def test_vmcore_stack_extraction_and_ticket_gen(self):
        """Test parsing panic vmcore extracts faulting module and callstack."""
        rep = self.engine.triage_vmcore("/var/crash/vmcore.zst", mock_panic="Null pointer dereference in nvidia")
        self.assertEqual(rep.faulting_module, "nvidia_modeset")
        self.assertGreaterEqual(len(rep.callstack), 2)
        self.assertIsNotNone(rep.ticket_id)

    def test_markdown_report_formatting(self):
        """Test formatting creates valid markdown for PostgreSQL bug_tracker."""
        rep = self.engine.triage_vmcore("/var/crash/vmcore.zst")
        md = self.engine.format_markdown_report(rep)
        self.assertIn("### Kernel Crash Report", md)
        self.assertIn(rep.faulting_module, md)


if __name__ == "__main__":
    unittest.main()

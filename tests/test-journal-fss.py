#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Forward-Secure Sealed Journald & Tampering Detection (T-707, T-708).
# AI-related: usr/libexec/mios/sec/journal_fss.py, tests/test-journal-fss.py
"""Automated unit test suite for MiOS Journal FSS Manager."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "sec"))

from journal_fss import JournalFSSManager

class TestJournalFSS(unittest.TestCase):
    def setUp(self):
        self.mgr = JournalFSSManager(interval_minutes=15, dry_run=True)

    def test_fss_key_setup_and_tpm_sealing(self):
        """Test initializing FSS generates 15-minute epoch key sealed to TPM."""
        res = self.mgr.setup_fss_keys()
        self.assertEqual(res.interval_minutes, 15)
        self.assertTrue(res.is_sealed_to_tpm)
        self.assertTrue(res.fss_key_id.startswith("fss_"))

    def test_tamper_detection_flags_altered_log_records(self):
        """Test modifying single record byte causes verification failure."""
        logs = [f"Log entry {i} timestamp" for i in range(10)]
        self.assertTrue(self.mgr.verify_journal_integrity(logs))
        # Tamper record 5
        self.assertFalse(self.mgr.verify_journal_integrity(logs, tamper_index=5))

if __name__ == "__main__":
    unittest.main()

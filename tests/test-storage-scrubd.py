#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Storage Scrubbing & PSI Pressure Throttling (T-717, T-718).
# AI-related: usr/libexec/mios/storage/scrubd.py, tests/test-storage-scrubd.py
"""Automated unit test suite for MiOS Storage Scrubber Daemon."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "storage"))

from scrubd import MAX_PSI_PRESSURE_THRESHOLD, StorageScrubManager

class TestStorageScrubd(unittest.TestCase):
    def setUp(self):
        self.mgr = StorageScrubManager(psi_threshold=20.0, dry_run=True)

    def test_bit_rot_repair_and_low_latency_impact(self):
        """Test scrubber repairs corrupt mirror block and limits latency degradation <5%."""
        rep = self.mgr.execute_pool_scrub("btrfs_root", 10000, simulate_bitrot=True)
        self.assertEqual(rep.bit_rot_blocks_repaired, 1)
        self.assertLess(rep.psi_io_pressure_avg, MAX_PSI_PRESSURE_THRESHOLD)
        self.assertLess(rep.interactive_latency_degradation_pct, 5.0)

if __name__ == "__main__":
    unittest.main()

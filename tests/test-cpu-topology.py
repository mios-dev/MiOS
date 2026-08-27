#!/usr/bin/env python3
# AI-hint: Automated unit test suite for CPU Topology Discovery & Core Partitioning (T-657, T-658).
# AI-related: usr/libexec/mios/hw/cpu_topology.py, tests/test-cpu-topology.py
"""Automated unit test suite for MiOS CPU Topology Allocator."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "hw"))

from cpu_topology import CPUTopologyAllocator


class TestCPUTopology(unittest.TestCase):
    def setUp(self):
        self.allocator = CPUTopologyAllocator(dry_run=True)

    def test_hybrid_core_partitioning(self):
        """Test Intel hybrid 8P+8E cores partitions into RT, Interactive, and BG slices."""
        alloc = self.allocator.discover_topology(mock_core_count=16, is_hybrid=True)
        self.assertEqual(alloc.realtime_cpuset, "0-1")
        self.assertEqual(alloc.interactive_cpuset, "2-7")
        self.assertEqual(alloc.background_cpuset, "8-15")

    def test_systemd_slice_dropin_generation(self):
        """Test systemd slice dropins declare AllowedCPUs accurately."""
        alloc = self.allocator.discover_topology(mock_core_count=16, is_hybrid=True)
        dropins = self.allocator.generate_systemd_slice_dropins(alloc)
        self.assertIn("realtime.slice.d/10-cpuset.conf", dropins)
        self.assertIn("AllowedCPUs=0-1", dropins["realtime.slice.d/10-cpuset.conf"])
        self.assertIn("CPUSchedulingPolicy=rr", dropins["realtime.slice.d/10-cpuset.conf"])


if __name__ == "__main__":
    unittest.main()

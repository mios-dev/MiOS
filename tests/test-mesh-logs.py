#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Mesh Log Forwarding & Partition Buffering (T-659, T-660).
# AI-related: usr/libexec/mios/node/mesh_logs.py, tests/test-mesh-logs.py
"""Automated unit test suite for MiOS Mesh Log Forwarder."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "node"))

from mesh_logs import MeshLogForwarder

class TestMeshLogs(unittest.TestCase):
    def setUp(self):
        self.fwd = MeshLogForwarder(node_id="test_node_01", dry_run=True)

    def test_live_log_streaming_when_connected(self):
        """Test logs stream directly to coordinator when mesh network is active."""
        self.fwd.ingest_journal_entry("mios-llm-light.service", "INFO", "Model swapped to qwen-32b")
        self.assertEqual(len(self.fwd.flushed_records), 1)
        self.assertEqual(len(self.fwd.local_buffer), 0)

    def test_partition_buffering_and_reconnection_flush(self):
        """Test network drop buffers 1,000 logs and flushes on reconnection with 0 loss."""
        self.fwd.set_network_state(False)
        for i in range(1000):
            self.fwd.ingest_journal_entry("systemd", "INFO", f"Heartbeat {i}")

        self.assertEqual(len(self.fwd.local_buffer), 1000)
        flushed = self.fwd.set_network_state(True)
        self.assertEqual(flushed, 1000)
        self.assertEqual(len(self.fwd.local_buffer), 0)
        self.assertEqual(len(self.fwd.flushed_records), 1000)

if __name__ == "__main__":
    unittest.main()

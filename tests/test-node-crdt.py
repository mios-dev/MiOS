#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-NODE LWW-Element-Set CRDT and Vector Clock state sync.
# AI-related: usr/libexec/mios/node/crdt.py, src/mios-rs/mios-node/src/state_sync.rs
"""Automated tests for WS-NODE edge mesh CRDT state synchronization and vector clock causality."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_CRDT_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "node", "crdt.py")

spec = importlib.util.spec_from_file_location("crdt", _CRDT_PATH)
if spec and spec.loader:
    crdt = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = crdt
    spec.loader.exec_module(crdt)
else:
    raise ImportError(f"Could not load crdt module from {_CRDT_PATH}")

class TestNodeCRDTSync(unittest.TestCase):
    """Validates vector clocks, LWW-Element-Set conflict resolution, and persistence."""

    def test_vector_clock_causality_and_merge(self):
        vc1 = crdt.VectorClock()
        vc1.increment(101)
        vc1.increment(101)

        vc2 = crdt.VectorClock()
        vc2.increment(102)

        vc1.merge(vc2)
        self.assertEqual(vc1.clocks[101], 2)
        self.assertEqual(vc1.clocks[102], 1)

    def test_lww_tombstone_deletion_convergence(self):
        node1 = crdt.StateStore(101)
        node2 = crdt.StateStore(102)

        node1.set("cluster.domain", b"mios.local")
        node2.merge_remote_store(node1.vector_clock, node1.replicable_elements())
        self.assertEqual(node2.get("cluster.domain"), b"mios.local")

        # Node 1 deletes the key with a newer timestamp
        time.sleep(0.001)
        node1.delete("cluster.domain")
        self.assertIsNone(node1.get("cluster.domain"))

        # Merge tombstone to Node 2
        node2.merge_remote_store(node1.vector_clock, node1.replicable_elements())
        self.assertIsNone(node2.get("cluster.domain"))

    def test_concurrent_edit_last_write_wins(self):
        node1 = crdt.StateStore(101)
        node2 = crdt.StateStore(102)

        node1.set("task.5001.status", b"PENDING")
        time.sleep(0.002)
        node2.set("task.5001.status", b"RUNNING")

        # Merge node2 into node1 -> node2 should win due to newer timestamp
        applied = node1.merge_remote_store(node2.vector_clock, node2.replicable_elements())
        self.assertGreaterEqual(applied, 1)
        self.assertEqual(node1.get("task.5001.status"), b"RUNNING")

    def test_snapshot_persistence_and_reload(self):
        with tempfile.TemporaryDirectory(prefix="mios-crdt-test-") as tmpdir:
            snap_path = os.path.join(tmpdir, "node102_state.json")
            node = crdt.StateStore(102, persistence_path=snap_path)
            node.set("worker.load", b"0.42")
            node.set("worker.healthy", b"true")
            node.save_to_disk()

            restored = crdt.StateStore(102, persistence_path=snap_path)
            self.assertEqual(restored.get("worker.load"), b"0.42")
            self.assertEqual(restored.get("worker.healthy"), b"true")

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNodeCRDTSync)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())

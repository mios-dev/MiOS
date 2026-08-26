#!/usr/bin/env python3
# AI-hint: Automated unit test suite for T-391 CRDT state compaction, tombstone garbage collection, and snapshot WAL truncation.
# AI-related: usr/libexec/mios/node/crdt.py, src/mios-rs/mios-node/src/state_sync.rs
"""Automated tests for WS-NODE CRDT state compaction and snapshot garbage collection."""

from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_CRDT_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "node", "crdt.py")

spec = importlib.util.spec_from_file_location("crdt", _CRDT_PATH)
if spec and spec.loader:
    crdt = importlib.util.module_from_spec(spec)
    sys.modules["crdt"] = crdt
    sys.modules["usr.libexec.mios.node.crdt"] = crdt
    spec.loader.exec_module(crdt)
else:
    raise ImportError(f"Could not load crdt module from {_CRDT_PATH}")


class TestNodeCRDTCompaction(unittest.TestCase):
    """Validates tombstone pruning, disconnection horizon TTL retention, and disk log compaction."""

    def test_tombstone_ttl_compaction(self):
        store = crdt.StateStore(101)

        # 1. Active key: should never be purged
        store.set("active.service", b"running")

        # 2. Fresh tombstone: deleted at t = 1000s
        store.set("fresh.deleted", b"data")
        store.delete("fresh.deleted")
        store.elements["fresh.deleted"].timestamp_ns = int(1000 * 1e9)

        # 3. Stale tombstone: deleted at t = 100s
        store.set("stale.deleted", b"old_data")
        store.delete("stale.deleted")
        store.elements["stale.deleted"].timestamp_ns = int(100 * 1e9)

        self.assertEqual(store.total_elements_count(), 3)
        self.assertEqual(store.count_tombstones(), 2)

        # Run compaction at current_time = 1050s with TTL = 200s
        # Stale age = 950s > 200s -> purged
        # Fresh age = 50s <= 200s -> retained
        stats = store.compact_tombstones(ttl_s=200.0, current_time_s=1050.0)

        self.assertEqual(stats["initial_elements"], 3)
        self.assertEqual(stats["active_elements"], 1)
        self.assertEqual(stats["tombstones_purged"], 1)
        self.assertEqual(stats["tombstones_retained"], 1)
        self.assertEqual(stats["remaining_elements"], 2)

        self.assertEqual(store.get("active.service"), b"running")
        self.assertIn("fresh.deleted", store.elements)
        self.assertNotIn("stale.deleted", store.elements)

    def test_disk_compaction_and_wal_truncation(self):
        with tempfile.TemporaryDirectory(prefix="mios-crdt-gc-") as tmpdir:
            snap_path = os.path.join(tmpdir, "state.json")
            store = crdt.StateStore(101, persistence_path=snap_path)

            store.set("k1", b"v1")
            store.set("k2", b"v2")
            store.delete("k2")
            store.elements["k2"].timestamp_ns = int(10 * 1e9)

            stats = store.compact_disk_storage(ttl_s=100.0, current_time_s=1000.0)
            self.assertEqual(stats["tombstones_purged"], 1)
            self.assertEqual(store.total_elements_count(), 1)

            # Reload from disk and verify clean state
            reloaded = crdt.StateStore(101, persistence_path=snap_path)
            self.assertEqual(reloaded.get("k1"), b"v1")
            self.assertEqual(reloaded.total_elements_count(), 1)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNodeCRDTCompaction)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

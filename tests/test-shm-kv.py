#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-SCHED zero-copy shared memory KV cache transfers.
# AI-related: usr/lib/mios/agent-pipe/mios_shm_kv.py, tests/test-shm-kv.py
"""Automated tests for WS-SCHED shared memory tensor writes, reads, and cleanup."""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe"))

from mios_shm_kv import ShmKVTransfer


class TestShmKV(unittest.TestCase):
    """Validates shared memory allocation, tensor payload round-trip, and cleanup."""

    def test_tensor_write_read_roundtrip(self):
        shm = ShmKVTransfer(segment_name="test_shm_tensor_01", size_bytes=65536)
        try:
            payload = b"FAKE_TENSOR_WEIGHTS_BINARY_DATA"
            success = shm.write_tensor_metadata(seq_len=512, hidden_dim=4096, payload=payload)
            self.assertTrue(success)

            result = shm.read_tensor_metadata()
            self.assertIsNotNone(result)
            seq_len, hidden_dim, data = result
            self.assertEqual(seq_len, 512)
            self.assertEqual(hidden_dim, 4096)
            self.assertEqual(data, payload)
        finally:
            shm.cleanup()


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestShmKV)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

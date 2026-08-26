#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-NODE zero-copy network buffer pool.
# AI-related: usr/libexec/mios/node/buffer_pool.py, src/mios-rs/mios-node/src/buffer_pool.rs
"""Automated tests for WS-NODE BufferPool, PooledBuffer RAII recycling, and zero-copy slicing."""

from __future__ import annotations

import importlib.util
import os
import sys
import threading
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_POOL_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "node", "buffer_pool.py")

spec = importlib.util.spec_from_file_location("buffer_pool", _POOL_PATH)
if spec and spec.loader:
    buffer_pool = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = buffer_pool
    spec.loader.exec_module(buffer_pool)
else:
    raise ImportError(f"Could not load buffer_pool module from {_POOL_PATH}")


class TestNodeBufferPool(unittest.TestCase):
    """Validates bucketed allocations, RAII recycling, zero-copy views, and bounded capacities."""

    def test_bucket_tier_resolution(self):
        self.assertEqual(buffer_pool.BucketTier.from_size(16), buffer_pool.BucketTier.SMALL)
        self.assertEqual(buffer_pool.BucketTier.from_size(256), buffer_pool.BucketTier.SMALL)
        self.assertEqual(buffer_pool.BucketTier.from_size(257), buffer_pool.BucketTier.MEDIUM)
        self.assertEqual(buffer_pool.BucketTier.from_size(4096), buffer_pool.BucketTier.MEDIUM)
        self.assertEqual(buffer_pool.BucketTier.from_size(4097), buffer_pool.BucketTier.LARGE)
        self.assertEqual(buffer_pool.BucketTier.from_size(65536), buffer_pool.BucketTier.LARGE)
        self.assertEqual(buffer_pool.BucketTier.from_size(65537), buffer_pool.BucketTier.HUGE)

    def test_raii_buffer_recycling_and_stats(self):
        pool = buffer_pool.BufferPool()

        # Allocate and use buffer within context manager
        with pool.acquire(100) as buf:
            self.assertEqual(buf.tier, buffer_pool.BucketTier.SMALL)
            buf.write(b"Hello MiOS Wire!")
            self.assertEqual(buf.as_bytes(), b"Hello MiOS Wire!")

            stats = pool.get_stats()
            self.assertEqual(stats.allocations, 1)
            self.assertEqual(stats.pool_misses, 1)
            self.assertEqual(stats.active_leased, 1)

        # Buffer is released upon exit
        stats = pool.get_stats()
        self.assertEqual(stats.recycles, 1)
        self.assertEqual(stats.active_leased, 0)
        self.assertEqual(pool.bucket_depths()[0], 1)

        # Next acquire reuses the recycled buffer
        with pool.acquire(100) as buf2:
            self.assertEqual(buf2.len(), 0)  # Cleared on recycle
            buf2.write(b"RecycledPayload")

            stats2 = pool.get_stats()
            self.assertEqual(stats2.allocations, 2)
            self.assertEqual(stats2.pool_hits, 1)
            self.assertEqual(stats2.active_leased, 1)

    def test_zero_copy_slicing_and_prefix_split(self):
        pool = buffer_pool.BufferPool()
        with pool.acquire(1000) as buf:
            buf.write(b"FIXED_16B_HEADER_PAYLOAD_BODY_DATA_CHUNK")

            # Zero-copy slicing via memoryview
            header_view = buf.slice(0, 16)
            self.assertEqual(bytes(header_view), b"FIXED_16B_HEADER")

            payload_view = buf.slice(16, buf.len())
            self.assertEqual(bytes(payload_view), b"_PAYLOAD_BODY_DATA_CHUNK")

            # Prefix splitting
            prefix = buf.split_prefix(16)
            self.assertEqual(prefix, b"FIXED_16B_HEADER")
            self.assertEqual(buf.as_bytes(), b"_PAYLOAD_BODY_DATA_CHUNK")

    def test_bounded_pool_capacity(self):
        pool = buffer_pool.BufferPool()
        max_cap = buffer_pool.BucketTier.SMALL.max_pool_capacity

        # Acquire max_cap + 10 buffers
        buffers = [pool.acquire_exact(buffer_pool.BucketTier.SMALL) for _ in range(max_cap + 10)]

        # Release all buffers
        for b in buffers:
            b.release()

        # Verify bucket size is bounded at max_cap
        small_depth = pool.bucket_depths()[0]
        self.assertEqual(small_depth, max_cap)

    def test_multithreaded_pool_concurrency(self):
        pool = buffer_pool.BufferPool()
        threads = []

        def worker():
            for _ in range(50):
                with pool.acquire(512) as b:
                    b.write(b"ThreadPayload")
                    self.assertEqual(b.as_bytes(), b"ThreadPayload")

        for _ in range(8):
            t = threading.Thread(target=worker)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        stats = pool.get_stats()
        self.assertEqual(stats.active_leased, 0)
        self.assertEqual(stats.allocations, 400)
        self.assertGreater(stats.pool_hits, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestNodeBufferPool)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

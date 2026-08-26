#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-STRG mios-bench-storage storage performance benchmark tool.
# AI-related: usr/libexec/mios/storage/mios-bench-storage, usr/bin/mios-bench-storage
"""Automated tests for WS-STRG storage benchmark tool (T-409 / AGY-2007)."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_BENCH_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "storage", "mios-bench-storage")

loader = importlib.machinery.SourceFileLoader("bench_storage", _BENCH_PATH)
spec = importlib.util.spec_from_loader("bench_storage", loader)
if spec and spec.loader:
    bench_storage = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = bench_storage
    spec.loader.exec_module(bench_storage)
else:
    raise ImportError(f"Could not load bench_storage module from {_BENCH_PATH}")


class TestBenchStorage(unittest.TestCase):
    """Validates IOPS, sequential throughput, fsync latency benchmarks, floor evaluations, and scratch safety."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="mios_test_bench_storage_")

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_scratch_file_lifecycle_and_safety(self):
        """Verify scratch file is created with specified size and cleaned up safely."""
        scratch_path = bench_storage.prepare_benchmark_file(self.test_dir, file_size_mb=2)
        self.assertTrue(os.path.isfile(scratch_path))
        self.assertEqual(os.path.getsize(scratch_path), 2 * 1024 * 1024)

        # Confirm non-destructive temporary naming
        self.assertIn("mios_bench_scratch_", os.path.basename(scratch_path))
        os.remove(scratch_path)

    def test_random_4k_benchmarks(self):
        scratch_path = bench_storage.prepare_benchmark_file(self.test_dir, file_size_mb=2)
        try:
            r_iops, r_lat = bench_storage.run_random_4k_read_benchmark(scratch_path, duration_sec=0.2, max_ops=1000)
            self.assertGreater(r_iops, 0.0)
            self.assertGreater(r_lat, 0.0)

            w_iops, w_lat = bench_storage.run_random_4k_write_benchmark(scratch_path, duration_sec=0.2, max_ops=1000)
            self.assertGreater(w_iops, 0.0)
            self.assertGreater(w_lat, 0.0)
        finally:
            if os.path.exists(scratch_path):
                os.remove(scratch_path)

    def test_seq_1m_throughput_benchmarks(self):
        scratch_path = bench_storage.prepare_benchmark_file(self.test_dir, file_size_mb=4)
        try:
            r_mbps = bench_storage.run_seq_1m_read_benchmark(scratch_path, duration_sec=0.2)
            self.assertGreater(r_mbps, 0.0)

            w_mbps = bench_storage.run_seq_1m_write_benchmark(scratch_path, duration_sec=0.2)
            self.assertGreater(w_mbps, 0.0)
        finally:
            if os.path.exists(scratch_path):
                os.remove(scratch_path)

    def test_fsync_latency_percentiles(self):
        scratch_path = bench_storage.prepare_benchmark_file(self.test_dir, file_size_mb=2)
        try:
            lat_stats = bench_storage.run_fsync_latency_benchmark(scratch_path, iterations=20)
            self.assertIn("p50_us", lat_stats)
            self.assertIn("p95_us", lat_stats)
            self.assertIn("p99_us", lat_stats)
            self.assertIn("max_us", lat_stats)
            self.assertGreater(lat_stats["p50_us"], 0.0)
            self.assertLessEqual(lat_stats["p50_us"], lat_stats["p95_us"])
            self.assertLessEqual(lat_stats["p95_us"], lat_stats["p99_us"])
            self.assertLessEqual(lat_stats["p99_us"], lat_stats["max_us"])
        finally:
            if os.path.exists(scratch_path):
                os.remove(scratch_path)

    def test_evaluate_inference_floors_pass_and_fail(self):
        # Passing mock metrics
        passing_metrics = {
            "iops_rand_read_4k": 8000.0,
            "iops_rand_write_4k": 4000.0,
            "mbps_seq_read_1m": 500.0,
            "mbps_seq_write_1m": 300.0,
            "fsync_latency_us": {"p95_us": 4000.0},
        }
        res_pass = bench_storage.evaluate_inference_floors(passing_metrics, profile_name="standard")
        self.assertTrue(res_pass["meets_ai_inference_floors"])
        self.assertTrue(res_pass["evaluations"]["iops_rand_read_4k"]["passed"])
        self.assertTrue(res_pass["evaluations"]["fsync_latency_p95_us"]["passed"])

        # Failing mock metrics (low IOPS, high latency)
        failing_metrics = {
            "iops_rand_read_4k": 500.0,
            "iops_rand_write_4k": 200.0,
            "mbps_seq_read_1m": 50.0,
            "mbps_seq_write_1m": 20.0,
            "fsync_latency_us": {"p95_us": 80000.0},
        }
        res_fail = bench_storage.evaluate_inference_floors(failing_metrics, profile_name="heavy_gpu")
        self.assertFalse(res_fail["meets_ai_inference_floors"])
        self.assertFalse(res_fail["evaluations"]["iops_rand_read_4k"]["passed"])
        self.assertFalse(res_fail["evaluations"]["mbps_seq_read_1m"]["passed"])

    def test_full_benchmark_suite_execution_and_cleanup(self):
        report = bench_storage.run_full_storage_benchmark(
            target_dir=self.test_dir,
            file_size_mb=4,
            duration_sec=0.2,
            fsync_iterations=10,
            profile="edge_llm",
        )
        self.assertEqual(report["file_size_mb"], 4)
        self.assertIn("assessment", report)
        self.assertIn("meets_ai_inference_floors", report["assessment"])

        # Verify scratch files are deleted
        scratch_files = [f for f in os.listdir(self.test_dir) if "mios_bench_scratch_" in f]
        self.assertEqual(len(scratch_files), 0, "Scratch files were not cleaned up")


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestBenchStorage)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

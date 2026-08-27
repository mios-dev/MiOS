#!/usr/bin/env python3
# AI-hint: Unit test suite for MiOS Container Storage LRU Garbage Collection engine (T-590 / AGY-2188).
# AI-related: usr/libexec/mios/storage/container_gc.py, usr/share/doc/mios/manual/storage.md
"""Unit and integration tests for ContainerGCManager."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_TARGET_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "storage", "container_gc.py")

spec = importlib.util.spec_from_file_location("container_gc", _TARGET_PATH)
if spec and spec.loader:
    container_gc = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = container_gc
    spec.loader.exec_module(container_gc)
else:
    raise ImportError(f"Could not load module from {_TARGET_PATH}")


class TestContainerGCManager(unittest.TestCase):
    """Test suite for container image inspection, LRU sorting, and threshold pruning."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="mios-test-containargc-")
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_list_images_mock(self):
        mgr = container_gc.ContainerGCManager(mock=True)
        images = mgr.list_images()
        self.assertEqual(len(images), 4)

        pinned = [img for img in images if img.is_pinned]
        self.assertEqual(len(pinned), 2)
        self.assertTrue(any(img.repository == "ghcr.io/mios-dev/mios" for img in pinned))

    def test_plan_prune_ordering_lru(self):
        mgr = container_gc.ContainerGCManager(threshold_pct=80.0, mock=True)
        plan = mgr.plan_prune()

        # In mock mode usage is 88.5% > 80.0%, so pruning triggers
        self.assertEqual(plan.unreferenced_images, 2)
        self.assertEqual(len(plan.prune_targets), 2)

        # Oldest unreferenced image (alpine:3.18) must be first target
        self.assertEqual(plan.prune_targets[0].repository, "docker.io/library/alpine")
        self.assertEqual(plan.prune_targets[1].repository, "docker.io/library/node")
        self.assertAlmostEqual(plan.reclaimable_mb, 192.5, places=1)

    def test_plan_prune_below_threshold_returns_zero_targets(self):
        mgr = container_gc.ContainerGCManager(threshold_pct=95.0, mock=True)
        plan = mgr.plan_prune()

        # In mock mode usage is 88.5% < 95.0%, so zero targets should be pruned
        self.assertEqual(len(plan.prune_targets), 0)
        self.assertEqual(plan.reclaimable_mb, 0.0)

    def test_execute_prune_mock(self):
        mgr = container_gc.ContainerGCManager(threshold_pct=80.0, mock=True)
        plan = mgr.plan_prune()
        count, reclaimed_mb = mgr.execute_prune(plan)

        self.assertEqual(count, 2)
        self.assertAlmostEqual(reclaimed_mb, 192.5, places=1)

    def test_cli_execution_scan_mock(self):
        test_args = ["container_gc.py", "--scan", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = container_gc.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_plan_mock(self):
        test_args = ["container_gc.py", "--plan", "--threshold", "80.0", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = container_gc.main()
            self.assertEqual(exit_code, 0)

    def test_cli_execution_prune_mock(self):
        test_args = ["container_gc.py", "--prune", "--threshold", "80.0", "--mock", "--json"]
        with patch.object(sys, "argv", test_args):
            exit_code = container_gc.main()
            self.assertEqual(exit_code, 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestContainerGCManager)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

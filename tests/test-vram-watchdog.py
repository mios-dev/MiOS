#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-AI VRAM watermark monitoring and eviction.
# AI-related: usr/libexec/mios/ai/vram-watchdog.py
"""Automated tests for WS-AI GPU memory evaluation and watermark threshold breaches."""

from __future__ import annotations

import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_VRAM_PATH = os.path.join(_ROOT, "usr", "libexec", "mios", "ai", "vram-watchdog.py")

spec = importlib.util.spec_from_file_location("vram_watchdog", _VRAM_PATH)
if spec and spec.loader:
    vram_watchdog = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = vram_watchdog
    spec.loader.exec_module(vram_watchdog)
else:
    raise ImportError(f"Could not load vram-watchdog module from {_VRAM_PATH}")

class TestVramWatchdog(unittest.TestCase):
    """Validates VRAM ratio computation and eviction decisions."""

    def test_vram_watermark_evaluation(self):
        monitor = vram_watchdog.VramMonitor(watermark_threshold=0.95)

        # 90% utilization (below 95%)
        needs_evict, ratio = monitor.evaluate_vram_status(used_bytes=90, total_bytes=100)
        self.assertFalse(needs_evict)
        self.assertAlmostEqual(ratio, 0.90)

        # 96% utilization (above 95%)
        needs_evict, ratio = monitor.evaluate_vram_status(used_bytes=96, total_bytes=100)
        self.assertTrue(needs_evict)
        self.assertAlmostEqual(ratio, 0.96)

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestVramWatchdog)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())

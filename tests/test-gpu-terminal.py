#!/usr/bin/env python3
# AI-hint: Automated unit test suite for GPU Terminal Rendering & Sub-5ms Keystroke Latency (T-727, T-728).
# AI-related: usr/libexec/mios/desktop/gpu_terminal.py, tests/test-gpu-terminal.py
"""Automated unit test suite for MiOS GPU Terminal Manager."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "usr", "libexec", "mios", "desktop"))

from gpu_terminal import MAX_KEYSTROKE_LATENCY_MS, MIN_GLYPH_THROUGHPUT_CPS, GPUTerminalManager

class TestGPUTerminal(unittest.TestCase):
    def setUp(self):
        self.mgr = GPUTerminalManager(renderer="Vulkan", dry_run=True)

    def test_alacritty_config_generation(self):
        """Test generated Alacritty config specifies opacity and Nerd font."""
        conf = self.mgr.generate_alacritty_config()
        self.assertIn("opacity = 0.95", conf)
        self.assertIn("JetBrainsMono Nerd Font", conf)

    def test_glyph_throughput_and_sub_5ms_latency(self):
        """Test glyph throughput exceeds 1,000,000 chars/s and keystroke latency < 5ms."""
        prof = self.mgr.benchmark_render_performance()
        self.assertGreaterEqual(prof.glyph_throughput_chars_per_sec, MIN_GLYPH_THROUGHPUT_CPS)
        self.assertLess(prof.keystroke_latency_ms, MAX_KEYSTROKE_LATENCY_MS)
        self.assertTrue(prof.vsync_locked)

if __name__ == "__main__":
    unittest.main()

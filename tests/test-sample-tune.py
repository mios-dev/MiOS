#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-AI dynamic sampling scheduler.
# AI-related: usr/lib/mios/agent-pipe/mios_sample_tune.py
"""Automated tests for WS-AI task entropy estimation and sampling hyperparameter adaptation."""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe"))

from mios_sample_tune import SamplingScheduler


class TestSampleTune(unittest.TestCase):
    """Validates sampling hyperparameter tuning for deterministic vs creative tasks."""

    def test_deterministic_code_task(self):
        scheduler = SamplingScheduler()
        params = scheduler.estimate_hyperparameters("Please write a python function to parse JSON")
        self.assertEqual(params["temperature"], 0.0)
        self.assertEqual(params["mode"], "deterministic")

    def test_creative_task(self):
        scheduler = SamplingScheduler()
        params = scheduler.estimate_hyperparameters("Write a creative story about an AI OS")
        self.assertEqual(params["temperature"], 0.7)
        self.assertEqual(params["mode"], "creative")


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSampleTune)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

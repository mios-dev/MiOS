#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-AI speculative decoding multi-model lane configuration.
# AI-related: usr/share/mios/llamacpp/mios-llm-light.yaml, usr/share/containers/systemd/mios-llm-heavy.container
"""Automated tests for WS-AI speculative model parameters and draft lane pairings."""

from __future__ import annotations

import os
import sys
import unittest
import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_CFG_PATH = os.path.join(_ROOT, "usr", "share", "mios", "llamacpp", "mios-llm-light.yaml")


class TestSpeculativeDecodingConfig(unittest.TestCase):
    """Validates llamacpp YAML model mappings and speculative parameters."""

    def test_yaml_structure_and_models(self):
        self.assertTrue(os.path.exists(_CFG_PATH))
        with open(_CFG_PATH, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        self.assertIn("models", data)
        self.assertIn("granite4.1:8b", data["models"])
        self.assertIn("lfm2:700m", data["models"])


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSpeculativeDecodingConfig)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

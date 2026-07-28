# AI-hint: Unit tests for mios_pipe.scheduler.vram (AGY-346).
"""Unit tests for VRAM and model residency manager."""

import asyncio
import unittest

from mios_pipe.scheduler.vram import (
    _model_active,
    _model_is_active,
    _norm_model_tag,
    configure,
)


class TestVram(unittest.TestCase):

    def setUp(self):
        configure(
            vram_budget_mb=23000,
            vram_checkpoint_enable=True,
        )

    def test_norm_model_tag(self):
        self.assertEqual(_norm_model_tag("mios-hermes"), "mios-hermes:latest")
        self.assertEqual(_norm_model_tag("qwen3.5:4b"), "qwen3.5:4b")
        self.assertEqual(_norm_model_tag("llama3:latest"), "llama3:latest")

    def test_model_active_refcount_roundtrip(self):
        ep = "http://localhost:8450/v1"
        model = "mios-hermes"

        self.assertFalse(_model_is_active(ep, model))

        asyncio.run(_model_active(ep, model, +1))
        self.assertTrue(_model_is_active(ep, model))

        asyncio.run(_model_active(ep, model, -1))
        self.assertFalse(_model_is_active(ep, model))


if __name__ == "__main__":
    unittest.main()

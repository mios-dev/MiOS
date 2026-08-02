# AI-hint: Unit tests for mios_pipe.context.scratchpad.
"""Unit tests for agent scratchpad blackboard."""

import contextvars
import unittest

from mios_pipe.context.scratchpad import (
    _scratchpad_note,
    _scratchpad_render,
    _scratchpad_for,
    _scratchpad_key,
    configure,
)

_test_conv_var = contextvars.ContextVar("test_conv_key", default="chat_test_123")


class TestScratchpad(unittest.TestCase):

    def setUp(self):
        configure(
            scratchpad_enable=True,
            scratchpad_max=5,
            scratchpad_summary_chars=100,
            scratchpad_ttl_s=3600,
            scratchpad_inject=5,
            conv_key_var=_test_conv_var,
        )

    def test_scratchpad_key_fallback(self):
        self.assertEqual(_scratchpad_key({}, "fb"), "fb")
        self.assertEqual(_scratchpad_key({"metadata": {"chat_id": "c1"}}), "c1")

    def test_scratchpad_note_and_render(self):
        _scratchpad_note("planner", "Investigating build failure in 98-drift-checks.sh")
        _scratchpad_note("coder", "Patched check_negative_coverage function")

        rendered = _scratchpad_render()
        self.assertIn("Shared agent context", rendered)
        self.assertIn("planner", rendered)
        self.assertIn("coder", rendered)
        self.assertIn("Investigating build failure", rendered)

    def test_scratchpad_max_bound(self):
        for i in range(10):
            _scratchpad_note("agent", f"Checkpoint note {i}")

        dq = _scratchpad_for("chat_test_123")
        self.assertEqual(len(dq), 5)
        self.assertEqual(dq[-1]["note"], "Checkpoint note 9")


if __name__ == "__main__":
    unittest.main()

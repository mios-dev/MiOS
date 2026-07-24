# AI-hint: Unit test suite for quality_gate.py and smartroute escalation integration.
# AI-related: mios_pipe/routing/quality_gate.py, mios_pipe/routing/smartroute.py
"""Unit tests for mios_pipe.routing.quality_gate."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mios_pipe.routing.quality_gate import evaluate_quality
from mios_pipe.routing.smartroute import should_escalate


class TestQualityGate(unittest.TestCase):
    """Test deterministic quality evaluation and escalation producer behavior."""

    def test_good_output_passes(self):
        good = "The capital of France is Paris. It is located on the Seine River."
        ok, reason = evaluate_quality(good)
        self.assertTrue(ok)
        self.assertEqual(reason, "quality_ok")
        self.assertFalse(should_escalate(ok, local_exhausted=False))

    def test_empty_output_fails_and_escalates(self):
        ok, reason = evaluate_quality("   \n")
        self.assertFalse(ok)
        self.assertEqual(reason, "empty_output")
        self.assertTrue(should_escalate(ok, local_exhausted=False))

    def test_below_min_length_fails(self):
        ok, reason = evaluate_quality("Hi", config={"min_length": 5})
        self.assertFalse(ok)
        self.assertEqual(reason, "below_min_length")
        self.assertTrue(should_escalate(ok, local_exhausted=False))

    def test_refusal_or_punt_fails(self):
        punt = "I do not have access to that information in the provided context."
        ok, reason = evaluate_quality(punt)
        self.assertFalse(ok)
        self.assertEqual(reason, "refusal_or_punt")
        self.assertTrue(should_escalate(ok, local_exhausted=False))

    def test_malformed_json_fails(self):
        bad_json = '{"key": "value", "unclosed": '
        ok, reason = evaluate_quality(bad_json)
        self.assertFalse(ok)
        self.assertEqual(reason, "malformed_json")
        self.assertTrue(should_escalate(ok, local_exhausted=False))

    def test_valid_json_passes(self):
        good_json = '{"status": "ok", "count": 42}'
        ok, reason = evaluate_quality(good_json)
        self.assertTrue(ok)
        self.assertEqual(reason, "quality_ok")
        self.assertFalse(should_escalate(ok, local_exhausted=False))


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-ORCH DCI tension-tracking ledger.
# AI-related: usr/lib/mios/agent-pipe/mios_tension.py
"""Automated tests for WS-ORCH objection tracking, severity filtering, and deliberation gating."""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe"))

from mios_tension import TensionLedger


class TestTensionLedger(unittest.TestCase):
    """Validates objection recording, resolution, and closing checks."""

    def test_tension_lifecycle_and_gating(self):
        ledger = TensionLedger()
        t1 = ledger.record_objection("agent_sec", "claim_01", "critical", "Potential memory leak in KV cache")
        t2 = ledger.record_objection("agent_perf", "claim_02", "low", "Minor variable naming polish")

        # Open critical objection blocks closing
        can_close, unresolved = ledger.can_close_deliberation()
        self.assertFalse(can_close)
        self.assertEqual(len(unresolved), 1)

        # Resolve the critical objection
        success = ledger.resolve_objection(t1, "Added explicit cleanup handler")
        self.assertTrue(success)

        # Now only low objection remains -> can close
        can_close, unresolved = ledger.can_close_deliberation()
        self.assertTrue(can_close)
        self.assertEqual(len(unresolved), 0)


def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTensionLedger)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())

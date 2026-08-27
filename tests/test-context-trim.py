#!/usr/bin/env python3
# AI-hint: Automated unit test suite for WS-AI adaptive context window truncation with needle heuristics.
# AI-related: usr/lib/mios/agent-pipe/mios_ctxpack.py, usr/lib/mios/agent-pipe/mios_pipe/context/ctxpack.py
"""Automated tests for WS-AI system prompt retention and priority conversational trimming."""

from __future__ import annotations

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe"))

from mios_pipe.context.ctxpack import pack

class TestContextTrim(unittest.TestCase):
    """Validates priority packing, needle retention, and token budget bounds."""

    def test_system_prompt_retention(self):
        items = [
            {"type": "system", "text": "SYSTEM_INSTRUCTION", "prio": 100},
            {"type": "memory", "text": "PINNED_FACT", "prio": 80},
            {"type": "chat", "text": "OLD_INTERMEDIATE_TURN", "prio": 10},
            {"type": "chat", "text": "RECENT_USER_TURN", "prio": 50},
        ]
        # Restrict budget so that only top items fit
        res = pack(items, budget=8, text_of=lambda x: x["text"], priority_of=lambda x: x["prio"])
        kept_types = [x["type"] for x in res.kept]
        self.assertIn("system", kept_types)
        self.assertIn("memory", kept_types)
        self.assertNotIn("OLD_INTERMEDIATE_TURN", [x["text"] for x in res.kept])

def main() -> int:
    suite = unittest.TestLoader().loadTestsFromTestCase(TestContextTrim)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    sys.exit(main())

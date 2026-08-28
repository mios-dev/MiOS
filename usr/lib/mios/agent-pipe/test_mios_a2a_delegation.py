#!/usr/bin/env python3
# AI-hint: Unit test for mios_a2a_delegation.py
# AI-related: mios_a2a_delegation
# AI-functions: test_agent_card, test_payload_negotiation, class TestA2ADelegation
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from mios_a2a_delegation import AgentCard, PayloadMode

class TestA2ADelegation(unittest.TestCase):
    def test_agent_card(self):
        card = AgentCard(agent_id="test_agent", endpoint="http://localhost:8000", supported_interfaces=["text", "semantic_frame"])
        self.assertTrue(card.supports(PayloadMode.TEXT))
        self.assertTrue(card.supports(PayloadMode.SEMANTIC_FRAME))
        self.assertFalse(card.supports(PayloadMode.EMBEDDING_HINTS))
        d = card.to_dict()
        self.assertEqual(d["agent_id"], "test_agent")

    def test_payload_negotiation(self):
        self.assertEqual(PayloadMode.TEXT.value, "text")

if __name__ == "__main__":
    unittest.main()

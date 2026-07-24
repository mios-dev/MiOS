# AI-hint: Unit test suite for mios_pipe.mcp_dispatch module.
# AI-related: mios_pipe/mcp_dispatch.py
"""Unit tests for mios_pipe.mcp_dispatch."""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mios_pipe.mcp_dispatch import build_mcp_tool_envelope


class TestMcpDispatch(unittest.TestCase):
    """Test MCP tool envelope builder."""

    def test_build_mcp_tool_envelope(self):
        env = build_mcp_tool_envelope("query_db", {"query": "hello"}, call_id="call_123")
        self.assertEqual(env["type"], "function")
        self.assertEqual(env["id"], "call_123")
        self.assertEqual(env["function"]["name"], "query_db")
        self.assertEqual(env["function"]["arguments"], {"query": "hello"})


if __name__ == "__main__":
    unittest.main()

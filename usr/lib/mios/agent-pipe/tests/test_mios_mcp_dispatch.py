# AI-hint: Unit test for mios_pipe.mcp_dispatch module (AGY-114).
from __future__ import annotations

from mios_pipe.mcp_dispatch import build_mcp_tool_envelope


def test_build_mcp_tool_envelope():
    env = build_mcp_tool_envelope("get_weather", {"location": "Tokyo"}, "call_123")
    assert env["type"] == "function"
    assert env["id"] == "call_123"
    assert env["function"]["name"] == "get_weather"
    assert env["function"]["arguments"]["location"] == "Tokyo"

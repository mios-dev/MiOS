# AI-hint: MCP tool call dispatch module for MiOS agent-pipe.
from __future__ import annotations

from typing import Any, Dict, Optional


def build_mcp_tool_envelope(
    tool_name: str,
    arguments: Dict[str, Any],
    call_id: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "type": "function",
        "id": call_id or f"call_{tool_name}",
        "function": {
            "name": tool_name,
            "arguments": arguments,
        },
    }

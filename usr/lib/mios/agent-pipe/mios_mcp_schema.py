#!/usr/bin/env python3
# AI-hint: Strict OpenAI function-schema conversion for MCP tool definitions.
# AI-related: mios_mcp, mios_mcp_transport
"""Pure schema translation, split out of mios_mcp.py.

No module state: these are total functions over dicts, which is why they were
the first thing to lift when mios_mcp.py went past the 800-line ceiling.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Strict OpenAI Function Schema Conversion
# ---------------------------------------------------------------------------

def make_schema_strict(schema: Optional[dict]) -> dict:
    """Convert an arbitrary JSON Schema (such as an MCP tool inputSchema) into
    a strict OpenAI function parameter definition.
    - Ensures root type is 'object'
    - Ensures all properties are listed in 'required'
    - Widens optional properties with 'null' type
    - Sets 'additionalProperties: False'
    - Recursively processes nested objects and arrays."""
    if not isinstance(schema, dict) or not schema:
        return {"type": "object", "properties": {}, "required": [], "additionalProperties": False}

    s = dict(schema)
    stype = s.get("type")

    if stype == "object" or ("properties" in s) or stype is None:
        s["type"] = "object"
        properties = s.get("properties") or {}
        if not isinstance(properties, dict):
            properties = {}
        s["properties"] = dict(properties)

        required = s.get("required") or []
        if not isinstance(required, list):
            required = []
        new_required = list(required)

        for prop_name, prop_val in s["properties"].items():
            if isinstance(prop_val, dict):
                prop_val = make_schema_strict(prop_val)
                s["properties"][prop_name] = prop_val
                if prop_name not in required:
                    new_required.append(prop_name)
                    t = prop_val.get("type")
                    if isinstance(t, str):
                        prop_val["type"] = [t, "null"]
                    elif isinstance(t, list):
                        if "null" not in t:
                            prop_val["type"] = list(t) + ["null"]
                    else:
                        prop_val["type"] = ["object", "null"]
            else:
                prop_val = {"type": ["string", "null"]}
                s["properties"][prop_name] = prop_val
                if prop_name not in required:
                    new_required.append(prop_name)

        s["required"] = new_required
        s["additionalProperties"] = False

    elif stype == "array":
        items = s.get("items")
        if isinstance(items, dict):
            s["items"] = make_schema_strict(items)

    return s

# Alias for backward compatibility
_make_schema_strict = make_schema_strict

def convert_mcp_to_openai_schema(mcp_tool: dict, server_id: str = "") -> dict:
    """Convert an MCP tool definition (name, description, inputSchema) into a
    strict OpenAI function tool schema:
    {"type": "function", "function": {"name": ..., "description": ..., "parameters": ..., "strict": True}}"""
    raw_name = str(mcp_tool.get("name") or "").strip()
    if server_id and not raw_name.startswith(f"mcp.{server_id}."):
        if raw_name.startswith("mcp."):
            tool_name = raw_name
        else:
            tool_name = f"mcp.{server_id}.{raw_name}"
    else:
        tool_name = raw_name

    desc = mcp_tool.get("description") or f"MCP tool {tool_name}"
    input_schema = mcp_tool.get("inputSchema") or {}
    strict_parameters = make_schema_strict(input_schema)

    schema: Dict[str, Any] = {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": desc,
            "strict": True,
            "parameters": strict_parameters,
        },
    }
    sid = server_id or mcp_tool.get("server_id")
    if sid:
        schema["x-mios-mcp-server"] = sid
    return schema

# Alias for backward compatibility with existing agent-pipe modules
_mcp_tool_to_openai_tool = lambda key, info: convert_mcp_to_openai_schema(
    {"name": key, "description": info.get("description"), "inputSchema": info.get("inputSchema")},
    server_id=info.get("server_id", ""),
)


#!/usr/bin/env python3
# AI-hint: Pretty-print /skills/openai-tools so the operator can see the exact JSON schema sub-agents (Hermes / OpenCode / future MCP) get when they fetch the catalog.
# AI-related: localhost:8640
"""Pretty-print /skills/openai-tools so the operator can see the
exact JSON schema sub-agents (Hermes / OpenCode / future MCP) get
when they fetch the catalog."""
import json
import sys
import urllib.request

with urllib.request.urlopen(
    "http://localhost:8640/skills/openai-tools", timeout=5
) as r:
    payload = json.load(r)

for t in payload.get("tools", []):
    fn = t["function"]
    name = fn["name"]
    desc = fn["description"]
    required = fn["parameters"]["required"]
    print(f"  {name:<40} required={required}")
    print(f"    description: {desc}")
    print()

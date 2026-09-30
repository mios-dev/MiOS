#!/bin/bash
# AI-hint: A smoke-test script to verify the MCP server's health by validating HTTP endpoints (/v1/verbs, /v1/dispatch) and stdio JSON-RPC interactions ...
# AI-doc: usr/share/doc/mios/manual/support.md
set -euo pipefail

echo "== /v1/verbs =="
curl -sf http://localhost:8640/v1/verbs > /tmp/mcp-verbs.json
python3 - <<'PY'
import json
d = json.load(open("/tmp/mcp-verbs.json"))
print(f"tool count: {len(d['tools'])}")
print(f"sample: {d['tools'][0]['name']} -- {d['tools'][0]['description'][:60]}")
print(f"schema keys: {list(d['tools'][0]['inputSchema'].keys())}")
PY
echo
echo "== /v1/dispatch =="
curl -sf -X POST http://localhost:8640/v1/dispatch \
    -H "Content-Type: application/json" \
    -d '{"tool":"list_windows","args":{}}' > /tmp/mcp-disp.json
python3 - <<'PY'
import json
d = json.load(open("/tmp/mcp-disp.json"))
print(f"success={d.get('success')} latency_ms={d.get('latency_ms')} stderr={(d.get('stderr') or '')[:80]!r}")
PY
echo
echo "== MCP SDK stdio: discovery, list, call =="
MCP_PYTHON="${MIOS_MCP_PYTHON:-/usr/lib/mios/agents/.venv/bin/python3}"
export MCP_PYTHON
"$MCP_PYTHON" - <<'PY'
import asyncio
import os
from mcp import Client, StdioServerParameters

async def main():
    server = StdioServerParameters(
        command=os.environ["MCP_PYTHON"],
        args=["/usr/libexec/mios/mios-mcp-server"],
    )
    async with Client(server) as client:
        listed = await client.list_tools()
        print(f"protocol={client.protocol_version} tools={len(listed.tools)}")
        assert listed.tools, "MCP catalog is empty"
        result = await client.call_tool("system_status", {})
        print(f"isError={result.is_error} content_blocks={len(result.content)}")

asyncio.run(main())
PY

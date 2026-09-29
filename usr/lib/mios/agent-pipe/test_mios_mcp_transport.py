#!/usr/bin/env python3
# AI-hint: Checks the SDK-backed MCP transport adapters and secret-safe header rendering.
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""The SDK owns wire framing; these checks cover only MiOS adapter behavior."""
import asyncio
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mios_mcp_transport as transport


class _Model:
    def __init__(self, **values):
        self.values = values

    def model_dump(self, **_kwargs):
        return self.values


class _SDK:
    enters = 0
    exits = 0

    def __init__(self, _target, **_kwargs):
        self.protocol_version = "2026-07-28"
        self.server_info = _Model(name="fixture", version="1")

    async def __aenter__(self):
        type(self).enters += 1
        return self

    async def __aexit__(self, *_args):
        type(self).exits += 1

    async def list_tools(self, *, cursor=None):
        return _Model(tools=[{"name": "query", "inputSchema": {"type": "object"}}], nextCursor=cursor)

    async def call_tool(self, name, arguments, read_timeout_seconds=None):
        return _Model(content=[{"type": "text", "text": name}], isError=False)


class TransportTests(unittest.TestCase):
    def setUp(self):
        _SDK.enters = _SDK.exits = 0

    def test_header_templates_expand_without_mutating_source(self):
        os.environ["MIOS_TEST_TOKEN"] = "secret"
        source = {"Authorization": "Bearer ${MIOS_TEST_TOKEN}"}
        try:
            self.assertEqual(transport._mcp_render_headers(source), {"Authorization": "Bearer secret"})
            self.assertEqual(source["Authorization"], "Bearer ${MIOS_TEST_TOKEN}")
        finally:
            os.environ.pop("MIOS_TEST_TOKEN", None)

    def test_stdio_sdk_client_reuses_session_and_maps_results(self):
        async def check():
            with patch.object(transport, "Client", _SDK):
                client = transport._McpStdioClient("fixture", "python", ["server.py"])
                self.assertEqual((await client.initialize())["protocolVersion"], "2026-07-28")
                self.assertEqual((await client.initialize())["serverInfo"]["name"], "fixture")
                self.assertEqual(_SDK.enters, 1)
                self.assertEqual((await client.list_tools())["result"]["tools"][0]["name"], "query")
                self.assertEqual((await client.call_tool("query", {}))["result"]["content"][0]["text"], "query")
                await client.close()
                self.assertEqual(_SDK.exits, 1)
        asyncio.run(check())

    def test_unsupported_compatibility_method_returns_error(self):
        async def check():
            with patch.object(transport, "Client", _SDK):
                client = transport._McpStdioClient("fixture", "python")
                try:
                    result = await client._rpc("made-up/method")
                    self.assertEqual(result["error"]["code"], -32601)
                finally:
                    await client.close()
        asyncio.run(check())


if __name__ == "__main__":
    unittest.main(verbosity=2)

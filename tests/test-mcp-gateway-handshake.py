#!/usr/bin/env python3
# AI-hint: Automated unit test suite for Declarative MCP Server Lifecycle & Dynamic Tool Schema Converter (T-577 / T-578 / AGY-2175 / AGY-2176).
# AI-related: usr/lib/mios/agent-pipe/mios_mcp.py, usr/lib/mios/agent-pipe/server.py
"""Automated unit test suite validating Declarative MCP server discovery from TOML declarations,
JSON-RPC 2.0 stdio/SSE handshakes, strict OpenAI function schema translation, dynamic tool
execution dispatching, and error handling."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import unittest
from unittest import mock
from typing import Any, Dict, List

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.normpath(os.path.join(_HERE, ".."))
_AGENT_PIPE = os.path.join(_ROOT, "usr", "lib", "mios", "agent-pipe")
if _AGENT_PIPE not in sys.path:
    sys.path.insert(0, _AGENT_PIPE)

import mios_mcp


def _run_async(coro):
    return asyncio.run(coro)


class TestMcpGatewayHandshake(unittest.TestCase):
    """Validates Declarative MCP server discovery, stdio/SSE protocol handshakes,
    OpenAI function schema conversion, and dynamic tool call dispatch."""

    def setUp(self):
        """Reset internal registries for test isolation."""
        mios_mcp._MCP_CLIENT_SERVERS.clear()
        mios_mcp._MCP_STDIO_CLIENTS.clear()
        mios_mcp._MCP_HTTP_CLIENTS.clear()
        mios_mcp.configure(
            mcp_client_tools={},
            mcp_client_lock=asyncio.Lock(),
            mcp_embed_new_tools=None,
            invalidate_worker_cache=lambda: None,
        )

    # -----------------------------------------------------------------------
    # 1. Declarative TOML Server Discovery
    # -----------------------------------------------------------------------

    def test_load_servers_from_toml_dict(self):
        """Verify parsing [mcp.servers] from a dictionary source."""
        toml_dict = {
            "mcp": {
                "protocol_version": "2025-11-25",
                "servers": {
                    "playwright": {
                        "enabled": True,
                        "transport": "stdio",
                        "command": "npx",
                        "args": ["-y", "@playwright/mcp@0.0.76", "--headless"],
                        "cwd": "/var/lib/mios/ai",
                        "env": {"HOME": "/var/lib/mios/ai"},
                        "tier": "rare",
                        "namespace": "browser_",
                        "taint": "untrusted_web",
                        "allowed_tools": ["navigate", "click", "snapshot"],
                    },
                    "weather_api": {
                        "enabled": True,
                        "transport": "sse",
                        "url": "http://127.0.0.1:8000/sse",
                        "headers": {"Authorization": "Bearer ${WEATHER_API_KEY}"},
                        "tier": "common",
                    },
                    "disabled_svc": {
                        "enabled": False,
                        "transport": "stdio",
                        "command": "legacy_bin",
                    },
                }
            }
        }

        specs = mios_mcp.load_servers_from_toml(toml_dict)
        self.assertEqual(len(specs), 3)

        spec_map = {s.id: s for s in specs}
        self.assertIn("playwright", spec_map)
        self.assertIn("weather_api", spec_map)
        self.assertIn("disabled_svc", spec_map)

        pw = spec_map["playwright"]
        self.assertEqual(pw.transport, "stdio")
        self.assertEqual(pw.command, "npx")
        self.assertEqual(pw.args, ["-y", "@playwright/mcp@0.0.76", "--headless"])
        self.assertEqual(pw.cwd, "/var/lib/mios/ai")
        self.assertEqual(pw.env, {"HOME": "/var/lib/mios/ai"})
        self.assertEqual(pw.namespace, "browser_")
        self.assertEqual(pw.taint, "untrusted_web")
        self.assertEqual(pw.allowed_tools, ["navigate", "click", "snapshot"])
        self.assertTrue(pw.enabled)

        w = spec_map["weather_api"]
        self.assertEqual(w.transport, "sse")
        self.assertEqual(w.url, "http://127.0.0.1:8000/sse")
        self.assertEqual(w.headers, {"Authorization": "Bearer ${WEATHER_API_KEY}"})

        d = spec_map["disabled_svc"]
        self.assertFalse(d.enabled)

    def test_load_servers_from_toml_string(self):
        """Verify parsing raw TOML string syntax into McpServerSpec instances."""
        toml_text = """
[mcp]
protocol_version = "2025-11-25"

[mcp.servers.duckdb]
enabled = true
transport = "stdio"
command = "uvx"
args = ["mcp-server-motherduck", "--db-path", ":memory:"]
tier = "rare"
namespace = "duckdb_"

[mcp.servers.remote_hub]
enabled = true
transport = "http"
url = "http://localhost:9090/mcp"
"""
        specs = mios_mcp.load_servers_from_toml(toml_text)
        self.assertEqual(len(specs), 2)
        spec_map = {s.id: s for s in specs}

        self.assertIn("duckdb", spec_map)
        self.assertIn("remote_hub", spec_map)
        self.assertEqual(spec_map["duckdb"].command, "uvx")
        self.assertEqual(spec_map["remote_hub"].transport, "http")

    def test_load_servers_from_toml_file(self):
        """Verify loading MCP server definitions from a temporary TOML file on disk."""
        with tempfile.NamedTemporaryFile("w", suffix=".toml", delete=False, encoding="utf-8") as f:
            f.write("""
[mcp.servers.disk_server]
enabled = true
transport = "stdio"
command = "python"
args = ["-m", "disk_mcp"]
""")
            temp_path = f.name

        try:
            specs = mios_mcp.load_servers_from_toml(temp_path)
            self.assertEqual(len(specs), 1)
            self.assertEqual(specs[0].id, "disk_server")
            self.assertEqual(specs[0].command, "python")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_spec_serialization_roundtrip(self):
        """Verify McpServerSpec to_dict() and from_dict() fidelity."""
        original = mios_mcp.McpServerSpec(
            id="test_spec",
            transport="stdio",
            command="custom_bin",
            args=["--flag", "val"],
            env={"KEY": "VAL"},
            cwd="/tmp",
            enabled=True,
            tier="core",
            namespace="custom_",
            taint="safe",
            allowed_tools=["tool_a", "tool_b"],
            label="Custom Test Spec",
            examples=["run tool_a"],
            note="unit test spec",
        )

        d = original.to_dict()
        reconstructed = mios_mcp.McpServerSpec.from_dict(d)

        self.assertEqual(reconstructed.id, original.id)
        self.assertEqual(reconstructed.transport, original.transport)
        self.assertEqual(reconstructed.command, original.command)
        self.assertEqual(reconstructed.args, original.args)
        self.assertEqual(reconstructed.env, original.env)
        self.assertEqual(reconstructed.cwd, original.cwd)
        self.assertEqual(reconstructed.tier, original.tier)
        self.assertEqual(reconstructed.namespace, original.namespace)
        self.assertEqual(reconstructed.taint, original.taint)
        self.assertEqual(reconstructed.allowed_tools, original.allowed_tools)
        self.assertEqual(reconstructed.label, original.label)
        self.assertEqual(reconstructed.examples, original.examples)
        self.assertEqual(reconstructed.note, original.note)

    # -----------------------------------------------------------------------
    # 2. Strict OpenAI Function Schema Conversion
    # -----------------------------------------------------------------------

    def test_convert_mcp_to_openai_schema_basic(self):
        """Verify standard MCP inputSchema conversion to strict OpenAI tools definition."""
        mcp_tool = {
            "name": "calculate",
            "description": "Perform math calculation",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Math expression to evaluate",
                    },
                    "precision": {
                        "type": "integer",
                        "description": "Decimal precision",
                    },
                },
                "required": ["expression"],
            },
        }

        openai_tool = mios_mcp.convert_mcp_to_openai_schema(mcp_tool, server_id="math_srv")

        self.assertEqual(openai_tool["type"], "function")
        self.assertEqual(openai_tool["x-mios-mcp-server"], "math_srv")

        fn = openai_tool["function"]
        self.assertEqual(fn["name"], "mcp.math_srv.calculate")
        self.assertEqual(fn["description"], "Perform math calculation")
        self.assertTrue(fn["strict"])

        params = fn["parameters"]
        self.assertEqual(params["type"], "object")
        self.assertFalse(params["additionalProperties"])
        self.assertEqual(set(params["required"]), {"expression", "precision"})

        # Required property retains clean type
        self.assertEqual(params["properties"]["expression"]["type"], "string")
        # Optional property widened to nullable
        self.assertIn("null", params["properties"]["precision"]["type"])

    def test_convert_mcp_to_openai_schema_nested_objects(self):
        """Verify strict schema transformation handles nested objects and arrays."""
        mcp_tool = {
            "name": "create_user",
            "description": "Create a user account",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "user": {
                        "type": "object",
                        "properties": {
                            "username": {"type": "string"},
                            "profile": {
                                "type": "object",
                                "properties": {
                                    "bio": {"type": "string"},
                                    "age": {"type": "integer"},
                                },
                                "required": ["bio"],
                            },
                        },
                        "required": ["username"],
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                            },
                            "required": ["name"],
                        },
                    },
                },
                "required": ["user"],
            },
        }

        openai_tool = mios_mcp.convert_mcp_to_openai_schema(mcp_tool, server_id="users")
        params = openai_tool["function"]["parameters"]

        # Check top-level strictness
        self.assertFalse(params["additionalProperties"])
        self.assertIn("tags", params["required"])

        # Check nested user object
        user_prop = params["properties"]["user"]
        self.assertFalse(user_prop["additionalProperties"])
        self.assertIn("profile", user_prop["required"])

        # Check deeply nested profile object
        profile_prop = user_prop["properties"]["profile"]
        self.assertFalse(profile_prop["additionalProperties"])
        self.assertEqual(set(profile_prop["required"]), {"bio", "age"})

        # Check array item strictness
        tag_items = params["properties"]["tags"]["items"]
        self.assertFalse(tag_items["additionalProperties"])
        self.assertEqual(tag_items["required"], ["name"])

    def test_convert_mcp_to_openai_schema_fallback_cases(self):
        """Verify graceful fallback on empty, missing, or malformed schema fields."""
        tool_empty = {"name": "ping"}
        out = mios_mcp.convert_mcp_to_openai_schema(tool_empty)
        self.assertEqual(out["function"]["name"], "ping")
        self.assertEqual(out["function"]["description"], "MCP tool ping")
        self.assertEqual(out["function"]["parameters"]["type"], "object")
        self.assertEqual(out["function"]["parameters"]["properties"], {})
        self.assertEqual(out["function"]["parameters"]["required"], [])
        self.assertFalse(out["function"]["parameters"]["additionalProperties"])

    # -----------------------------------------------------------------------
    # 3. Real Subprocess Stdio MCP Server Handshake & Execution
    # -----------------------------------------------------------------------

    def test_stdio_handshake_discovery_and_execution(self):
        """Spawn a genuine Python MCP server subprocess over stdio, verify JSON-RPC 2.0
        initialize handshake, notifications/initialized, tools/list discovery, and
        dynamic tool call execution dispatch."""

        # Self-contained mock stdio MCP server script
        mock_server_code = """
import sys, json

for line in sys.stdin:
    if not line.strip():
        continue
    try:
        req = json.loads(line)
    except Exception:
        continue
    rid = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    if method == "initialize":
        resp = {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": "2025-11-25",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mock-calc-server", "version": "1.0.0"}
            }
        }
        sys.stdout.write(json.dumps(resp) + "\\n")
        sys.stdout.flush()
    elif method == "notifications/initialized":
        pass
    elif method == "tools/list":
        resp = {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "tools": [
                    {
                        "name": "add_numbers",
                        "description": "Add two numbers together",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "a": {"type": "number"},
                                "b": {"type": "number"}
                            },
                            "required": ["a", "b"]
                        }
                    },
                    {
                        "name": "format_greeting",
                        "description": "Format greeting string",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "shout": {"type": "boolean"}
                            },
                            "required": ["name"]
                        }
                    }
                ]
            }
        }
        sys.stdout.write(json.dumps(resp) + "\\n")
        sys.stdout.flush()
    elif method == "tools/call":
        tname = params.get("name")
        args = params.get("arguments") or {}
        if tname == "add_numbers":
            a = float(args.get("a", 0))
            b = float(args.get("b", 0))
            resp = {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {"content": [{"type": "text", "text": str(a + b)}], "isError": False}
            }
        elif tname == "format_greeting":
            name = str(args.get("name", "world"))
            msg = f"HELLO {name.upper()}!" if args.get("shout") else f"Hello {name}!"
            resp = {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {"content": [{"type": "text", "text": msg}], "isError": False}
            }
        else:
            resp = {
                "jsonrpc": "2.0",
                "id": rid,
                "error": {"code": -32601, "message": f"Tool '{tname}' not found"}
            }
        sys.stdout.write(json.dumps(resp) + "\\n")
        sys.stdout.flush()
"""

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(mock_server_code)
            mock_script_path = f.name

        try:
            async def _run_test():
                # 1. Configure and probe server
                server_cfg = {
                    "id": "calc_srv",
                    "transport": "stdio",
                    "command": sys.executable,
                    "args": [mock_script_path],
                    "enabled": True,
                    "namespace": "calc_",
                    "tier": "core",
                }

                await mios_mcp._mcp_probe_server(server_cfg)

                # 2. Verify server state
                srv_state = mios_mcp._MCP_CLIENT_SERVERS.get("calc_srv")
                self.assertIsNotNone(srv_state)
                self.assertEqual(srv_state["status"], "ready")
                self.assertEqual(srv_state["protocolVersion"], "2025-11-25")
                self.assertEqual(srv_state["tools_count"], 2)

                # 3. Verify registered tools
                async with mios_mcp._MCP_CLIENT_LOCK:
                    tools = dict(mios_mcp._MCP_CLIENT_TOOLS)

                self.assertIn("mcp.calc_srv.add_numbers", tools)
                self.assertIn("mcp.calc_srv.format_greeting", tools)

                add_tool = tools["mcp.calc_srv.add_numbers"]
                self.assertEqual(add_tool["description"], "Add two numbers together")
                self.assertEqual(add_tool["namespace"], "calc_")

                # 4. Dispatch tool call: add_numbers
                res_add = await mios_mcp.dispatch_tool_call(
                    server_id="calc_srv",
                    tool_name="add_numbers",
                    arguments={"a": 15.5, "b": 24.5},
                )
                self.assertNotIn("error", res_add)
                self.assertEqual(res_add["content"][0]["text"], "40.0")

                # 5. Dispatch tool call via namespaced key: format_greeting
                res_greet = await mios_mcp._mcp_call_tool(
                    "mcp.calc_srv.format_greeting",
                    {"name": "Developer", "shout": True},
                )
                self.assertNotIn("error", res_greet)
                self.assertEqual(res_greet["content"][0]["text"], "HELLO DEVELOPER!")

                # 6. Dispatch tool call with default optional argument
                res_greet_default = await mios_mcp.dispatch_tool_call(
                    server_id="calc_srv",
                    tool_name="format_greeting",
                    arguments={"name": "Alice"},
                )
                self.assertNotIn("error", res_greet_default)
                self.assertEqual(res_greet_default["content"][0]["text"], "Hello Alice!")

                # 7. Clean shutdown
                cli = mios_mcp._MCP_STDIO_CLIENTS.get("calc_srv")
                if cli is not None:
                    await cli.close()
                    self.assertIsNone(cli.proc)

            _run_async(_run_test())

        finally:
            if os.path.exists(mock_script_path):
                os.remove(mock_script_path)

    # -----------------------------------------------------------------------
    # 4. SSE / HTTP Mock Transport Handshake & Execution
    # -----------------------------------------------------------------------

    def test_http_sse_handshake_and_dispatch(self):
        """Verify HTTP/SSE JSON-RPC transport handshake, tools/list, and execution."""
        class _MockHttpClient:
            async def post(self, url, json=None, headers=None, timeout=30.0):
                body = json or {}
                method = body.get("method")
                rid = body.get("id", 1)
                params = body.get("params") or {}

                if method == "initialize":
                    return mios_mcp.JSONResponse({
                        "jsonrpc": "2.0",
                        "id": rid,
                        "result": {
                            "protocolVersion": "2025-11-25",
                            "serverInfo": {"name": "mock-sse-hub"},
                        },
                    })
                elif method == "tools/list":
                    return mios_mcp.JSONResponse({
                        "jsonrpc": "2.0",
                        "id": rid,
                        "result": {
                            "tools": [
                                {
                                    "name": "lookup_ip",
                                    "description": "Look up geolocation for IP address",
                                    "inputSchema": {
                                        "type": "object",
                                        "properties": {"ip": {"type": "string"}},
                                        "required": ["ip"],
                                    },
                                }
                            ]
                        },
                    })
                elif method == "tools/call":
                    ip = params.get("arguments", {}).get("ip", "127.0.0.1")
                    return mios_mcp.JSONResponse({
                        "jsonrpc": "2.0",
                        "id": rid,
                        "result": {
                            "content": [{"type": "text", "text": f"Loc: {ip} -> Localhost"}],
                            "isError": False,
                        },
                    })
                return mios_mcp.JSONResponse({"jsonrpc": "2.0", "id": rid, "result": {}})

        async def _run_test():
            # Inject mock client factory
            mios_mcp.configure(get_client=lambda: _MockHttpClient())

            server_cfg = {
                "id": "geo_hub",
                "transport": "http",
                "url": "http://127.0.0.1:9191/mcp",
                "enabled": True,
            }

            await mios_mcp._mcp_probe_server(server_cfg)

            srv_state = mios_mcp._MCP_CLIENT_SERVERS.get("geo_hub")
            self.assertIsNotNone(srv_state)
            self.assertEqual(srv_state["status"], "ready")
            self.assertEqual(srv_state["tools_count"], 1)

            # Dispatch tool call
            res = await mios_mcp.dispatch_tool_call(
                server_id="geo_hub",
                tool_name="lookup_ip",
                arguments={"ip": "192.168.1.1"},
            )
            self.assertNotIn("error", res)
            self.assertIn("192.168.1.1", res["content"][0]["text"])

        _run_async(_run_test())

    # -----------------------------------------------------------------------
    # 5. Error Handling & Edge Cases
    # -----------------------------------------------------------------------

    def test_dispatch_unknown_server_or_tool(self):
        """Verify proper error structure when querying unknown servers or tools."""
        async def _run_test():
            res = await mios_mcp.dispatch_tool_call(
                server_id="nonexistent_srv",
                tool_name="missing_tool",
                arguments={},
            )
            self.assertIn("error", res)
            self.assertEqual(res["code"], -32601)
            self.assertIn("unknown MCP server", res["error"])

        _run_async(_run_test())

    def test_stdio_timeout_handling(self):
        """Verify stdio timeout handling returns structured timeout error."""
        cli = mios_mcp._McpStdioClient("hang_srv", "dummy_cmd")

        async def _run_test():
            # Simulate a timeout when awaiting response
            async def _fake_send(body):
                pass  # never replies

            cli.proc = mock.MagicMock()
            cli._send = _fake_send
            cli._inited = True

            res = await cli._await_rpc("slow_method", {}, timeout_s=0.05)
            self.assertIn("error", res)
            self.assertEqual(res["error"]["code"], -32000)
            self.assertIn("timeout", res["error"]["message"])

        _run_async(_run_test())

    # -----------------------------------------------------------------------
    # 6. Declarative McpGateway Full Lifecycle
    # -----------------------------------------------------------------------

    def test_mcp_gateway_lifecycle(self):
        """Verify McpGateway management, schema queries, and shutdown lifecycle."""
        gateway = mios_mcp.McpGateway()
        toml_content = """
[mcp.servers.local_tool]
enabled = true
transport = "stdio"
command = "echo"
args = ["test"]
"""
        gateway.load_from_toml(toml_content)
        self.assertIn("local_tool", gateway.specs)

        # Manually register mock tool to test schema retrieval
        mios_mcp._MCP_CLIENT_TOOLS["mcp.local_tool.sample"] = {
            "server_id": "local_tool",
            "tool": "sample",
            "description": "Sample test tool",
            "inputSchema": {
                "type": "object",
                "properties": {"val": {"type": "string"}},
                "required": ["val"],
            },
        }

        openai_tools = gateway.get_openai_tools()
        self.assertTrue(len(openai_tools) >= 1)
        sample_tool = next(t for t in openai_tools if t["function"]["name"] == "mcp.local_tool.sample")
        self.assertEqual(sample_tool["function"]["strict"], True)
        self.assertEqual(sample_tool["function"]["description"], "Sample test tool")

        _run_async(gateway.shutdown())
        self.assertEqual(len(mios_mcp._MCP_STDIO_CLIENTS), 0)

    # -----------------------------------------------------------------------
    # 7. Allowed Tools Filter & Environment Rendering
    # -----------------------------------------------------------------------

    def test_stdio_allowed_tools_filtering(self):
        """Verify allowed_tools filters discovered tools correctly."""
        mock_server_code = """
import sys, json
for line in sys.stdin:
    if not line.strip(): continue
    req = json.loads(line)
    rid = req.get("id")
    method = req.get("method")
    if method == "initialize":
        sys.stdout.write(json.dumps({"jsonrpc":"2.0","id":rid,"result":{"protocolVersion":"2025-11-25","serverInfo":{"name":"filter-srv"}}}) + "\\n")
        sys.stdout.flush()
    elif method == "notifications/initialized":
        pass
    elif method == "tools/list":
        sys.stdout.write(json.dumps({"jsonrpc":"2.0","id":rid,"result":{"tools":[{"name":"allowed_one"},{"name":"blocked_two"}]}}) + "\\n")
        sys.stdout.flush()
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(mock_server_code)
            mock_path = f.name

        try:
            async def _run_test():
                cfg = {
                    "id": "filter_test",
                    "transport": "stdio",
                    "command": sys.executable,
                    "args": [mock_path],
                    "allowed_tools": ["allowed_one"],
                }
                await mios_mcp._mcp_probe_server(cfg)
                srv = mios_mcp._MCP_CLIENT_SERVERS.get("filter_test")
                self.assertEqual(srv["tools_count"], 1)

                async with mios_mcp._MCP_CLIENT_LOCK:
                    tools = dict(mios_mcp._MCP_CLIENT_TOOLS)
                self.assertIn("mcp.filter_test.allowed_one", tools)
                self.assertNotIn("mcp.filter_test.blocked_two", tools)

                cli = mios_mcp._MCP_STDIO_CLIENTS.get("filter_test")
                if cli:
                    await cli.close()

            _run_async(_run_test())
        finally:
            if os.path.exists(mock_path):
                os.remove(mock_path)

    def test_env_header_rendering(self):
        """Verify environment variable substitution in headers and configs."""
        os.environ["MIOS_TEST_ENV_VAR_1"] = "bearer_token_123"
        try:
            headers = {"Authorization": "Bearer ${MIOS_TEST_ENV_VAR_1}", "X-Custom": "static"}
            rendered = mios_mcp._mcp_render_headers(headers)
            self.assertEqual(rendered["Authorization"], "Bearer bearer_token_123")
            self.assertEqual(rendered["X-Custom"], "static")
        finally:
            os.environ.pop("MIOS_TEST_ENV_VAR_1", None)

    def test_fastapi_endpoints_logic(self):
        """Verify REST API response handlers for clients, tools, and dispatch."""
        mios_mcp._MCP_CLIENT_SERVERS["test_srv"] = {
            "id": "test_srv",
            "status": "ready",
            "protocolVersion": "2025-11-25",
            "tools_count": 1,
        }
        mios_mcp._MCP_CLIENT_TOOLS["mcp.test_srv.test_tool"] = {
            "server_id": "test_srv",
            "tool": "test_tool",
            "description": "Test tool desc",
            "inputSchema": {"type": "object"},
        }

        async def _run_test():
            # 1. Clients logic
            clients_resp = await mios_mcp.mcp_clients_logic()
            clients_data = json.loads(clients_resp.body)
            self.assertEqual(clients_data["object"], "mios.mcp.clients")
            self.assertEqual(len(clients_data["servers"]), 1)

            # 2. Tools list logic
            tools_resp = await mios_mcp.mcp_tools_list_logic()
            tools_data = json.loads(tools_resp.body)
            self.assertEqual(tools_data["object"], "mios.mcp.tools")
            self.assertEqual(len(tools_data["tools"]), 1)
            self.assertEqual(tools_data["tools"][0]["name"], "mcp.test_srv.test_tool")

            # 3. Dispatch logic validation
            class _FakeRequest:
                def __init__(self, data):
                    self._data = data
                async def json(self):
                    return self._data

            # Missing tool name returns 400
            bad_resp = await mios_mcp.mcp_dispatch_logic(_FakeRequest({}))
            self.assertEqual(bad_resp.status_code, 400)

        _run_async(_run_test())


if __name__ == "__main__":
    unittest.main(verbosity=2)

#!/usr/bin/env python3
# AI-hint: Stdlib unit test for the MCP JSON-RPC transports -- header env expansion, SSE and JSON response decoding, and error mapping (mios_mcp_transport).
# AI-doc: usr/share/doc/mios/manual/agent-pipe.md
"""Unit tests for mios_mcp_transport. Pure stdlib plus a stub HTTP client."""
import asyncio
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mios_mcp_transport as T


class _Resp:
    """The minimum of an httpx response that _mcp_http_rpc actually reads."""

    def __init__(self, status_code=200, payload=None, content_type="application/json", text=""):
        self.status_code = status_code
        self.headers = {"content-type": content_type}
        self.text = text
        self._payload = payload

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class _StubClient:
    def __init__(self, resp=None, raise_exc=None):
        self._resp = resp
        self._raise = raise_exc
        self.calls = []

    async def post(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers, "timeout": timeout})
        if self._raise is not None:
            raise self._raise
        return self._resp


def _with_client(client):
    """Install a fake mios_mcp whose _resolve_http_client returns `client`.

    _mcp_http_rpc imports mios_mcp INSIDE the call precisely so the factory can
    be rebound, so a module injected into sys.modules is the honest seam here.
    """
    mod = types.ModuleType("mios_mcp")

    async def _resolve_http_client():
        return client

    mod._resolve_http_client = _resolve_http_client
    sys.modules["mios_mcp"] = mod


class RenderHeadersTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("MIOS_TEST_TOKEN", None)

    def test_expands_an_env_placeholder(self):
        os.environ["MIOS_TEST_TOKEN"] = "s3cret"
        out = T._mcp_render_headers({"Authorization": "Bearer ${MIOS_TEST_TOKEN}"})
        self.assertEqual(out["Authorization"], "Bearer s3cret")

    def test_an_unset_var_expands_to_empty_not_to_the_placeholder(self):
        # Leaving the literal ${VAR} in place would send "Bearer ${VAR}" to the
        # server as if it were a credential.
        out = T._mcp_render_headers({"Authorization": "Bearer ${MIOS_TEST_TOKEN}"})
        self.assertEqual(out["Authorization"], "Bearer ")
        self.assertNotIn("${", out["Authorization"])

    def test_expands_several_placeholders_in_one_value(self):
        os.environ["MIOS_TEST_TOKEN"] = "a"
        out = T._mcp_render_headers({"X": "${MIOS_TEST_TOKEN}/${MIOS_TEST_TOKEN}"})
        self.assertEqual(out["X"], "a/a")

    def test_lowercase_and_malformed_placeholders_are_left_alone(self):
        out = T._mcp_render_headers({"a": "${lower}", "b": "$NOBRACE", "c": "${}"})
        self.assertEqual(out["a"], "${lower}")
        self.assertEqual(out["b"], "$NOBRACE")
        self.assertEqual(out["c"], "${}")

    def test_non_string_values_are_stringified(self):
        self.assertEqual(T._mcp_render_headers({"n": 7, "b": True}), {"n": "7", "b": "True"})

    def test_none_and_empty_yield_an_empty_mapping(self):
        self.assertEqual(T._mcp_render_headers(None), {})
        self.assertEqual(T._mcp_render_headers({}), {})


class HttpRpcTests(unittest.TestCase):
    def tearDown(self):
        sys.modules.pop("mios_mcp", None)

    def test_request_envelope_is_jsonrpc_2_0(self):
        c = _StubClient(_Resp(payload={"jsonrpc": "2.0", "id": 5, "result": {}}))
        _with_client(c)
        asyncio.run(T._mcp_http_rpc("http://x", {}, "tools/list", params={"p": 1}, rid=5))
        sent = c.calls[0]["json"]
        self.assertEqual(sent, {"jsonrpc": "2.0", "id": 5, "method": "tools/list", "params": {"p": 1}})

    def test_params_are_omitted_when_none(self):
        c = _StubClient(_Resp(payload={"result": {}}))
        _with_client(c)
        asyncio.run(T._mcp_http_rpc("http://x", {}, "ping"))
        self.assertNotIn("params", c.calls[0]["json"])

    def test_default_headers_are_added_without_overriding_callers(self):
        c = _StubClient(_Resp(payload={"result": {}}))
        _with_client(c)
        asyncio.run(T._mcp_http_rpc("http://x", {"Content-Type": "application/custom"}, "ping"))
        h = c.calls[0]["headers"]
        self.assertEqual(h["Content-Type"], "application/custom", "a caller's value wins")
        self.assertIn("text/event-stream", h["Accept"])

    def test_caller_headers_are_not_mutated(self):
        c = _StubClient(_Resp(payload={"result": {}}))
        _with_client(c)
        caller = {"Authorization": "Bearer x"}
        asyncio.run(T._mcp_http_rpc("http://x", caller, "ping"))
        self.assertEqual(caller, {"Authorization": "Bearer x"})

    def test_json_result_is_returned(self):
        _with_client(_StubClient(_Resp(payload={"result": {"tools": []}})))
        self.assertEqual(asyncio.run(T._mcp_http_rpc("http://x", {}, "tools/list")),
                         {"result": {"tools": []}})

    def test_a_non_200_becomes_a_jsonrpc_error_carrying_the_status(self):
        _with_client(_StubClient(_Resp(status_code=503, text="upstream down")))
        out = asyncio.run(T._mcp_http_rpc("http://x", {}, "ping"))
        self.assertEqual(out["error"]["code"], 503)
        self.assertIn("upstream down", out["error"]["message"])

    def test_a_transport_error_becomes_a_jsonrpc_error_and_does_not_raise(self):
        _with_client(_StubClient(raise_exc=T.httpx.HTTPError("boom")))
        out = asyncio.run(T._mcp_http_rpc("http://x", {}, "ping"))
        self.assertEqual(out["error"]["code"], -32000)
        self.assertIn("boom", out["error"]["message"])

    def test_sse_data_event_is_decoded(self):
        _with_client(_StubClient(_Resp(content_type="text/event-stream",
                                       text='event: message\ndata: {"result": 1}\n\n')))
        self.assertEqual(asyncio.run(T._mcp_http_rpc("http://x", {}, "ping")), {"result": 1})

    def test_sse_with_no_data_event_is_an_error_not_a_silent_empty(self):
        _with_client(_StubClient(_Resp(content_type="text/event-stream", text="event: ping\n\n")))
        out = asyncio.run(T._mcp_http_rpc("http://x", {}, "ping"))
        self.assertEqual(out["error"]["code"], -32700)

    def test_sse_skips_an_undecodable_data_line_and_takes_the_next(self):
        _with_client(_StubClient(_Resp(content_type="text/event-stream",
                                       text='data: not-json\n\ndata: {"result": 1}\n\n')))
        self.assertEqual(asyncio.run(T._mcp_http_rpc("http://x", {}, "ping")), {"result": 1})

    def test_a_non_json_body_becomes_a_parse_error_not_an_exception(self):
        _with_client(_StubClient(_Resp(payload=None, text="<html>")))
        out = asyncio.run(T._mcp_http_rpc("http://x", {}, "ping"))
        self.assertEqual(out["error"]["code"], -32700)


class StdioClientTests(unittest.TestCase):
    def test_request_ids_are_monotonic_and_start_at_one(self):
        c = T._McpStdioClient("sid", "/bin/true")
        self.assertEqual([c._next_id() for _ in range(3)], [1, 2, 3])

    def test_a_fresh_client_is_not_initialised(self):
        c = T._McpStdioClient("sid", "/bin/true")
        self.assertFalse(c._inited)
        self.assertEqual(c._pending, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)

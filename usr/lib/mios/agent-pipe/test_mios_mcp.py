# AI-hint: Stdlib unit test for mios_mcp -- the external-MCP CONSUME client extracted from server.py (refactor R-MCP). Hermetically stubs httpx + fastapi.responses + the injected deps (HTTP client / MCP-tool registry+lock / embedder / worker-cache invalidator) with NO network, DB, or subprocess, and asserts: the layered registry read (later overlay REPLACES by id), the ${ENV} header expansion, _mcp_http_rpc parsing BOTH application/json and text/event-stream responses, the per-server probe PROJECTION (tools/list -> mcp.<sid>.<tool> registry entries carrying namespace/tier/taint/examples + cache-invalidate + embed side-effects), the /v1/mcp/clients + /v1/mcp/tools + /v1/mcp/dispatch route-logic shapes, and the _McpStdioClient self-heal state machine (initialize once, skip re-init while alive, respawn+re-initialize after the subprocess dies).
# AI-related: ./mios_mcp.py, ./server.py
# AI-functions: _run, test_render_headers, test_load_registry_layered, test_http_rpc_json, test_http_rpc_sse, test_probe_server_projection, test_route_logic_shapes, test_call_tool_unknown, test_stdio_self_heal
"""Offline unit tests for mios_mcp (no network, no DB, no real subprocess)."""

import asyncio
import json as _json
import os
import sys
import tempfile
import types


# -- Hermetic 3rd-party stubs (stdlib-only run): install BEFORE importing mios_mcp.
_httpx = types.ModuleType("httpx")


class _HTTPError(Exception):
    pass


_httpx.HTTPError = _HTTPError
sys.modules["httpx"] = _httpx

_resp_mod = types.ModuleType("fastapi.responses")


class _JSONResponse:
    def __init__(self, content=None, status_code=200, **_kw):
        self.status_code = status_code
        self._content = content
        self.body = _json.dumps(content).encode("utf-8")


_resp_mod.JSONResponse = _JSONResponse
sys.modules["fastapi.responses"] = _resp_mod
_fa = types.ModuleType("fastapi")
_fa.responses = _resp_mod
_fa.Request = object


# mios_mcp builds an APIRouter for its /v1/mcp/* routes (R13); the route handlers are
# decorated at import time. This stub returns each wrapped handler unchanged so the
# module imports and the *_logic the tests exercise stay reachable -- no real FastAPI.
class _StubRouter:
    def __getattr__(self, _name):
        def _decorator_factory(*_a, **_k):
            def _wrap(fn=None):
                return fn if fn is not None else (lambda f: f)
            return _wrap
        return _decorator_factory


_fa.APIRouter = lambda *a, **k: _StubRouter()
sys.modules.setdefault("fastapi", _fa)

import mios_mcp as mc  # noqa: E402


def _run(coro):
    return asyncio.run(coro)


class _Resp:
    def __init__(self, status=200, ct="application/json", payload=None, text=""):
        self.status_code = status
        self.headers = {"content-type": ct}
        self._payload = payload
        self.text = text

    def json(self):
        return self._payload


def _client_returning(resp):
    class _Client:
        async def post(self, *_a, **_k):
            return resp
    client = _Client()

    async def _get():
        return client
    return _get


def _embed_calls(box):
    async def _embed():
        box.append(1)
    return _embed


def _reset_registry(servers_dict=None, tools_dict=None, embed_box=None,
                    invalidated_box=None):
    """Inject fresh server-resident deps so each test is isolated."""
    inval = invalidated_box if invalidated_box is not None else []
    mc._MCP_CLIENT_SERVERS.clear()
    mc.configure(
        mcp_client_tools=tools_dict if tools_dict is not None else {},
        mcp_client_lock=asyncio.Lock(),
        mcp_embed_new_tools=_embed_calls(embed_box if embed_box is not None else []),
        invalidate_worker_cache=(lambda: inval.append(1)),
    )


def test_render_headers():
    os.environ["MIOS_TEST_MCP_TOKEN"] = "sekret"
    out = mc._mcp_render_headers({"Authorization": "Bearer ${MIOS_TEST_MCP_TOKEN}",
                                  "X-Plain": "v"})
    assert out["Authorization"] == "Bearer sekret", out
    assert out["X-Plain"] == "v", out
    # unknown var expands to empty (never leaves the ${...} literal).
    out2 = mc._mcp_render_headers({"H": "${MIOS_NO_SUCH_VAR_XYZ}"})
    assert out2["H"] == "", out2


def test_load_registry_layered():
    with tempfile.TemporaryDirectory() as d:
        p_vendor = os.path.join(d, "vendor.json")
        p_user = os.path.join(d, "user.json")
        with open(p_vendor, "w", encoding="utf-8") as f:
            _json.dump({"servers": [{"id": "a", "url": "http://v"},
                                    {"id": "b", "url": "http://b"}]}, f)
        with open(p_user, "w", encoding="utf-8") as f:
            # user overlay REPLACES "a" (disables it) -- not a merge.
            _json.dump({"servers": [{"id": "a", "enabled": False}]}, f)
        orig = mc._MCP_REGISTRY_PATHS
        mc._MCP_REGISTRY_PATHS = [p_vendor, p_user]
        try:
            reg = mc._mcp_load_registry()
        finally:
            mc._MCP_REGISTRY_PATHS = orig
        by_id = {s["id"]: s for s in reg}
        assert set(by_id) == {"a", "b"}, by_id
        assert by_id["a"].get("enabled") is False, by_id["a"]
        assert "url" not in by_id["a"], by_id["a"]      # fully replaced, not merged


def test_http_rpc_json():
    mc.configure(get_client=_client_returning(
        _Resp(ct="application/json", payload={"jsonrpc": "2.0", "id": 1,
                                              "result": {"ok": True}})))
    out = _run(mc._mcp_http_rpc("http://x", {}, "initialize", params={}))
    assert out["result"]["ok"] is True, out


def test_http_rpc_sse():
    sse = "event: message\ndata: {\"jsonrpc\":\"2.0\",\"id\":1,\"result\":{\"sse\":1}}\n\n"
    mc.configure(get_client=_client_returning(
        _Resp(ct="text/event-stream", text=sse)))
    out = _run(mc._mcp_http_rpc("http://x", {}, "tools/list"))
    assert out["result"]["sse"] == 1, out


def test_probe_server_projection():
    embed_box, inval_box = [], []
    tools = {}
    _reset_registry(tools_dict=tools, embed_box=embed_box, invalidated_box=inval_box)

    async def _fake_rpc(url, headers, method, params=None, rid=1, timeout_s=30.0):
        if method == "initialize":
            return {"result": {"protocolVersion": "2025-06-18",
                               "serverInfo": {"name": "srv"}}}
        if method == "tools/list":
            return {"result": {"tools": [
                {"name": "query", "description": "run SQL",
                 "inputSchema": {"type": "object"}},
                {"name": "ping", "description": "ping"},
            ]}}
        return {"error": {"code": -32000, "message": "unexpected"}}

    orig = mc._mcp_http_rpc
    mc._mcp_http_rpc = _fake_rpc
    try:
        _run(mc._mcp_probe_server({
            "id": "duck", "url": "http://duck", "transport": "http",
            "namespace": "duckdb_", "tier": "common", "taint": "ro",
            "examples": ["select 1"]}))
    finally:
        mc._mcp_http_rpc = orig
    # projection: every remote tool registered namespaced mcp.<sid>.<tool>.
    assert "mcp.duck.query" in tools and "mcp.duck.ping" in tools, tools
    ent = tools["mcp.duck.query"]
    assert ent["server_id"] == "duck" and ent["tool"] == "query", ent
    assert ent["namespace"] == "duckdb_" and ent["tier"] == "common", ent
    assert ent["taint"] == "ro" and ent["examples"] == ["select 1"], ent
    assert ent["url"] == "http://duck", ent
    # per-server state + side effects.
    st = mc._MCP_CLIENT_SERVERS["duck"]
    assert st["status"] == "ready" and st["tools_count"] == 2, st
    assert st["protocolVersion"] == "2025-06-18", st
    assert embed_box and inval_box, (embed_box, inval_box)


def test_route_logic_shapes():
    tools = {"mcp.s.t": {"server_id": "s", "tool": "t", "description": "d",
                         "inputSchema": {"type": "object"}, "url": "http://s"}}
    _reset_registry(tools_dict=tools)
    mc._MCP_CLIENT_SERVERS["s"] = {"id": "s", "status": "ready", "tools_count": 1}

    cl = _json.loads(_run(mc.mcp_clients_logic()).body)
    assert cl["object"] == "mios.mcp.clients" and cl["tools_total"] == 1, cl
    assert cl["servers"][0]["id"] == "s", cl

    tl = _json.loads(_run(mc.mcp_tools_list_logic()).body)
    assert tl["object"] == "mios.mcp.tools", tl
    assert tl["tools"][0]["name"] == "mcp.s.t", tl

    # dispatch: missing tool -> 400; the call forwarder is stubbed for the happy path.
    class _Req:
        def __init__(self, body):
            self._b = body

        async def json(self):
            return self._b

    bad = _run(mc.mcp_dispatch_logic(_Req({})))
    assert bad.status_code == 400, bad.status_code

    async def _fake_call(key, args):
        return {"called": key, "args": args}
    orig = mc._mcp_call_tool
    mc._mcp_call_tool = _fake_call
    try:
        ok = _json.loads(_run(mc.mcp_dispatch_logic(_Req({"tool": "mcp.s.t",
                                                          "args": {"x": 1}}))).body)
    finally:
        mc._mcp_call_tool = orig
    assert ok["called"] == "mcp.s.t" and ok["args"] == {"x": 1}, ok


def test_call_tool_unknown():
    _reset_registry(tools_dict={})
    out = _run(mc._mcp_call_tool("mcp.nope.x", {}))
    assert "error" in out and "unknown" in out["error"], out


def test_stdio_self_heal():
    cli = mc._McpStdioClient("sid", "cmd", [], {}, None)
    spawns = []

    class _FakeProc:
        def __init__(self):
            self.returncode = None

    async def _fake_spawn():
        spawns.append(1)
        cli.proc = _FakeProc()

    async def _fake_await_rpc(method, params, timeout_s):
        return {"result": {"protocolVersion": "p"}}

    async def _fake_send(body):
        return None

    cli._spawn = _fake_spawn
    cli._await_rpc = _fake_await_rpc
    cli._send = _fake_send

    # first session: spawns once + initializes.
    _run(cli._ensure_session())
    assert cli._inited is True and len(spawns) == 1, spawns
    # still alive + inited -> the guard short-circuits, NO respawn.
    _run(cli._ensure_session())
    assert len(spawns) == 1, spawns
    # subprocess dies -> next call must respawn AND re-initialize (self-heal).
    cli.proc.returncode = 0
    _run(cli._ensure_session())
    assert len(spawns) == 2 and cli._inited is True, spawns
    # an initialize that errors leaves the session un-inited (fail-closed).
    async def _err_rpc(method, params, timeout_s):
        return {"error": {"code": -32000, "message": "boom"}}
    cli._await_rpc = _err_rpc
    cli.proc.returncode = 0
    _run(cli._ensure_session())
    assert cli._inited is False, "errored initialize must not mark inited"


def test_declared_protocol_version_is_current():
    # MiOS DECLARES the current MCP revision as the latest it offers. SSOT:
    # [mcp].protocol_version / env MIOS_MCP_PROTOCOL_VERSION (default = current).
    assert mc.MCP_PROTOCOL_VERSION == "2025-11-25", mc.MCP_PROTOCOL_VERSION


def test_initialize_advertises_current_version():
    # strict-OUT: the http initialize handshake SENDS the declared current revision
    # (not a scattered literal) -- read from the one SSOT constant.
    _reset_registry(tools_dict={})
    sent = {}

    async def _fake_rpc(url, headers, method, params=None, rid=1, timeout_s=30.0):
        if method == "initialize":
            sent["version"] = (params or {}).get("protocolVersion")
            return {"result": {"protocolVersion": (params or {}).get("protocolVersion"),
                               "serverInfo": {"name": "s"}}}
        return {"result": {"tools": []}}

    orig = mc._mcp_http_rpc
    mc._mcp_http_rpc = _fake_rpc
    try:
        _run(mc._mcp_probe_server({"id": "s", "url": "http://s", "transport": "http"}))
    finally:
        mc._mcp_http_rpc = orig
    assert sent["version"] == mc.MCP_PROTOCOL_VERSION == "2025-11-25", sent


def test_back_compat_negotiation_accepts_older_revision():
    # liberal-IN: a server answering with an OLDER revision (the previous stable
    # one) is accepted as-returned -- status ready, tools registered. MiOS never
    # rejects/hard-breaks a peer that speaks an older revision.
    tools = {}
    _reset_registry(tools_dict=tools)

    async def _fake_rpc(url, headers, method, params=None, rid=1, timeout_s=30.0):
        if method == "initialize":
            return {"result": {"protocolVersion": "2025-06-18",
                               "serverInfo": {"name": "old"}}}
        if method == "tools/list":
            return {"result": {"tools": [{"name": "t", "description": "d"}]}}
        return {"error": {"code": -32000, "message": "x"}}

    orig = mc._mcp_http_rpc
    mc._mcp_http_rpc = _fake_rpc
    try:
        _run(mc._mcp_probe_server({"id": "old", "url": "http://old", "transport": "http"}))
    finally:
        mc._mcp_http_rpc = orig
    st = mc._MCP_CLIENT_SERVERS["old"]
    assert st["status"] == "ready", st
    assert st["protocolVersion"] == "2025-06-18", st   # older revision honored
    assert "mcp.old.t" in tools, tools


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print("ok", fn.__name__)
    print(f"all {len(fns)} tests passed")

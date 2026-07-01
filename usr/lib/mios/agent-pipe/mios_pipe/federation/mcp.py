# AI-hint: External-MCP CONSUME client extracted VERBATIM from server.py (refactor R-MCP wave). Owns the consumer half that turned MiOS's MCP from publish-only into a federated tool surface: the layered registry read (_mcp_load_registry, vendor /usr < /etc < user), the ${ENV} header expansion (_mcp_render_headers), the single Streamable-HTTP JSON-RPC 2.0 call (_mcp_http_rpc, accepts application/json OR text/event-stream), the long-lived self-healing stdio subprocess client (_McpStdioClient: newline-delimited JSON-RPC over stdin/stdout, respawn+re-initialize on crash, non-blocking reader + stderr surfacing), the per-server probe/initialize/tools-list registration (_mcp_probe_stdio/_mcp_probe_server, fail-open per server), the startup fan-out (_mcp_client_startup), the tools/call forwarder (_mcp_call_tool), and the GET /v1/mcp/clients + GET /v1/mcp/tools + POST /v1/mcp/dispatch route bodies (as *_logic functions; the @app routes stay thin in server.py). Moved byte-identically -- server.py re-imports every moved name under its original alias (surface-parity zero-diff). The shared MCP-tool registry + lock (_MCP_CLIENT_TOOLS/_MCP_CLIENT_LOCK) stay server-resident and are dependency-INJECTED via configure() alongside _get_client, the MCP-tool embedder (_mcp_embed_new_tools, from mios_toolsearch) and the worker-tool-surface cache invalidator (_invalidate_worker_cache -- the probes cannot rebind server's _WORKER_TOOLS_FULL_CACHE global across the one-way boundary). This module NEVER imports server. The declared revision is the [mcp].protocol_version SSOT (MCP_PROTOCOL_VERSION); the newer MCP feature set (durable Tasks, elicitation, OAuth resource-server auth, tool icons) + the stateless-transport revision are scoped follow-ups -- this client implements the core initialize / tools-list / tools-call consume path.
# AI-related: ./server.py, ./mios_config.py, ./mios_jsonsalvage.py, ./mios_toolsearch.py, ./test_mios_mcp.py
# AI-functions: _mcp_load_registry, _mcp_render_headers, _mcp_http_rpc, _McpStdioClient, _mcp_probe_stdio, _mcp_probe_server, _mcp_client_startup, _mcp_call_tool, mcp_clients_logic, mcp_tools_list_logic, mcp_dispatch_logic, configure
"""External-MCP consume client for the agent-pipe federated tool surface (refactor R-MCP).

Extracted VERBATIM from ``server.py``. MiOS CONSUMES external MCP servers (not
just publishes its own): a layered registry read, an initialize handshake over
Streamable-HTTP or a spawned stdio subprocess, ``tools/list`` registration of
every remote tool namespaced ``mcp.<server>.<tool>``, and ``tools/call``
forwarding. The ``GET /v1/mcp/clients`` / ``GET /v1/mcp/tools`` /
``POST /v1/mcp/dispatch`` routes stay in ``server.py`` as thin wrappers calling
the ``*_logic`` functions here.

The shared MCP-tool registry + lock (``_MCP_CLIENT_TOOLS`` / ``_MCP_CLIENT_LOCK``)
remain server-resident (the worker / toolsearch / toolexec planes share them) and
are injected via :func:`configure`, together with the HTTP client factory, the
per-tool embedder (``_mcp_embed_new_tools``, from ``mios_toolsearch``), and the
worker-tool-surface cache invalidator. This module never imports ``server``
(one-way boundary); ``server.py`` re-imports every moved name under its original
alias so the importable surface is byte-identical.

The declared revision is the ``[mcp].protocol_version`` SSOT
(:data:`MCP_PROTOCOL_VERSION`, env ``MIOS_MCP_PROTOCOL_VERSION``). The newer MCP
feature set (durable Tasks, elicitation, OAuth resource-server auth, tool icons,
structured tool output) and the upcoming stateless-transport revision are scoped
follow-ups; this client implements the core initialize / tools-list / tools-call
consume path over Streamable-HTTP (current) + stdio.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Optional

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from mios_jsonsalvage import loads_lenient as _loads_lenient
from mios_config import _toml_section

log = logging.getLogger("mios-agent-pipe")


# ── MCP protocol-revision SSOT ───────────────────────────────────────────
# The MCP spec revision MiOS DECLARES as the latest it offers on the
# `initialize` handshake (over BOTH the Streamable-HTTP and stdio transports).
# A protocol-revision token (like an HTTP version string) -- declared ONCE here
# from the [mcp].protocol_version SSOT (env MIOS_MCP_PROTOCOL_VERSION overrides),
# never restated at a call site. The published server (mios-mcp-server) reads the
# SAME SSOT key, so consumer + server stay in lockstep. Negotiation is
# liberal-IN / strict-OUT: MiOS advertises the current revision out, but a server
# that answers with an older revision is recorded as-returned and proceeds (never
# rejected on mismatch), so an older peer still registers and stays usable.
MCP_PROTOCOL_VERSION = str(
    os.environ.get("MIOS_MCP_PROTOCOL_VERSION")
    or (_toml_section("mcp") or {}).get("protocol_version")
    or "2025-11-25").strip()


# ── T-032: MCP sandbox gate ──────────────────────────────────────────────
# When [security.mcp_sandbox].enable is true, every stdio MCP server spawn is
# routed through /usr/libexec/mios/mcp-server-runner which acts as a gatekeeper
# (directory traversal blocking, write-path enforcement, optional rootless podman
# sandbox). Default false (degrade-open: MCP servers execute directly on host).
_MCP_SANDBOX_CFG = (_toml_section("security") or {}).get("mcp_sandbox") or {}
if isinstance(_MCP_SANDBOX_CFG, str):
    _MCP_SANDBOX_CFG = {}
MCP_SANDBOX_ENABLE = (
    str(os.environ.get("MIOS_MCP_SANDBOX")
        or _MCP_SANDBOX_CFG.get("enable", "false"))
    .strip().lower() not in {"false", "0", "no", "off", ""})
MCP_SANDBOX_GATEKEEPER = "/usr/libexec/mios/mcp-server-runner"


# -- Dependency-injection seam --
# The consume client calls back into server.py's HTTP client factory, the shared
# MCP-tool registry + lock (server-resident -- also DI'd into the worker /
# toolsearch / toolexec planes), the MCP-tool embedder (lives in mios_toolsearch),
# and the worker-tool-surface cache invalidator (a probe registering new tools
# must drop server's _WORKER_TOOLS_FULL_CACHE so it rebuilds; the module cannot
# rebind that server global across the one-way boundary). server.py calls
# configure() with all of them AFTER each is defined. They stay None / empty until
# injected so a standalone ``import mios_mcp`` still succeeds for the unit tests.
_get_client = None
_MCP_CLIENT_TOOLS: dict = {}      # injected by reference (server-resident)
_MCP_CLIENT_LOCK = None           # injected (server-resident asyncio.Lock)
_mcp_embed_new_tools = None       # injected (mios_toolsearch._mcp_embed_new_tools)


def _invalidate_worker_cache() -> None:
    """Default no-op until server injects its _WORKER_TOOLS_FULL_CACHE invalidator."""
    return None


def configure(*, get_client=None, mcp_client_tools=None, mcp_client_lock=None,
              mcp_embed_new_tools=None, invalidate_worker_cache=None) -> None:
    """Inject server.py's runtime deps: the HTTP client factory, the shared
    MCP-tool registry + lock (BY REFERENCE so server-side mutation stays visible),
    the MCP-tool embedder, and the worker-surface cache invalidator."""
    global _get_client, _MCP_CLIENT_TOOLS, _MCP_CLIENT_LOCK
    global _mcp_embed_new_tools, _invalidate_worker_cache
    if get_client is not None:
        _get_client = get_client
    if mcp_client_tools is not None:
        _MCP_CLIENT_TOOLS = mcp_client_tools
    if mcp_client_lock is not None:
        _MCP_CLIENT_LOCK = mcp_client_lock
    if mcp_embed_new_tools is not None:
        _mcp_embed_new_tools = mcp_embed_new_tools
    if invalidate_worker_cache is not None:
        _invalidate_worker_cache = invalidate_worker_cache


# Module-owned MCP state. _MCP_CLIENT_TOOLS + _MCP_CLIENT_LOCK are server-resident
# (declared as injected placeholders in the DI seam above), so they are NOT defined
# here -- only the registry path list, the per-server status map, the long-lived
# stdio-client registry, and the ${ENV} placeholder regex.
_MCP_REGISTRY_PATHS = [
    "/usr/share/mios/ai/v1/mcp.json",                               # vendor
    "/etc/mios/ai/v1/mcp.json",                                     # host
    os.path.expanduser("~/.config/mios/ai/v1/mcp.json"),            # user
]
_MCP_CLIENT_SERVERS: dict = {}    # sid -> {status, protocolVersion, tools_count, …}
_MCP_STDIO_CLIENTS: dict = {}     # sid -> _McpStdioClient (long-lived subprocess)
_MCP_ENV_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def _mcp_load_registry() -> list:
    """Layered registry read: vendor < /etc < user. Later overlays REPLACE
    earlier entries with the same id (not merge) so an operator can disable a
    vendor entry by re-declaring it with enabled:false."""
    by_id: dict = {}
    for p in _MCP_REGISTRY_PATHS:
        try:
            with open(p) as f:
                d = json.load(f) or {}
        except (OSError, json.JSONDecodeError):
            continue
        for s in (d.get("servers") or []):
            if not isinstance(s, dict):
                continue
            sid = str(s.get("id") or s.get("server_label") or "").strip()
            if sid:
                by_id[sid] = s
    return list(by_id.values())


def _mcp_render_headers(h: dict) -> dict:
    """Expand ${ENV_VAR} placeholders (e.g. for Bearer tokens stored in env)."""
    out: dict = {}
    for k, v in (h or {}).items():
        s = str(v)
        for var in _MCP_ENV_RE.findall(s):
            s = s.replace("${" + var + "}", os.environ.get(var, ""))
        out[k] = s
    return out


async def _mcp_http_rpc(url: str, headers: dict, method: str,
                       params: Optional[dict] = None, rid: int = 1,
                       timeout_s: float = 30.0) -> dict:
    """Single JSON-RPC 2.0 call to an MCP server over Streamable-HTTP. Accepts
    either application/json or text/event-stream responses (spec allows the
    server to upgrade to SSE for any response)."""
    body: dict = {"jsonrpc": "2.0", "id": rid, "method": method}
    if params is not None:
        body["params"] = params
    h = dict(headers or {})
    h.setdefault("Content-Type", "application/json")
    h.setdefault("Accept", "application/json, text/event-stream")
    try:
        client = await _get_client()
        r = await client.post(url, json=body, headers=h, timeout=timeout_s)
    except httpx.HTTPError as e:
        return {"error": {"code": -32000, "message": f"http error: {e}"}}
    if r.status_code != 200:
        return {"error": {"code": r.status_code,
                          "message": (r.text or "")[:200]}}
    ct = (r.headers.get("content-type") or "").lower()
    if "text/event-stream" in ct:
        for chunk in r.text.split("\n\n"):
            for line in chunk.splitlines():
                if line.startswith("data:"):
                    try:
                        return _loads_lenient(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
        return {"error": {"code": -32700, "message": "no SSE data event"}}
    try:
        return r.json()
    except (json.JSONDecodeError, ValueError):
        return {"error": {"code": -32700, "message": "non-JSON response"}}


class _McpStdioClient:
    """Long-lived MCP server subprocess speaking newline-delimited JSON-RPC 2.0
 over stdin/stdout (MCP stdio transport). Mirrors _mcp_http_rpc's
    error-envelope shape so callers need NO special-casing. Self-heals: a dead
    process is respawned AND re-initialized on the next call (restart-on-crash).
    Non-blocking (asyncio subprocess + StreamReader.readline). stderr -> DEVNULL
    (spec: the server MAY log to stderr; the client MAY ignore it)."""

    def __init__(self, sid, command, args, env, cwd):
        self.sid = sid
        self.command = command
        self.args = list(args or [])
        self.env = dict(env or {})
        self.cwd = cwd or None
        self.proc = None
        self._pending: dict = {}          # rid -> Future
        self._lock = asyncio.Lock()       # serialize (re)spawn + initialize
        self._reader = None
        self._idc = 0                     # monotonic per-client request id
        self._inited = False
        self._init_result: dict = {}

    def _next_id(self) -> int:
        self._idc += 1
        return self._idc

    async def _spawn(self) -> None:
        child_env = dict(os.environ)
        child_env.update(_mcp_render_headers(self.env))   # reuse ${ENV} expansion
        # T-032: when MCP sandbox is enabled, route through the gatekeeper
        _cmd = self.command
        _args = list(self.args)
        if MCP_SANDBOX_ENABLE and os.path.isfile(MCP_SANDBOX_GATEKEEPER):
            log.info("mcp sandbox: routing %s through gatekeeper %s",
                     self.sid, MCP_SANDBOX_GATEKEEPER)
            child_env["MIOS_MCP_SANDBOX"] = "true"
            # Write-allowed paths from TOML config
            _wap = _MCP_SANDBOX_CFG.get("write_allowed_paths") or []
            if isinstance(_wap, list):
                child_env["MIOS_WRITE_ALLOWED_PATHS"] = ":".join(str(p) for p in _wap)
            _args = [_cmd] + _args
            _cmd = MCP_SANDBOX_GATEKEEPER
        self.proc = await asyncio.create_subprocess_exec(
            _cmd, *_args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,               # P4: capture (was DEVNULL) so
            env=child_env, cwd=self.cwd)                  # a failing server's error is visible
        self._inited = False
        self._reader = asyncio.create_task(self._read_loop(self.proc))
        asyncio.create_task(self._stderr_log(self.proc))

    async def _stderr_log(self, proc) -> None:
        """P4: surface a stdio MCP server's stderr (first chunk) in the journal instead of
        silently discarding it -- otherwise a spawn/crash is an opaque 'stdio init failed'."""
        try:
            data = await proc.stderr.read(4000)
            if data:
                log.warning("mcp stdio[%s] stderr: %s", self.sid,
                            data.decode("utf-8", "replace").strip()[:1200])
        except Exception:  # noqa: BLE001
            pass

    async def _read_loop(self, proc) -> None:
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                s = line.strip()
                if not s:
                    continue
                try:
                    msg = _loads_lenient(s)
                except (json.JSONDecodeError, ValueError):
                    continue          # spec: ignore non-message stdout
                rid = msg.get("id")
                if rid is not None:
                    fut = self._pending.pop(rid, None)
                    if fut is not None and not fut.done():
                        fut.set_result(msg)
        except Exception:
            pass
        finally:
            for fut in list(self._pending.values()):
                if not fut.done():
                    fut.set_result({"error": {"code": -32000,
                                              "message": "stdio server exited"}})
            self._pending.clear()
            if self.proc is proc:
                self.proc = None
                self._inited = False

    async def _send(self, body: dict) -> None:
        self.proc.stdin.write(
            (json.dumps(body, ensure_ascii=False) + "\n").encode("utf-8"))
        await self.proc.stdin.drain()

    async def _await_rpc(self, method, params, timeout_s) -> dict:
        rid = self._next_id()
        body = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            body["params"] = params
        fut = asyncio.get_running_loop().create_future()
        self._pending[rid] = fut
        try:
            await self._send(body)
            return await asyncio.wait_for(fut, timeout_s)
        except asyncio.TimeoutError:
            self._pending.pop(rid, None)
            return {"error": {"code": -32000,
                              "message": f"stdio timeout ({method})"}}
        except Exception as e:
            self._pending.pop(rid, None)
            return {"error": {"code": -32000, "message": f"stdio error: {e}"}}

    async def _ensure_session(self) -> None:
        # FIX (adversarial verdict): respawn MUST re-run initialize, else a
        # post-crash tools/call hits an uninitialized (spec-rejecting) server.
        async with self._lock:
            if (self.proc is not None and self.proc.returncode is None
                    and self._inited):
                return
            if self.proc is None or self.proc.returncode is not None:
                try:
                    await self._spawn()
                except Exception as e:
                    self.proc = None
                    self._inited = False
                    log.warning("mcp stdio: spawn failed for %s: %s",
                                self.sid, e)
                    return
            init = await self._await_rpc("initialize", {
                "protocolVersion": MCP_PROTOCOL_VERSION, "capabilities": {},
                "clientInfo": {"name": "mios-agent-pipe", "version": "1.0"}},
                30.0)
            if init.get("error"):
                self._inited = False
                return
            self._init_result = init.get("result") or {}
            try:
                await self._send({"jsonrpc": "2.0",
                                  "method": "notifications/initialized"})
            except Exception:
                pass
            self._inited = True

    async def _rpc(self, method, params=None, timeout_s=30.0) -> dict:
        await self._ensure_session()
        if not self._inited or self.proc is None:
            return {"error": {"code": -32000,
                              "message": "stdio session unavailable"}}
        return await self._await_rpc(method, params, timeout_s)

    async def initialize(self) -> dict:
        await self._ensure_session()
        return self._init_result if self._inited else {"error": "stdio init failed"}

    async def close(self) -> None:
        try:
            if self._reader is not None:
                self._reader.cancel()
            p = self.proc
            if p is not None and p.returncode is None:
                try:
                    p.stdin.close()
                except Exception:
                    pass
                try:
                    await asyncio.wait_for(p.wait(), 3.0)
                except Exception:
                    try:
                        p.terminate()
                        await asyncio.wait_for(p.wait(), 3.0)
                    except Exception:
                        try:
                            p.kill()
                        except Exception:
                            pass
        except Exception:
            pass


async def _mcp_probe_stdio(cfg: dict, state: dict, sid: str) -> None:
    """initialize + tools/list an stdio (subprocess) MCP server; register its
    tools. Mirrors the http probe; fail-open (errors land in state, never raise)."""
    command = str(cfg.get("command") or "").strip()
    if not command:
        state["status"] = "config-error"
        state["error"] = "missing 'command' for stdio transport"
        return
    cli = _MCP_STDIO_CLIENTS.get(sid)
    if cli is None:
        cli = _McpStdioClient(sid, command, cfg.get("args") or [],
                              cfg.get("env") or {}, cfg.get("cwd"))
        _MCP_STDIO_CLIENTS[sid] = cli
    init = await cli.initialize()
    if not cli._inited:
        state["status"] = "init-failed"
        state["error"] = (init.get("error") if isinstance(init, dict) else None) \
            or "stdio initialize failed"
        log.warning("mcp client(stdio): initialize failed for %s: %s",
                    sid, state["error"])
        return
    state["protocolVersion"] = (init or {}).get("protocolVersion")
    state["serverInfo"] = (init or {}).get("serverInfo")
    tl = await cli._rpc("tools/list")
    if tl.get("error"):
        state["status"] = "tools-list-failed"
        state["error"] = tl["error"].get("message")
        return
    tools = (tl.get("result") or {}).get("tools") or []
    allowed = set(cfg.get("allowed_tools") or [])
    if allowed:
        tools = [t for t in tools if t.get("name") in allowed]
    async with _MCP_CLIENT_LOCK:
        for k in [k for k, v in _MCP_CLIENT_TOOLS.items()
                  if v.get("server_id") == sid]:
            _MCP_CLIENT_TOOLS.pop(k, None)
        for t in tools:
            tn = str(t.get("name") or "").strip()
            if not tn:
                continue
            _MCP_CLIENT_TOOLS[f"mcp.{sid}.{tn}"] = {
                "server_id": sid, "tool": tn,
                "description": t.get("description"),
                "inputSchema": t.get("inputSchema"),
                "transport": "stdio",
                "namespace": cfg.get("namespace") or "",   # P4: tier/namespace/taint
                "tier": cfg.get("tier") or "rare",
                "taint": cfg.get("taint") or "",
                "examples": cfg.get("examples") or [],      # P4-fix: TDWA retrieval
            }
        state["tools_count"] = sum(1 for v in _MCP_CLIENT_TOOLS.values()
                                   if v.get("server_id") == sid)
    state["status"] = "ready"
    _invalidate_worker_cache()
    await _mcp_embed_new_tools()                 # P4: make this server's tools selectable
    log.info("mcp client(stdio): %s ready (%d tools, protocol %s)",
             sid, state["tools_count"], state["protocolVersion"])


async def _mcp_probe_server(cfg: dict) -> None:
    """initialize + tools/list ONE MCP server; register its tools in the
    catalog. Errors are captured in the per-server state dict (never raise)
    so a single bad server doesn't break startup."""
    sid = str(cfg.get("id") or "").strip()
    if not sid:
        return
    state: dict = {"id": sid, "url": cfg.get("url") or cfg.get("server_url"),
                   "status": "connecting", "protocolVersion": None,
                   "tools_count": 0,
                   "label": cfg.get("label") or cfg.get("server_label") or sid}
    async with _MCP_CLIENT_LOCK:
        _MCP_CLIENT_SERVERS[sid] = state

    if not cfg.get("enabled", True):
        state["status"] = "disabled"
        return
    transport = (cfg.get("transport") or "http").lower()
    if transport == "stdio":
        await _mcp_probe_stdio(cfg, state, sid)
        return
    if transport != "http":
        state["status"] = "unsupported-transport"
        state["error"] = f"unsupported transport {transport!r} (http/stdio only)"
        log.info("mcp client: %s skipped (%s)", sid, state["error"])
        return
    url = (cfg.get("url") or cfg.get("server_url") or "").rstrip("/") or ""
    if not url:
        state["status"] = "config-error"
        state["error"] = "missing url"
        return
    headers = _mcp_render_headers(cfg.get("headers") or {})

    init = await _mcp_http_rpc(url, headers, "initialize", params={
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {"name": "mios-agent-pipe", "version": "1.0"}})
    if init.get("error"):
        state["status"] = "init-failed"
        state["error"] = init["error"].get("message")
        log.warning("mcp client: initialize failed for %s: %s",
                    sid, state["error"])
        return
    state["protocolVersion"] = (init.get("result") or {}).get("protocolVersion")
    state["serverInfo"] = (init.get("result") or {}).get("serverInfo")

    tl = await _mcp_http_rpc(url, headers, "tools/list", rid=2)
    if tl.get("error"):
        state["status"] = "tools-list-failed"
        state["error"] = tl["error"].get("message")
        return
    tools = (tl.get("result") or {}).get("tools") or []
    allowed = set(cfg.get("allowed_tools") or [])
    if allowed:
        tools = [t for t in tools if t.get("name") in allowed]

    async with _MCP_CLIENT_LOCK:
        for k in [k for k, v in _MCP_CLIENT_TOOLS.items()
                  if v.get("server_id") == sid]:
            _MCP_CLIENT_TOOLS.pop(k, None)
        for t in tools:
            tn = str(t.get("name") or "").strip()
            if not tn:
                continue
            key = f"mcp.{sid}.{tn}"
            _MCP_CLIENT_TOOLS[key] = {
                "server_id": sid, "tool": tn,
                "description": t.get("description"),
                "inputSchema": t.get("inputSchema"),
                "url": url,
                "headers_template": cfg.get("headers") or {},
                "namespace": cfg.get("namespace") or "",   # P4: tier/namespace/taint
                "tier": cfg.get("tier") or "rare",
                "taint": cfg.get("taint") or "",
                "examples": cfg.get("examples") or [],      # P4-fix: TDWA retrieval
            }
        state["tools_count"] = sum(1 for v in _MCP_CLIENT_TOOLS.values()
                                   if v.get("server_id") == sid)
    state["status"] = "ready"
    # Late-discovered MCP tools must appear in the memoised worker surface
    # (P0): drop the cache so it rebuilds on next request.
    _invalidate_worker_cache()
    await _mcp_embed_new_tools()                 # P4: make this server's tools selectable
    log.info("mcp client: %s ready (%d tools, protocol %s)",
             sid, state["tools_count"], state["protocolVersion"])


async def _mcp_client_startup() -> None:
    """Read the registry, probe every enabled server concurrently. Errors per
    server are captured in state; total startup never blocks on a slow peer."""
    if os.environ.get("MIOS_MCP_CLIENT_DISABLED",
                      "").strip().lower() in {"1", "true", "yes"}:
        log.info("mcp client: disabled by env (MIOS_MCP_CLIENT_DISABLED)")
        return
    servers = _mcp_load_registry()
    if not servers:
        log.info("mcp client: registry empty -- no external servers configured")
        return
    log.info("mcp client: probing %d external server(s)", len(servers))
    await asyncio.gather(*(_mcp_probe_server(s) for s in servers),
                         return_exceptions=True)


async def _mcp_call_tool(key: str, args: dict) -> dict:
    """Forward a tools/call to the MCP server that owns this namespaced tool."""
    async with _MCP_CLIENT_LOCK:
        info = _MCP_CLIENT_TOOLS.get(key)
    if not info:
        return {"error": f"unknown MCP tool: {key}"}
    if info.get("transport") == "stdio":
        cli = _MCP_STDIO_CLIENTS.get(info["server_id"])
        if cli is None:
            return {"error": f"stdio client unavailable: {key}", "tool": key}
        resp = await cli._rpc(
            "tools/call",
            params={"name": info["tool"], "arguments": args or {}},
            timeout_s=120.0)
        if resp.get("error"):
            return {"error": resp["error"].get("message"),
                    "code": resp["error"].get("code"), "tool": key}
        return resp.get("result") or {}
    headers = _mcp_render_headers(info.get("headers_template") or {})
    resp = await _mcp_http_rpc(
        info["url"], headers, "tools/call",
        params={"name": info["tool"], "arguments": args or {}},
        rid=int(time.time() * 1000) & 0x7FFFFFFF, timeout_s=120.0)
    if resp.get("error"):
        return {"error": resp["error"].get("message"),
                "code": resp["error"].get("code"),
                "tool": key}
    return resp.get("result") or {}


# ── /v1/mcp/* route bodies (the @app routes stay thin in server.py) ───

async def mcp_clients_logic() -> JSONResponse:
    """Inspect the consumer-side MCP client. Every external server's status +
    tools_count + protocolVersion -- the proof the registry was read and
    servers were initialized correctly."""
    async with _MCP_CLIENT_LOCK:
        servers = [dict(v) for v in _MCP_CLIENT_SERVERS.values()]
        total = len(_MCP_CLIENT_TOOLS)
    return JSONResponse({"object": "mios.mcp.clients",
                         "servers": servers, "tools_total": total})


async def mcp_tools_list_logic() -> JSONResponse:
    """List every external MCP tool discovered, namespaced 'mcp.<server>.<tool>'."""
    async with _MCP_CLIENT_LOCK:
        tools = [
            {"name": k, "description": v.get("description"),
             "inputSchema": v.get("inputSchema"),
             "server_id": v.get("server_id")}
            for k, v in _MCP_CLIENT_TOOLS.items()
        ]
    return JSONResponse({"object": "mios.mcp.tools", "tools": tools})


async def mcp_dispatch_logic(request: "Request") -> JSONResponse:
    """Forward a tools/call to the external MCP server that owns the tool.
    Body: {tool: 'mcp.<server>.<tool>', args: {...}}. Unknown tool -> error."""
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse({"error": "invalid json"}, status_code=400)
    tool = str(body.get("tool") or body.get("name") or "").strip()
    args = body.get("args") or body.get("arguments") or {}
    if not tool:
        return JSONResponse({"error": "missing 'tool'"}, status_code=400)
    return JSONResponse(await _mcp_call_tool(tool, args))


# -- @app -> APIRouter migration (refactor R13 batch 2: federation/standards) ----
# The three /v1/mcp/* consumer-side inspection + dispatch routes moved off
# server.py's @app onto this co-located mcp_router (same routes->APIRouter pattern
# the /a2a wave established). server.py imports mcp_router + the three handler NAMES
# and mounts the router via app.include_router(mcp_router); the handler names are
# re-imported there so server's importable `provided` surface is unchanged and the
# served path/method set is identical (the live-app route gate proves it). Each body
# now calls the module-resident *_logic DIRECTLY (same module -- no sys.modules hop).
# One-way boundary: this module never imports server (the MCP-client deps the logic
# reads arrive via configure()). APIRouter()/method decorators are structural, not
# config.
mcp_router = APIRouter()


@mcp_router.get("/v1/mcp/clients")
async def mcp_clients() -> JSONResponse:
    """Inspect the consumer-side MCP client. Every external server's status +
    tools_count + protocolVersion -- the proof the registry was read and
    servers were initialized correctly. Calls mcp_clients_logic (same module)."""
    return await mcp_clients_logic()


@mcp_router.get("/v1/mcp/tools")
async def mcp_tools_list() -> JSONResponse:
    """List every external MCP tool discovered, namespaced 'mcp.<server>.<tool>'.
    Calls mcp_tools_list_logic (same module)."""
    return await mcp_tools_list_logic()


@mcp_router.post("/v1/mcp/dispatch")
async def mcp_dispatch(request: Request) -> JSONResponse:
    """Forward a tools/call to the external MCP server that owns the tool.
    Body: {tool: 'mcp.<server>.<tool>', args: {...}}. Unknown tool -> error.
    Calls mcp_dispatch_logic (same module)."""
    return await mcp_dispatch_logic(request)

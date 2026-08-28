# AI-hint: Declarative MCP server lifecycle manager and dynamic tool schema converter in agent-pipe.
# AI-doc: usr/share/doc/mios/manual/mcp.md, usr/share/doc/mios/manual/federation.md
"""Declarative Model Context Protocol (MCP) server lifecycle manager, JSON-RPC 2.0 client
transports (stdio subprocesses & SSE/HTTP endpoints), dynamic OpenAI tool schema converter,
and runtime tool execution dispatcher."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import json
import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional, Union

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from mios_config import _toml_section
from mios_mcp_schema import (          # noqa: F401 -- re-exported: importers and tests use mios_mcp
    convert_mcp_to_openai_schema,
    make_schema_strict,
    _mcp_tool_to_openai_tool,
)
from mios_mcp_transport import (       # noqa: F401 -- re-exported for the same reason
    MCP_PROTOCOL_VERSION,
    MCP_SANDBOX_ENABLE,
    MCP_SANDBOX_GATEKEEPER,
    _MCP_ENV_RE,
    _mcp_render_headers,
    _mcp_http_rpc,
    _McpHttpClient,
    _McpStdioClient,
)

log = logging.getLogger("mios-agent-pipe")


# Dependency injection for agent-pipe runtime
_get_client: Optional[Callable] = None
_MCP_CLIENT_TOOLS: dict = {}  # injected by reference: "mcp.<sid>.<tool>" -> tool metadata
_MCP_CLIENT_LOCK: asyncio.Lock = asyncio.Lock()
_mcp_embed_new_tools: Optional[Callable] = None
_invalidate_worker_cache: Callable = lambda: None

def _default_client_factory():
    return httpx.AsyncClient(timeout=30.0)

async def _resolve_http_client() -> httpx.AsyncClient:
    global _get_client
    if _get_client is not None:
        c = _get_client()
        if asyncio.iscoroutine(c):
            return await c
        return c
    return _default_client_factory()

def configure(
    *,
    get_client: Optional[Callable] = None,
    mcp_client_tools: Optional[dict] = None,
    mcp_client_lock: Optional[asyncio.Lock] = None,
    mcp_embed_new_tools: Optional[Callable] = None,
    invalidate_worker_cache: Optional[Callable] = None,
) -> None:
    """Inject server.py's runtime dependencies: HTTP client factory, shared MCP-tool
    registry + lock (by reference so server-side mutation stays visible), the MCP-tool
    embedder, and worker-surface cache invalidator."""
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

# Registry file paths
_MCP_REGISTRY_PATHS = [
    "/usr/share/mios/ai/v1/mcp.json",  # vendor (lowest)
    "/etc/mios/ai/v1/mcp.json",  # host
    os.path.expanduser("~/.config/mios/ai/v1/mcp.json"),  # user (highest)
]

_MCP_CLIENT_SERVERS: dict = {}  # sid -> {status, protocolVersion, tools_count, ...}
_MCP_STDIO_CLIENTS: dict = {}  # sid -> _McpStdioClient (long-lived subprocess)
_MCP_HTTP_CLIENTS: dict = {}  # sid -> _McpHttpClient

# ---------------------------------------------------------------------------
# Declarative Specification & TOML Parsing
# ---------------------------------------------------------------------------

@dataclass
class McpServerSpec:
    """Declarative specification for an MCP server instance."""

    id: str
    transport: str = "stdio"  # "stdio", "sse", "http"
    command: Optional[str] = None
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    cwd: Optional[str] = None
    url: Optional[str] = None
    headers: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    tier: str = "common"  # "core", "common", "rare"
    namespace: str = ""
    taint: str = ""
    allowed_tools: List[str] = field(default_factory=list)
    label: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    note: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "id": self.id,
            "transport": self.transport,
            "enabled": self.enabled,
            "tier": self.tier,
            "namespace": self.namespace,
            "taint": self.taint,
        }
        if self.command:
            d["command"] = self.command
        if self.args:
            d["args"] = list(self.args)
        if self.env:
            d["env"] = dict(self.env)
        if self.cwd:
            d["cwd"] = self.cwd
        if self.url:
            d["url"] = self.url
        if self.headers:
            d["headers"] = dict(self.headers)
        if self.allowed_tools:
            d["allowed_tools"] = list(self.allowed_tools)
        if self.label:
            d["label"] = self.label
        if self.examples:
            d["examples"] = list(self.examples)
        if self.note:
            d["note"] = self.note
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any], sid: str = "") -> McpServerSpec:
        server_id = str(d.get("id") or d.get("server_label") or sid or "").strip()
        transport = str(d.get("transport") or ("http" if (d.get("url") or d.get("server_url")) else "stdio")).strip().lower()
        url = d.get("url") or d.get("server_url")
        args_raw = d.get("args") or []
        args = [str(a) for a in args_raw] if isinstance(args_raw, (list, tuple)) else []
        env_raw = d.get("env") or {}
        env = {str(k): str(v) for k, v in env_raw.items()} if isinstance(env_raw, dict) else {}
        headers_raw = d.get("headers") or {}
        headers = {str(k): str(v) for k, v in headers_raw.items()} if isinstance(headers_raw, dict) else {}
        allowed_raw = d.get("allowed_tools") or []
        allowed_tools = [str(t) for t in allowed_raw] if isinstance(allowed_raw, (list, tuple)) else []
        examples_raw = d.get("examples") or []
        examples = [str(e) for e in examples_raw] if isinstance(examples_raw, (list, tuple)) else []

        return cls(
            id=server_id,
            transport=transport,
            command=d.get("command"),
            args=args,
            env=env,
            cwd=d.get("cwd"),
            url=url,
            headers=headers,
            enabled=bool(d.get("enabled", True)),
            tier=str(d.get("tier") or "common"),
            namespace=str(d.get("namespace") or ""),
            taint=str(d.get("taint") or ""),
            allowed_tools=allowed_tools,
            label=d.get("label") or d.get("server_label") or server_id,
            examples=examples,
            note=d.get("note"),
        )

def load_servers_from_toml(toml_data: Union[dict, str, bytes]) -> List[McpServerSpec]:
    """Parse [mcp.servers] / [tools.mcp_servers] declarations from mios.toml.
    Accepts parsed dictionary, TOML string, or filesystem path."""
    parsed: dict = {}
    if isinstance(toml_data, (str, bytes)):
        content = toml_data.decode("utf-8") if isinstance(toml_data, bytes) else toml_data
        if isinstance(content, str) and os.path.isfile(content):
            try:
                import tomllib
                with open(content, "rb") as f:
                    parsed = tomllib.load(f) or {}
            except Exception:
                try:
                    import tomli as tomllib  # type: ignore
                    with open(content, "rb") as f:
                        parsed = tomllib.load(f) or {}
                except Exception:
                    parsed = {}
        else:
            try:
                import tomllib
                parsed = tomllib.loads(content) or {}
            except Exception:
                try:
                    import tomli as tomllib  # type: ignore
                    parsed = tomllib.loads(content) or {}
                except Exception:
                    parsed = {}
    elif isinstance(toml_data, dict):
        parsed = toml_data

    servers_section = (
        parsed.get("mcp", {}).get("servers")
        or parsed.get("mcp_servers")
        or parsed.get("tools", {}).get("mcp_servers")
        or parsed.get("servers")
        or {}
    )

    specs: List[McpServerSpec] = []
    if isinstance(servers_section, dict):
        for sid, cfg in servers_section.items():
            if isinstance(cfg, dict):
                specs.append(McpServerSpec.from_dict(cfg, sid=sid))
    elif isinstance(servers_section, list):
        for item in servers_section:
            if isinstance(item, dict):
                specs.append(McpServerSpec.from_dict(item))

    return specs

def _mcp_load_registry() -> list:
    """Layered registry read: vendor < /etc < user < mios.toml.
    Later overlays REPLACE earlier entries with the same id so operators
    can override or disable entries with enabled:false."""
    by_id: dict = {}

    # 1. Read JSON registries
    for p in _MCP_REGISTRY_PATHS:
        try:
            with open(p, "r", encoding="utf-8") as f:
                d = json.load(f) or {}
        except (OSError, json.JSONDecodeError):
            continue
        for s in d.get("servers") or []:
            if not isinstance(s, dict):
                continue
            sid = str(s.get("id") or s.get("server_label") or "").strip()
            if sid:
                by_id[sid] = s

    # 2. Read mios.toml [mcp.servers]
    toml_mcp = _toml_section("mcp") or {}
    toml_servers = toml_mcp.get("servers") or {}
    if isinstance(toml_servers, dict):
        for sid, cfg in toml_servers.items():
            if isinstance(cfg, dict):
                spec = McpServerSpec.from_dict(cfg, sid=sid)
                by_id[spec.id] = spec.to_dict()
    elif isinstance(toml_servers, list):
        for item in toml_servers:
            if isinstance(item, dict):
                spec = McpServerSpec.from_dict(item)
                by_id[spec.id] = spec.to_dict()

    return list(by_id.values())


# ---------------------------------------------------------------------------
# Server Probing & Tool Registration
# ---------------------------------------------------------------------------

async def _mcp_probe_stdio(cfg: dict, state: dict, sid: str) -> None:
    """Initialize + tools/list an stdio subprocess MCP server; register its tools."""
    command = str(cfg.get("command") or "").strip()
    if not command:
        state["status"] = "config-error"
        state["error"] = "missing 'command' for stdio transport"
        return

    cli = _MCP_STDIO_CLIENTS.get(sid)
    if cli is None:
        cli = _McpStdioClient(
            sid,
            command,
            cfg.get("args") or [],
            cfg.get("env") or {},
            cfg.get("cwd"),
        )
        _MCP_STDIO_CLIENTS[sid] = cli

    init = await cli.initialize()
    if not cli._inited:
        state["status"] = "init-failed"
        state["error"] = (init.get("error") if isinstance(init, dict) else None) or "stdio initialize failed"
        log.warning("mcp client(stdio): initialize failed for %s: %s", sid, state["error"])
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
        for k in [k for k, v in _MCP_CLIENT_TOOLS.items() if v.get("server_id") == sid]:
            _MCP_CLIENT_TOOLS.pop(k, None)
        for t in tools:
            tn = str(t.get("name") or "").strip()
            if not tn:
                continue
            _MCP_CLIENT_TOOLS[f"mcp.{sid}.{tn}"] = {
                "server_id": sid,
                "tool": tn,
                "description": t.get("description"),
                "inputSchema": t.get("inputSchema"),
                "transport": "stdio",
                "namespace": cfg.get("namespace") or "",
                "tier": cfg.get("tier") or "common",
                "taint": cfg.get("taint") or "",
                "examples": cfg.get("examples") or [],
            }
        state["tools_count"] = sum(1 for v in _MCP_CLIENT_TOOLS.values() if v.get("server_id") == sid)

    state["status"] = "ready"
    _invalidate_worker_cache()
    if _mcp_embed_new_tools is not None:
        try:
            await _mcp_embed_new_tools()
        except Exception:
            pass
    log.info(
        "mcp client(stdio): %s ready (%d tools, protocol %s)",
        sid,
        state["tools_count"],
        state["protocolVersion"],
    )

async def _mcp_probe_http(cfg: dict, state: dict, sid: str) -> None:
    """Initialize + tools/list an HTTP/SSE MCP server; register its tools."""
    url = (cfg.get("url") or cfg.get("server_url") or "").rstrip("/")
    if not url:
        state["status"] = "config-error"
        state["error"] = "missing url"
        return

    headers = _mcp_render_headers(cfg.get("headers") or {})
    transport = str(cfg.get("transport") or "http").lower()

    cli = _MCP_HTTP_CLIENTS.get(sid)
    if cli is None:
        cli = _McpHttpClient(sid, url, headers=headers, transport=transport)
        _MCP_HTTP_CLIENTS[sid] = cli

    init = await _mcp_http_rpc(
        url,
        headers,
        "initialize",
        params={
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "mios-agent-pipe", "version": "1.0"},
        },
    )
    if init.get("error"):
        state["status"] = "init-failed"
        state["error"] = init["error"].get("message")
        log.warning("mcp client: initialize failed for %s: %s", sid, state["error"])
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
        for k in [k for k, v in _MCP_CLIENT_TOOLS.items() if v.get("server_id") == sid]:
            _MCP_CLIENT_TOOLS.pop(k, None)
        for t in tools:
            tn = str(t.get("name") or "").strip()
            if not tn:
                continue
            key = f"mcp.{sid}.{tn}"
            _MCP_CLIENT_TOOLS[key] = {
                "server_id": sid,
                "tool": tn,
                "description": t.get("description"),
                "inputSchema": t.get("inputSchema"),
                "url": url,
                "headers_template": cfg.get("headers") or {},
                "transport": transport,
                "namespace": cfg.get("namespace") or "",
                "tier": cfg.get("tier") or "common",
                "taint": cfg.get("taint") or "",
                "examples": cfg.get("examples") or [],
            }
        state["tools_count"] = sum(1 for v in _MCP_CLIENT_TOOLS.values() if v.get("server_id") == sid)

    state["status"] = "ready"
    _invalidate_worker_cache()
    if _mcp_embed_new_tools is not None:
        try:
            await _mcp_embed_new_tools()
        except Exception:
            pass
    log.info(
        "mcp client(%s): %s ready (%d tools, protocol %s)",
        transport,
        sid,
        state["tools_count"],
        state["protocolVersion"],
    )

async def _mcp_probe_server(cfg: dict) -> None:
    """Initialize + tools/list ONE MCP server; register its tools in the catalog."""
    sid = str(cfg.get("id") or "").strip()
    if not sid:
        return

    state: dict = {
        "id": sid,
        "url": cfg.get("url") or cfg.get("server_url"),
        "status": "connecting",
        "protocolVersion": None,
        "tools_count": 0,
        "label": cfg.get("label") or cfg.get("server_label") or sid,
        "transport": cfg.get("transport") or "stdio",
    }
    async with _MCP_CLIENT_LOCK:
        _MCP_CLIENT_SERVERS[sid] = state

    if not cfg.get("enabled", True):
        state["status"] = "disabled"
        return

    transport = (cfg.get("transport") or "http").lower()
    if transport == "stdio":
        await _mcp_probe_stdio(cfg, state, sid)
    elif transport in {"http", "sse", "streamable-http"}:
        await _mcp_probe_http(cfg, state, sid)
    else:
        state["status"] = "unsupported-transport"
        state["error"] = f"unsupported transport {transport!r} (http/sse/stdio only)"
        log.info("mcp client: %s skipped (%s)", sid, state["error"])

async def _mcp_client_startup() -> None:
    """Read all declarative registries, probe every enabled server concurrently."""
    if os.environ.get("MIOS_MCP_CLIENT_DISABLED", "").strip().lower() in {"1", "true", "yes"}:
        log.info("mcp client: disabled by env (MIOS_MCP_CLIENT_DISABLED)")
        return
    servers = _mcp_load_registry()
    if not servers:
        log.info("mcp client: registry empty -- no external servers configured")
        return
    log.info("mcp client: probing %d external server(s)", len(servers))
    await asyncio.gather(*(_mcp_probe_server(s) for s in servers), return_exceptions=True)

# ---------------------------------------------------------------------------
# Dynamic Tool Call Dispatcher
# ---------------------------------------------------------------------------

async def dispatch_tool_call(server_id: str, tool_name: str, arguments: dict, timeout_s: float = 120.0) -> dict:
    """Dispatch an execution call directly to a target MCP server by ID and tool name."""
    sid = server_id.strip()
    tn = tool_name.strip()

    # Handle namespaced tool name if server_id omitted
    if not sid and tn.startswith("mcp."):
        parts = tn.split(".", 2)
        if len(parts) >= 3:
            sid = parts[1]
            tn = parts[2]

    # Check stdio client
    cli_stdio = _MCP_STDIO_CLIENTS.get(sid)
    if cli_stdio is not None:
        resp = await cli_stdio.call_tool(tn, arguments or {}, timeout_s=timeout_s)
        if resp.get("error"):
            return {"error": resp["error"].get("message"), "code": resp["error"].get("code"), "tool": tn, "server_id": sid}
        return resp.get("result") or resp

    # Check HTTP/SSE client
    cli_http = _MCP_HTTP_CLIENTS.get(sid)
    if cli_http is not None:
        resp = await cli_http.call_tool(tn, arguments or {}, timeout_s=timeout_s)
        if resp.get("error"):
            return {"error": resp["error"].get("message"), "code": resp["error"].get("code"), "tool": tn, "server_id": sid}
        return resp.get("result") or resp

    # Fallback to key lookup in tool catalog
    key = f"mcp.{sid}.{tn}" if sid else tn
    async with _MCP_CLIENT_LOCK:
        info = _MCP_CLIENT_TOOLS.get(key)

    if info:
        return await _mcp_call_tool(key, arguments)

    return {"error": f"unknown MCP server or tool: {sid}.{tn}", "code": -32601, "tool": tn, "server_id": sid}

async def _mcp_call_tool(key: str, args: dict) -> dict:
    """Forward a tools/call to the MCP server that owns this namespaced tool."""
    async with _MCP_CLIENT_LOCK:
        info = _MCP_CLIENT_TOOLS.get(key)
    if not info:
        return {"error": f"unknown MCP tool: {key}"}

    transport = info.get("transport", "http").lower()
    sid = info.get("server_id", "")
    target_tool = info.get("tool", key)

    if transport == "stdio":
        cli = _MCP_STDIO_CLIENTS.get(sid)
        if cli is None:
            return {"error": f"stdio client unavailable: {key}", "tool": key}
        resp = await cli._rpc(
            "tools/call",
            params={"name": target_tool, "arguments": args or {}},
            timeout_s=120.0,
        )
        if resp.get("error"):
            return {"error": resp["error"].get("message"), "code": resp["error"].get("code"), "tool": key}
        return resp.get("result") or {}

    # HTTP / SSE transport
    headers = _mcp_render_headers(info.get("headers_template") or {})
    url = info.get("url") or ""
    resp = await _mcp_http_rpc(
        url,
        headers,
        "tools/call",
        params={"name": target_tool, "arguments": args or {}},
        rid=int(time.time() * 1000) & 0x7FFFFFFF,
        timeout_s=120.0,
    )
    if resp.get("error"):
        return {"error": resp["error"].get("message"), "code": resp["error"].get("code"), "tool": key}
    return resp.get("result") or {}

# ---------------------------------------------------------------------------
# Declarative MCP Gateway Manager Class
# ---------------------------------------------------------------------------

class McpGateway:
    """Encapsulated Declarative MCP Server Lifecycle Manager and Schema Converter."""

    def __init__(self, specs: Optional[List[McpServerSpec]] = None):
        self.specs: Dict[str, McpServerSpec] = {}
        if specs:
            for s in specs:
                self.specs[s.id] = s

    def add_server(self, spec: McpServerSpec) -> None:
        self.specs[spec.id] = spec

    def load_from_toml(self, toml_source: Union[dict, str, bytes]) -> None:
        for spec in load_servers_from_toml(toml_source):
            self.specs[spec.id] = spec

    async def startup(self) -> None:
        for s in self.specs.values():
            await _mcp_probe_server(s.to_dict())

    async def shutdown(self) -> None:
        for cli in list(_MCP_STDIO_CLIENTS.values()):
            try:
                await cli.close()
            except Exception:
                pass
        _MCP_STDIO_CLIENTS.clear()
        _MCP_HTTP_CLIENTS.clear()

    def get_servers(self) -> List[dict]:
        return [dict(v) for v in _MCP_CLIENT_SERVERS.values()]

    def get_tools(self) -> List[dict]:
        return [
            {
                "name": k,
                "description": v.get("description"),
                "inputSchema": v.get("inputSchema"),
                "server_id": v.get("server_id"),
                "tier": v.get("tier"),
                "namespace": v.get("namespace"),
            }
            for k, v in _MCP_CLIENT_TOOLS.items()
        ]

    def get_openai_tools(self) -> List[dict]:
        return [
            convert_mcp_to_openai_schema(
                {"name": k, "description": v.get("description"), "inputSchema": v.get("inputSchema")},
                server_id=v.get("server_id", ""),
            )
            for k, v in _MCP_CLIENT_TOOLS.items()
        ]

    async def dispatch(self, server_id: str, tool_name: str, arguments: dict) -> dict:
        return await dispatch_tool_call(server_id, tool_name, arguments)

# ---------------------------------------------------------------------------
# FastAPI Router & Endpoint Logic
# ---------------------------------------------------------------------------

async def mcp_clients_logic() -> JSONResponse:
    """Inspect consumer-side MCP clients: server status, tools_count, protocolVersion."""
    async with _MCP_CLIENT_LOCK:
        servers = [dict(v) for v in _MCP_CLIENT_SERVERS.values()]
        total = len(_MCP_CLIENT_TOOLS)
    return JSONResponse({"object": "mios.mcp.clients", "servers": servers, "tools_total": total})

async def mcp_tools_list_logic() -> JSONResponse:
    """List discovered external MCP tools namespaced as 'mcp.<server>.<tool>'."""
    async with _MCP_CLIENT_LOCK:
        tools = [
            {
                "name": k,
                "description": v.get("description"),
                "inputSchema": v.get("inputSchema"),
                "server_id": v.get("server_id"),
            }
            for k, v in _MCP_CLIENT_TOOLS.items()
        ]
    return JSONResponse({"object": "mios.mcp.tools", "tools": tools})

async def mcp_dispatch_logic(request: Request) -> JSONResponse:
    """Forward tools/call to target MCP server: body {tool: 'mcp.<server>.<tool>', args: {...}}."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    tool = str(body.get("tool") or body.get("name") or "").strip()
    args = body.get("args") or body.get("arguments") or {}
    if not tool:
        return JSONResponse({"error": "missing 'tool'"}, status_code=400)

    res = await _mcp_call_tool(tool, args)
    return JSONResponse(res)

mcp_router = APIRouter()

@mcp_router.get("/v1/mcp/clients")
async def mcp_clients() -> JSONResponse:
    return await mcp_clients_logic()

@mcp_router.get("/v1/mcp/tools")
async def mcp_tools_list() -> JSONResponse:
    return await mcp_tools_list_logic()

@mcp_router.post("/v1/mcp/dispatch")
async def mcp_dispatch(request: Request) -> JSONResponse:
    return await mcp_dispatch_logic(request)

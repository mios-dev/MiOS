#!/usr/bin/env python3
# AI-hint: JSON-RPC 2.0 client transports for MCP servers -- HTTP/SSE and long-lived stdio subprocesses.
# AI-related: mios_mcp, mios_mcp_schema, /usr/libexec/mios/mcp-server-runner
"""The two MCP client transports, split out of mios_mcp.py.

Neither transport touches the injected module state in mios_mcp (the client
factory, the shared tool registry and its lock, the embedder): they take
everything they need as arguments, which is what made this the safe cut when
the module went past the 800-line ceiling.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
import logging
from typing import List, Optional

import httpx

from mios_jsonsalvage import loads_lenient as _loads_lenient

log = logging.getLogger("mios-agent-pipe")

from mios_config import _toml_section

# Protocol version, sandbox policy and header rendering live with the transports
# that use them, so this module imports nothing from mios_mcp -- mios_mcp imports
# them back from here. That direction is what keeps the split acyclic.
MCP_PROTOCOL_VERSION = str(
    os.environ.get("MIOS_MCP_PROTOCOL_VERSION")
    or (_toml_section("mcp") or {}).get("protocol_version")
    or "2025-11-25"
).strip()

_MCP_SANDBOX_CFG = (_toml_section("security") or {}).get("mcp_sandbox") or {}
if isinstance(_MCP_SANDBOX_CFG, str):
    _MCP_SANDBOX_CFG = {}
MCP_SANDBOX_ENABLE = (
    str(os.environ.get("MIOS_MCP_SANDBOX") or _MCP_SANDBOX_CFG.get("enable", "false"))
    .strip()
    .lower()
    not in {"false", "0", "no", "off", ""}
)
MCP_SANDBOX_GATEKEEPER = "/usr/libexec/mios/mcp-server-runner"

_MCP_ENV_RE = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def _mcp_render_headers(h: dict) -> dict:
    """Expand ${ENV_VAR} placeholders (e.g. for Bearer tokens held in the environment)."""
    out: dict = {}
    for k, v in (h or {}).items():
        s = str(v)
        for var in _MCP_ENV_RE.findall(s):
            s = s.replace("${" + var + "}", os.environ.get(var, ""))
        out[k] = s
    return out


# HTTP / SSE JSON-RPC 2.0 Client Transport
# ---------------------------------------------------------------------------

async def _mcp_http_rpc(
    url: str,
    headers: dict,
    method: str,
    params: Optional[dict] = None,
    rid: int = 1,
    timeout_s: float = 30.0,
) -> dict:
    """Single JSON-RPC 2.0 call to an MCP server over HTTP/SSE.
    Handles application/json and text/event-stream (SSE) streaming responses."""
    body: dict = {"jsonrpc": "2.0", "id": rid, "method": method}
    if params is not None:
        body["params"] = params
    h = dict(headers or {})
    h.setdefault("Content-Type", "application/json")
    h.setdefault("Accept", "application/json, text/event-stream")

    try:
        # Deferred import, and deliberately not a from-import at module scope:
        # mios_mcp.configure() REBINDS the client factory this resolves, and
        # mios_mcp imports this module, so binding the name here at load time
        # would both capture a stale factory and close the import cycle.
        from mios_mcp import _resolve_http_client

        client = await _resolve_http_client()
        r = await client.post(url, json=body, headers=h, timeout=timeout_s)
    except httpx.HTTPError as e:
        return {"error": {"code": -32000, "message": f"http error: {e}"}}

    if r.status_code != 200:
        return {"error": {"code": r.status_code, "message": (r.text or "")[:200]}}

    ct = (r.headers.get("content-type") or "").lower()
    if "text/event-stream" in ct:
        text_content = getattr(r, "text", "")
        if not text_content and hasattr(r, "body"):
            body_val = r.body
            text_content = body_val.decode("utf-8", "replace") if isinstance(body_val, bytes) else str(body_val)
        for chunk in text_content.split("\n\n"):
            for line in chunk.splitlines():
                if line.startswith("data:"):
                    try:
                        return _loads_lenient(line[5:].strip())
                    except Exception:
                        continue
        return {"error": {"code": -32700, "message": "no SSE data event"}}

    try:
        if hasattr(r, "json") and callable(r.json):
            return r.json()
        elif hasattr(r, "body"):
            raw = r.body
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", "replace")
            return _loads_lenient(raw)
        elif hasattr(r, "text"):
            return _loads_lenient(r.text)
        return {"error": {"code": -32700, "message": "non-JSON response"}}
    except Exception:
        return {"error": {"code": -32700, "message": "non-JSON response"}}

class _McpHttpClient:
    """HTTP/SSE MCP transport client."""

    def __init__(self, sid: str, url: str, headers: Optional[dict] = None, transport: str = "http"):
        self.sid = sid
        self.url = url.rstrip("/")
        self.headers = dict(headers or {})
        self.transport = transport
        self._inited = False
        self._init_result: dict = {}

    async def initialize(self) -> dict:
        rendered = _mcp_render_headers(self.headers)
        res = await _mcp_http_rpc(
            self.url,
            rendered,
            "initialize",
            params={
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "mios-agent-pipe", "version": "1.0"},
            },
            timeout_s=30.0,
        )
        if res.get("error"):
            self._inited = False
            return res
        self._inited = True
        self._init_result = res.get("result") or {}
        # Send initialized notification if possible
        asyncio.create_task(
            _mcp_http_rpc(
                self.url,
                rendered,
                "notifications/initialized",
                params={},
                rid=0,
                timeout_s=5.0,
            )
        )
        return self._init_result

    async def list_tools(self, cursor: Optional[str] = None) -> dict:
        rendered = _mcp_render_headers(self.headers)
        params = {"cursor": cursor} if cursor else {}
        return await _mcp_http_rpc(
            self.url,
            rendered,
            "tools/list",
            params=params,
            rid=int(time.time() * 1000) & 0x7FFFFFFF,
            timeout_s=30.0,
        )

    async def call_tool(self, name: str, arguments: dict, timeout_s: float = 120.0) -> dict:
        rendered = _mcp_render_headers(self.headers)
        return await _mcp_http_rpc(
            self.url,
            rendered,
            "tools/call",
            params={"name": name, "arguments": arguments or {}},
            rid=int(time.time() * 1000) & 0x7FFFFFFF,
            timeout_s=timeout_s,
        )

    async def close(self) -> None:
        self._inited = False

# ---------------------------------------------------------------------------
# Stdio JSON-RPC 2.0 Subprocess Client
# ---------------------------------------------------------------------------

class _McpStdioClient:
    """Subprocess stdio JSON-RPC 2.0 MCP client with resilient lifecycle management."""

    def __init__(self, sid: str, command: str, args: Optional[List[str]] = None, env: Optional[dict] = None, cwd: Optional[str] = None):
        self.sid = sid
        self.command = command
        self.args = list(args or [])
        self.env = dict(env or {})
        self.cwd = cwd or None
        self.proc: Optional[asyncio.subprocess.Process] = None
        self._pending: dict = {}  # rid -> Future
        self._lock = asyncio.Lock()  # serialize (re)spawn + initialize
        self._reader: Optional[asyncio.Task] = None
        self._idc = 0  # monotonic request ID
        self._inited = False
        self._init_result: dict = {}

    def _next_id(self) -> int:
        self._idc += 1
        return self._idc

    async def _spawn(self) -> None:
        child_env = dict(os.environ)
        child_env.update(_mcp_render_headers(self.env))
        _cmd = self.command
        _args = list(self.args)

        if MCP_SANDBOX_ENABLE and os.path.isfile(MCP_SANDBOX_GATEKEEPER):
            log.info("mcp sandbox: routing %s through gatekeeper %s", self.sid, MCP_SANDBOX_GATEKEEPER)
            child_env["MIOS_MCP_SANDBOX"] = "true"
            _wap = _MCP_SANDBOX_CFG.get("write_allowed_paths") or []
            if isinstance(_wap, list):
                child_env["MIOS_WRITE_ALLOWED_PATHS"] = ":".join(str(p) for p in _wap)
            _args = [_cmd] + _args
            _cmd = MCP_SANDBOX_GATEKEEPER

        self.proc = await asyncio.create_subprocess_exec(
            _cmd,
            *_args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=child_env,
            cwd=self.cwd,
        )
        self._inited = False
        self._reader = asyncio.create_task(self._read_loop(self.proc))
        asyncio.create_task(self._stderr_log(self.proc))

    async def _stderr_log(self, proc: asyncio.subprocess.Process) -> None:
        try:
            if proc.stderr is not None:
                data = await proc.stderr.read(4000)
                if data:
                    log.warning(
                        "mcp stdio[%s] stderr: %s",
                        self.sid,
                        data.decode("utf-8", "replace").strip()[:1200],
                    )
        except Exception:
            pass

    async def _read_loop(self, proc: asyncio.subprocess.Process) -> None:
        try:
            while True:
                if proc.stdout is None:
                    break
                line = await proc.stdout.readline()
                if not line:
                    break
                s = line.strip()
                if not s:
                    continue
                try:
                    msg = _loads_lenient(s.decode("utf-8", "replace") if isinstance(s, bytes) else s)
                except Exception:
                    continue  # ignore non-message stdout lines
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
                    fut.set_result({"error": {"code": -32000, "message": "stdio server exited"}})
            self._pending.clear()
            if self.proc is proc:
                self.proc = None
                self._inited = False

    async def _send(self, body: dict) -> None:
        if self.proc is None or self.proc.stdin is None:
            raise RuntimeError("stdio subprocess not running")
        payload = (json.dumps(body, ensure_ascii=False) + "\n").encode("utf-8")
        self.proc.stdin.write(payload)
        await self.proc.stdin.drain()

    async def _await_rpc(self, method: str, params: Optional[dict] = None, timeout_s: float = 30.0) -> dict:
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
            return {"error": {"code": -32000, "message": f"stdio timeout ({method})"}}
        except Exception as e:
            self._pending.pop(rid, None)
            return {"error": {"code": -32000, "message": f"stdio error: {e}"}}

    async def _ensure_session(self) -> None:
        async with self._lock:
            if self.proc is not None and self.proc.returncode is None and self._inited:
                return
            if self.proc is None or self.proc.returncode is not None:
                try:
                    await self._spawn()
                except Exception as e:
                    self.proc = None
                    self._inited = False
                    log.warning("mcp stdio: spawn failed for %s: %s", self.sid, e)
                    return

            init = await self._await_rpc(
                "initialize",
                {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "mios-agent-pipe", "version": "1.0"},
                },
                30.0,
            )
            if init.get("error"):
                self._inited = False
                return
            self._init_result = init.get("result") or {}
            try:
                await self._send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            except Exception:
                pass
            self._inited = True

    async def _rpc(self, method: str, params: Optional[dict] = None, timeout_s: float = 30.0) -> dict:
        await self._ensure_session()
        if not self._inited or self.proc is None:
            return {"error": {"code": -32000, "message": "stdio session unavailable"}}
        return await self._await_rpc(method, params, timeout_s)

    async def initialize(self) -> dict:
        await self._ensure_session()
        return self._init_result if self._inited else {"error": "stdio init failed"}

    async def list_tools(self, cursor: Optional[str] = None) -> dict:
        params = {"cursor": cursor} if cursor else {}
        return await self._rpc("tools/list", params=params)

    async def call_tool(self, name: str, arguments: dict, timeout_s: float = 120.0) -> dict:
        return await self._rpc("tools/call", params={"name": name, "arguments": arguments or {}}, timeout_s=timeout_s)

    async def close(self) -> None:
        try:
            if self._reader is not None:
                self._reader.cancel()
            p = self.proc
            if p is not None and p.returncode is None:
                if p.stdin is not None:
                    try:
                        p.stdin.close()
                    except Exception:
                        pass
                try:
                    await asyncio.wait_for(p.wait(), 2.0)
                except Exception:
                    try:
                        p.terminate()
                        await asyncio.wait_for(p.wait(), 2.0)
                    except Exception:
                        try:
                            p.kill()
                        except Exception:
                            pass
        except Exception:
            pass
        finally:
            self.proc = None
            self._inited = False

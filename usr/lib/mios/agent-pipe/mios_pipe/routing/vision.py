# AI-hint: VISION + CLIENT-TOOLS responders extracted VERBATIM from server.py (refactor R9 wave).
# AI-doc: usr/share/doc/mios/manual/routing.md

from __future__ import annotations

import base64
import json
import os
import re
import time
import logging
from typing import Any, AsyncGenerator, Optional

import httpx
from fastapi.responses import JSONResponse, StreamingResponse

from mios_sse import _sse_chunk, _sse_done
from mios_toolexec import _format_tool_error
from mios_jsonsalvage import loads_lenient as _loads_lenient
from mios_dispatch import dispatch_mios_verb
from mios_config import _AUTH_HOSTPORTS, _TOOL_BACKEND, _TOOL_BACKEND_MODEL
import mios_tokenize  # WS-A5 tokenizer seam -- token estimate for the ctx clamp

log = logging.getLogger("mios-agent-pipe")

VISION_MODEL = ""
VISION_ENDPOINT = ""
_BACKEND_KEY = ""
DEFAULT_TOOL_CAP = 24

_VERB_CATALOG: dict = {}

_get_client = None
_verb_to_openai_tool = None
_resolve_verb_key = None
_agent_contract = None
_pick_tool_backend = None
_select_child_tools = None
_tool_call_sig = None

async def _safe_get_client():
    if callable(_get_client):
        return await _get_client()
    return httpx.AsyncClient()

def configure(*, vision_model=None, vision_endpoint=None, backend_key=None,
              default_tool_cap=None, verb_catalog=None, get_client=None,
              verb_to_openai_tool=None, resolve_verb_key=None,
              agent_contract=None, pick_tool_backend=None,
              select_child_tools=None, tool_call_sig=None) -> None:
    """Inject server.py's VLM-lane config, the live verb catalog and the runtime
    helpers the vision + client-tools responders call back into."""
    global VISION_MODEL, VISION_ENDPOINT, _BACKEND_KEY, DEFAULT_TOOL_CAP
    global _VERB_CATALOG, _get_client, _verb_to_openai_tool, _resolve_verb_key
    global _agent_contract, _pick_tool_backend, _select_child_tools, _tool_call_sig
    if vision_model is not None:
        VISION_MODEL = vision_model
    if vision_endpoint is not None:
        VISION_ENDPOINT = vision_endpoint
    if backend_key is not None:
        _BACKEND_KEY = backend_key
    if default_tool_cap is not None:
        DEFAULT_TOOL_CAP = default_tool_cap
    if verb_catalog is not None:
        _VERB_CATALOG = verb_catalog
    if get_client is not None:
        _get_client = get_client
    if verb_to_openai_tool is not None:
        _verb_to_openai_tool = verb_to_openai_tool
    if resolve_verb_key is not None:
        _resolve_verb_key = resolve_verb_key
    if agent_contract is not None:
        _agent_contract = agent_contract
    if pick_tool_backend is not None:
        _pick_tool_backend = pick_tool_backend
    if select_child_tools is not None:
        _select_child_tools = select_child_tools
    if tool_call_sig is not None:
        _tool_call_sig = tool_call_sig

def _messages_have_image(messages: list) -> bool:
    """True if any message carries OpenAI vision content (a content list with
    an image_url / input_image part) -- the signal to route this turn to the
    local VLM instead of the text executor (which cannot see images)."""
    for m in messages or []:
        if not isinstance(m, dict):
            continue
        c = m.get("content")
        if isinstance(c, list):
            for part in c:
                if isinstance(part, dict) and part.get("type") in (
                        "image_url", "input_image", "image"):
                    return True
    return False

_VISION_UNAVAILABLE_MSG = (
    "I can't read images right now — the local vision model isn't loaded on this "
    "machine. Image understanding returns once the vision model is provisioned; "
    "text questions still work normally.")

def _vision_backend_failed(status: int, body_text: str) -> bool:
    """True when a vision-backend response means the VLM did NOT actually run
    (model unprovisioned / failed to load) rather than a real reply. llama-swap
    returns 5xx with 'exited prematurely'/'upstream command' when the GGUF is
    absent; surface those as an honest 'unavailable', never relay them raw."""
    if status >= 500:
        return True
    _bl = (body_text or "").lower()
    return any(s in _bl for s in ("exited prematurely", "upstream command",
                                  "no router for", "failed to load model",
                                  "image inputs are not supported"))

_VISION_FETCH_FAILED_MSG = (
    "I couldn't open that image — the link didn't return a viewable image (it may "
    "be a web page, a video, or unreachable). Upload the image directly, or share a "
    "direct image link (.png/.jpg/.gif), and I'll describe what's actually in it.")

_VISION_MAX_BYTES = int(os.environ.get("MIOS_VISION_MAX_BYTES", str(40 * 1024 * 1024)))

def _vision_msg_response(msg: str, streaming: bool, chat_id: str, model: str) -> Any:
    """An honest vision message as a real OpenAI assistant turn (chat.completion /
    SSE), so OWUI + Discord render it as a normal reply (not an error body)."""
    if streaming:
        async def _g() -> AsyncGenerator[bytes, None]:
            yield _sse_chunk(msg, chat_id=chat_id, model=model, role="assistant")
            yield _sse_chunk("", chat_id=chat_id, model=model, finish_reason="stop")
            yield _sse_done()
        return StreamingResponse(_g(), media_type="text/event-stream")
    # chat_id ALREADY carries the "chatcmpl-" prefix (routing/chat.py mints it as
    # f"chatcmpl-{uuid4}"), so re-prefixing emitted "chatcmpl-chatcmpl-..." -- and a
    # different id from the SSE branch two lines up, which passes chat_id through
    # bare. `created` is required on an OpenAI chat.completion; _client_tools_wrap
    # below is the correct shape to match.
    return JSONResponse(content={
        "id": chat_id, "object": "chat.completion",
        "created": int(time.time()), "model": model,
        "choices": [{"index": 0,
                     "message": {"role": "assistant", "content": msg},
                     "finish_reason": "stop"}]}, status_code=200)

def _vision_unavailable_response(streaming: bool, chat_id: str, model: str) -> Any:
    return _vision_msg_response(_VISION_UNAVAILABLE_MSG, streaming, chat_id, model)

def _resolve_media_url_from_html(html: str) -> Optional[str]:
    """Resolve a media-asset URL from a page's HTML metadata -- GENERIC (JSON-LD
    contentUrl, og:image, og:video, twitter:image), no site-specific keyword, so it
    works for Tenor/Imgur/etc. First hit wins (operator rule: no hardcoded domains)."""
    m = re.search(r'"contentUrl"\s*:\s*"([^"]+\.(?:gif|mp4|webp|png|jpe?g)[^"]*)"',
                  html or "", re.I)
    if m:
        try:
            return m.group(1).encode().decode("unicode_escape")
        except Exception:  # noqa: BLE001
            return m.group(1)
    for _prop in ("og:image", "og:video:secure_url", "og:video", "twitter:image"):
        m = re.search(r'<meta[^>]+(?:property|name)=["\']' + re.escape(_prop)
                      + r'["\'][^>]+content=["\']([^"\']+)["\']', html or "", re.I)
        if m:
            return m.group(1)
    return None

async def _vision_inline_remote_images(messages: list) -> bool:
    import io as _io
    ok = True
    client = await _get_client()
    _to = httpx.Timeout(connect=10.0, read=20.0, write=10.0, pool=10.0)
    _hdrs = {"user-agent": "Mozilla/5.0 (MiOS vision fetch)"}
    for _m in messages or []:
        if not isinstance(_m, dict):
            continue
        _c = _m.get("content")
        if not isinstance(_c, list):
            continue
        for _part in _c:
            if not isinstance(_part, dict):
                continue
            if _part.get("type") not in ("image_url", "input_image", "image"):
                continue
            _iu = _part.get("image_url")
            _url = (_iu.get("url") if isinstance(_iu, dict)
                    else (_iu if isinstance(_iu, str) else None))
            if not isinstance(_url, str) or _url.startswith("data:"):
                continue                                   # already inline / nothing to do
            if not _url.startswith(("http://", "https://")):
                continue
            try:
                r = await client.get(_url, follow_redirects=True, headers=_hdrs, timeout=_to)
                _ct = (r.headers.get("content-type") or "").lower()
                _data = r.content
                if not _ct.startswith("image/"):
                    _media = _resolve_media_url_from_html(r.text)
                    if not _media:
                        ok = False
                        continue
                    r2 = await client.get(_media, follow_redirects=True,
                                          headers=_hdrs, timeout=_to)
                    _data = r2.content
                if not _data or len(_data) > _VISION_MAX_BYTES:
                    ok = False
                    continue
                from PIL import Image as _PILImage
                _im = _PILImage.open(_io.BytesIO(_data))
                if getattr(_im, "is_animated", False):
                    _im.seek(max(0, getattr(_im, "n_frames", 1) // 2))  # middle frame
                _buf = _io.BytesIO()
                _im.convert("RGB").save(_buf, format="PNG")
                _durl = "data:image/png;base64," + base64.b64encode(_buf.getvalue()).decode()
                if isinstance(_iu, dict):
                    _iu["url"] = _durl
                else:
                    _part["image_url"] = {"url": _durl}
                log.info("vision: inlined remote image (%dB png) from %s", len(_durl), _url[:80])
            except Exception as _e:  # noqa: BLE001 -- degrade-open per part
                log.warning("vision image inline failed for %s: %s", _url[:80], _e)
                ok = False
    return ok

async def _vision_complete(body: dict, streaming: bool, chat_id: str,
                           model: str) -> Any:
    """Proxy an image-bearing turn to the local VLM (OpenAI-compatible, on the
    dGPU lane). Streams the VLM SSE verbatim; non-stream returns its JSON. When
    the vision model is unprovisioned / fails to load, returns an HONEST 'vision
 unavailable' assistant turn instead of relaying a raw 5xx (
    'FIX ALL VISION' -- the confusing leaf error was the reported failure)."""
    if not (VISION_MODEL or "").strip():
        return _vision_unavailable_response(streaming, chat_id, model)
    _msgs = body.get("messages")
    if isinstance(_msgs, list) and _messages_have_image(_msgs):
        try:
            if not await _vision_inline_remote_images(_msgs):
                return _vision_msg_response(_VISION_FETCH_FAILED_MSG, streaming,
                                            chat_id, model)
        except Exception as _e:  # noqa: BLE001 -- never block the turn
            log.warning("vision inline pre-step error: %s", _e)
    vbody = dict(body)
    vbody["model"] = VISION_MODEL
    headers = {"content-type": "application/json"}
    if _BACKEND_KEY:
        headers["authorization"] = f"Bearer {_BACKEND_KEY}"
    url = f"{VISION_ENDPOINT}/v1/chat/completions"
    client = await _get_client()
    if not streaming:
        vbody["stream"] = False
        try:
            r = await client.post(
                url, content=json.dumps(vbody).encode("utf-8"), headers=headers)
        except Exception as e:
            log.warning("vision backend failed: %s", e)
            return _vision_unavailable_response(False, chat_id, model)
        if _vision_backend_failed(r.status_code, r.text):
            log.warning("vision backend unavailable (status=%s): %s",
                        r.status_code, (r.text or "")[:200])
            return _vision_unavailable_response(False, chat_id, model)
        return JSONResponse(content=r.json(), status_code=r.status_code)

    async def _gen() -> AsyncGenerator[bytes, None]:
        vbody["stream"] = True
        try:
            async with client.stream(
                    "POST", url,
                    content=json.dumps(vbody).encode("utf-8"),
                    headers=headers) as resp:
                if _vision_backend_failed(resp.status_code, ""):
                    _err = await resp.aread()
                    log.warning("vision stream unavailable (status=%s): %s",
                                resp.status_code, (_err[:200] if _err else b""))
                    yield _sse_chunk(_VISION_UNAVAILABLE_MSG, chat_id=chat_id,
                                     model=model, role="assistant")
                    yield _sse_chunk("", chat_id=chat_id, model=model,
                                     finish_reason="stop")
                    yield _sse_done()
                    return
                async for chunk in resp.aiter_bytes():
                    yield chunk
        except Exception as e:
            log.warning("vision stream failed: %s", e)
            yield _sse_chunk(_VISION_UNAVAILABLE_MSG, chat_id=chat_id, model=model,
                             role="assistant")
            yield _sse_chunk("", chat_id=chat_id, model=model, finish_reason="stop")
            yield _sse_done()

    return StreamingResponse(_gen(), media_type="text/event-stream")

def _has_client_tools(body: dict) -> bool:
    """True when the CALLER supplied its own OpenAI tools[] -- the signal that this
    is client-side tool-calling (the client executes the functions and wants
    tool_calls back), NOT a MiOS-orchestrated turn. OWUI strips tools before
    calling the pipe and the mios CLI is Hermes-direct, so this is False for them
    (zero regression). Empty/missing tools -> False (normal orchestration)."""
    if not isinstance(body, dict) or str(body.get("tool_choice") or "").strip().lower() == "none":
        return False
    t = body.get("tools")
    return isinstance(t, list) and len(t) > 0

_CLIENT_TOOLS_IDENTITY = (
    "You are MiOS AI, the local agentic assistant of MiOS (a private, offline-first "
    "AI operating system running on this machine). You are NOT a Mozilla, Firefox, "
    "or \"Smart Window\" product -- any such framing in other instructions names "
    "only the surface you are embedded in, never your identity or your limits.\n"
    "Beyond any browser tools the client provided, the tools[] list ALSO contains the "
    "full MiOS tool surface: launching applications, controlling windows, web search, "
    "messaging, persistent memory, OS recipes, and file search. THESE are the \"MiOS tools\" / "
    "\"MCP tools\" a user refers to. When asked to do something on the computer (open "
    "an app, run a search, send a message, remember something), CALL the matching tool -- never reply "
    "that you cannot open apps, send messages, or that you lack tools. "
    "For ANY action tool (messaging, file ops, launch, etc.), you MUST actually call the tool "
    "with the correct parameters -- NEVER claim success, narrate, or make excuses "
    "about lack of intent/permissions without actually executing the tool. "
    "To open any application by name use launch_app (it resolves Windows AND Linux apps); "
    "use launch_windows_app for a Windows-only app and open_url to open a web page. "
    "For any question about the host, OS, version, or environment, call system_status "
    "(or sys_env) and answer from its `os` field -- never state the OS from training data "
    "(you are a Fedora/GNOME Linux userland that may run inside a Windows host via WSL2; "
    "verify, never assume \"Windows 10\")."
)

def _client_tools_mios_surface() -> list:
    """The MiOS verb catalog projected as OpenAI tools, for merging into a
    client-tools turn. Non-rare only -- the catalog's own [verbs.*].tier is the
    SSOT for 'commonly needed', so this is principled selection, not a hardcoded
    allow/deny list."""
    out: list = []
    for _vname, _vcfg in _VERB_CATALOG.items():
        try:
            if (_vcfg.get("tier") or "") == "rare":
                continue
            out.append(_verb_to_openai_tool(_vname, _vcfg))
        except Exception:  # noqa: BLE001
            continue
    return out

def _client_tools_is_mios(name: str, client_names: set) -> bool:
    if not name:
        return False
    try:
        return _resolve_verb_key(name) in _VERB_CATALOG
    except Exception:  # noqa: BLE001
        return False

def _client_tools_inject_identity(messages: list) -> list:
    _contract = _agent_contract()
    lead = (_contract + "\n\n" + _CLIENT_TOOLS_IDENTITY) if _contract else _CLIENT_TOOLS_IDENTITY
    msgs = [dict(m) for m in messages if isinstance(m, dict)]
    if msgs and msgs[0].get("role") in ("system", "developer"):
        base = str(msgs[0].get("content") or "")
        msgs[0]["content"] = lead + "\n\n" + base
        return msgs
    return [{"role": "system", "content": lead}] + msgs

def _name_is_verb(name) -> bool:
    """True if a tool name resolves to a real MiOS verb (the client already carries
    the MiOS surface -- e.g. Hermes via its mios MCP client)."""
    if not name:
        return False
    try:
        resolver = _resolve_verb_key
        if not callable(resolver):
            try:
                from mios_pipe.routing.verbcatalog import _resolve_verb_key as default_resolver
                resolver = default_resolver
            except Exception:  # noqa: BLE001
                resolver = None
        key = resolver(str(name)) if callable(resolver) else str(name)
        return key in _VERB_CATALOG
    except Exception:  # noqa: BLE001
        return False

_ELIDED_TOOL_RESULT = "[tool result elided to fit context budget]"
_ELIDED_IMAGE = "[image omitted to fit context budget]"
_TRUNC_MARKER = "\n[...truncated to fit context budget...]"
_DEFAULT_TOOL_CTX = 32768


def _tool_ctx() -> int:
    """Context window for the client-tools lane (env MIOS_AGENT_PIPE_TOOL_CTX).
    An unparsable or non-positive value falls back to the default instead of
    raising out of the degrade path."""
    try:
        val = int(os.environ.get("MIOS_AGENT_PIPE_TOOL_CTX", "") or _DEFAULT_TOOL_CTX)
        return val if val > 0 else _DEFAULT_TOOL_CTX
    except (TypeError, ValueError):
        return _DEFAULT_TOOL_CTX


def _call_ids(msg) -> list:
    if not isinstance(msg, dict) or msg.get("role") != "assistant":
        return []
    return [c.get("id") for c in (msg.get("tool_calls") or [])
            if isinstance(c, dict) and c.get("id")]


def _repair_message_shape(messages: list) -> list:
    """Restore an OpenAI-valid sequence after messages were dropped.

    * every assistant tool_call keeps a matching tool result (unanswered calls
      are removed from the assistant message);
    * every tool result answers a tool_call of the nearest preceding assistant
      turn (orphans are dropped);
    * the first non-system turn is a user turn;
    * consecutive plain user/assistant turns are merged so roles alternate.
    """
    msgs = [m for m in messages if isinstance(m, dict)]
    answered = {m.get("tool_call_id") for m in msgs if m.get("role") == "tool"}
    fixed: list = []
    open_ids: set = set()
    for m in msgs:
        role = m.get("role")
        if role == "assistant" and m.get("tool_calls"):
            calls = [c for c in m["tool_calls"]
                     if isinstance(c, dict) and c.get("id") in answered]
            m = {**m}
            if calls:
                m["tool_calls"] = calls
            else:
                m.pop("tool_calls", None)
                if not m.get("content"):
                    open_ids = set()
                    continue
            open_ids = {c.get("id") for c in calls}
        elif role == "tool":
            if m.get("tool_call_id") not in open_ids:
                continue
        elif role in ("user", "system", "developer"):
            open_ids = set()
        fixed.append(m)
    # First non-system turn must be a user turn.
    head = [m for m in fixed if m.get("role") in ("system", "developer")]
    body = [m for m in fixed if m.get("role") not in ("system", "developer")]
    while body and body[0].get("role") != "user":
        body.pop(0)
    # Merge consecutive plain turns of the same role.
    merged: list = []
    for m in body:
        prev = merged[-1] if merged else None
        plain = m.get("role") in ("user", "assistant") and not m.get("tool_calls")
        if (prev is not None and plain and prev.get("role") == m.get("role")
                and not prev.get("tool_calls")):
            a, b = prev.get("content"), m.get("content")
            if isinstance(a, list) or isinstance(b, list):
                la = a if isinstance(a, list) else ([{"type": "text", "text": a}] if a else [])
                lb = b if isinstance(b, list) else ([{"type": "text", "text": b}] if b else [])
                merged[-1] = {**prev, "content": la + lb}
            else:
                merged[-1] = {**prev, "content": "\n\n".join(x for x in (a, b) if x)}
            continue
        merged.append(m)
    return head + merged


def _drop_stale_tool_results(messages: list, ttl_turns: int = 1) -> list:
    """Elide tool results older than ttl_turns assistant turns.

    The result message is kept with placeholder content so every assistant
    tool_call still has its answer (dropping it would make the request invalid).
    """
    out = []
    assistant_count = 0
    for msg in reversed(messages):
        if isinstance(msg, dict):
            role = msg.get("role")
            if role == "assistant":
                assistant_count += 1
            if role in ("tool", "function") and assistant_count > ttl_turns:
                msg = {**msg, "content": _ELIDED_TOOL_RESULT}
        out.append(msg)
    return list(reversed(out))


def _content_tokens(content) -> int:
    if isinstance(content, list):
        total = 0
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                total += mios_tokenize.count_text(str(part.get("text") or ""))
            elif isinstance(part, dict):
                total += mios_tokenize.count_text(json.dumps(part))
        return total
    return mios_tokenize.count_text(str(content or ""))


def _truncate_text(text: str, max_tok: int) -> str:
    if mios_tokenize.count_text(text) <= max_tok:
        return text
    keep = max(10, max_tok - mios_tokenize.count_text(_TRUNC_MARKER))
    return mios_tokenize.truncate_to_tokens(text, keep) + _TRUNC_MARKER


def _truncate_content(content, max_tok: int):
    """Truncate content to about max_tok tokens, preserving its type.

    Strings are cut with a marker. OpenAI content-part lists stay lists: image
    parts become a text placeholder, then the largest text parts are cut.
    """
    if not isinstance(content, list):
        return _truncate_text(str(content or ""), max_tok)
    parts = []
    for part in content:
        if isinstance(part, dict) and part.get("type") not in (None, "text"):
            parts.append({"type": "text", "text": _ELIDED_IMAGE})
        elif isinstance(part, dict):
            parts.append(dict(part))
    while _content_tokens(parts) > max_tok:
        texts = [(mios_tokenize.count_text(str(p.get("text") or "")), i)
                 for i, p in enumerate(parts) if p.get("type") == "text"]
        if not texts:
            break
        tok, idx = max(texts)
        excess = _content_tokens(parts) - max_tok
        if tok <= 20:
            break
        parts[idx] = {**parts[idx],
                      "text": _truncate_text(str(parts[idx].get("text") or ""), max(10, tok - excess))}
        if mios_tokenize.count_text(str(parts[idx]["text"])) >= tok:
            break
    return parts


def _compact_tool_schema(tool: dict) -> dict:
    """Shrink a tool definition without changing its call signature: trim the
    function description and drop nested property descriptions/examples."""
    if not isinstance(tool, dict):
        return tool

    def _strip(node):
        if isinstance(node, dict):
            return {k: _strip(v) for k, v in node.items()
                    if k not in ("description", "examples", "example", "title")}
        if isinstance(node, list):
            return [_strip(v) for v in node]
        return node

    out = dict(tool)
    fn = dict(out.get("function") or {})
    if fn:
        if fn.get("description"):
            fn["description"] = _truncate_text(str(fn["description"]), 48)
        if isinstance(fn.get("parameters"), dict):
            fn["parameters"] = _strip(fn["parameters"])
        out["function"] = fn
    return out


def _tool_name(tool) -> str:
    if not isinstance(tool, dict):
        return ""
    return str((tool.get("function") or {}).get("name") or tool.get("name") or "")


def _forced_tool_name(tool_choice) -> str:
    if isinstance(tool_choice, dict):
        return str((tool_choice.get("function") or {}).get("name") or tool_choice.get("name") or "")
    return ""


def _budget_tools(tools: list, budget: int, forced: str) -> list:
    """Keep tools in caller order (forced tool first) while they fit `budget`."""
    ordered = sorted(tools, key=lambda t: 0 if forced and _tool_name(t) == forced else 1)
    kept, used = [], 0
    for t in ordered:
        cost = mios_tokenize.count_messages([], tools=[t])
        if kept and used + cost > budget and _tool_name(t) != forced:
            continue
        kept.append(t)
        used += cost
    return kept


def _prune_request_to_context_budget(req: dict, max_ctx: int = _DEFAULT_TOOL_CTX) -> dict:
    """Principled multi-tier request pruning before backend dispatch so the
    payload fits the backend context instead of failing with HTTP 400.

    Tiers (each runs only while still over budget):
      1. tool_choice 'none' -> drop tools and tool_choice.
      2. Elide stale tool results (placeholder keeps tool_call pairing).
      3. Compact middle turns via plan_compaction, then repair the sequence.
      4. Budget tool definitions: compact schemas, then keep tools in caller
         order (forced tool always kept) within half the budget.
      5. Truncate each oversized message (content-part aware).
      6. Iteratively truncate the largest message.
    Finally repair the sequence and clamp max_tokens to what actually fits.
    """
    req = dict(req)
    messages = [m for m in list(req.get("messages") or []) if isinstance(m, dict)]
    tools = [t for t in (req.get("tools") or []) if isinstance(t, dict)] \
        if isinstance(req.get("tools"), list) else None

    if str(req.get("tool_choice") or "").strip().lower() == "none":
        req.pop("tools", None)
        req.pop("tool_choice", None)
        tools = None

    def _count(msgs, tls):
        return mios_tokenize.count_messages(msgs, tools=tls or None)

    target = max(1024, max_ctx - 1024)
    in_tokens = _count(messages, tools)

    if in_tokens > target:
        messages = _drop_stale_tool_results(messages, ttl_turns=1)
        in_tokens = _count(messages, tools)

    if in_tokens > target:
        from mios_pipe.context.compact import plan_compaction
        tools_tok = _count([], tools) if tools else 0
        plan = plan_compaction(messages, budget=max(512, target - tools_tok),
                               keep_recent=4, keep_system=True)
        if plan.needed and plan.to_keep:
            messages = _repair_message_shape(plan.to_keep)
            in_tokens = _count(messages, tools)

    if in_tokens > target and tools:
        tool_budget = target // 2
        if _count([], tools) > tool_budget:
            tools = [_compact_tool_schema(t) for t in tools]
        if _count([], tools) > tool_budget:
            before = len(tools)
            tools = _budget_tools(tools, tool_budget, _forced_tool_name(req.get("tool_choice")))
            log.warning("context budget: kept %d of %d caller tools", len(tools), before)
        in_tokens = _count(messages, tools)

    if in_tokens > target:
        avail = max(256, target - (_count([], tools) if tools else 0))
        messages = [{**m, "content": _truncate_content(m.get("content"), avail)}
                    if m.get("content") and _content_tokens(m.get("content")) > avail else m
                    for m in messages]
        in_tokens = _count(messages, tools)

    for _ in range(64):
        if in_tokens <= target or not messages:
            break
        cands = [(_content_tokens(m.get("content")), i) for i, m in enumerate(messages)
                 if m.get("role") not in ("system", "developer") and m.get("content")]
        if not cands or max(cands)[0] < 50:
            cands = [(_content_tokens(m.get("content")), i)
                     for i, m in enumerate(messages) if m.get("content")]
        if not cands:
            break
        tok, idx = max(cands)
        if tok <= 25:
            break
        excess = in_tokens - target + 64
        messages[idx] = {**messages[idx],
                         "content": _truncate_content(messages[idx]["content"], max(25, tok - excess))}
        new_tokens = _count(messages, tools)
        if new_tokens >= in_tokens:
            break
        in_tokens = new_tokens

    messages = _repair_message_shape(messages)
    req["messages"] = messages
    if tools is not None:
        if tools:
            req["tools"] = tools
        else:
            req.pop("tools", None)
            req.pop("tool_choice", None)
    in_tokens = _count(messages, tools)

    cap = max_ctx - in_tokens - 256
    if cap < 64:
        log.warning("context budget: prompt %d leaves %d tokens of %d", in_tokens, cap, max_ctx)
        cap = 64
    req_mt = int(req.get("max_tokens") or 0)
    if req_mt <= 0 or req_mt > cap:
        req["max_tokens"] = cap
    return req


async def _client_tools_backend(req: dict) -> dict:
    try:
        req = _prune_request_to_context_budget(req, max_ctx=_tool_ctx())
    except Exception as _e:  # noqa: BLE001 -- never block the call on the clamp
        log.warning("client-tools context pruning failed: %s", _e)
    _url, _mdl = await _pick_tool_backend()

    async def _post(url: str, mdl: str):
        rq = dict(req)
        rq["model"] = mdl
        headers = {"content-type": "application/json"}
        _hp = url.split("://")[-1].split("/")[0]
        if _BACKEND_KEY and _hp in _AUTH_HOSTPORTS:
            headers["authorization"] = f"Bearer {_BACKEND_KEY}"
        client = await _safe_get_client()
        return await client.post(
            f"{url}/chat/completions",
            content=json.dumps(rq).encode("utf-8"), headers=headers)

    try:
        r = await _post(_url, _mdl)
    except Exception as _e:  # noqa: BLE001 -- network/timeout -> try light below
        log.warning("client-tools backend POST %s failed: %s", _url, _e)
        r = None
    if r is not None and r.status_code == 200:
        return r.json()
    if r is not None:
        try:
            _names = [((_t.get("function") or {}).get("name") or _t.get("name"))
                      for _t in (req.get("tools") or [])]
            log.warning(
                "client-tools backend %s (%s) -> HTTP %d; req[tools=%d tool_choice=%s "
                "ptc=%s msgs=%d]; names=%s; body=%s",
                _url, _mdl, r.status_code, len(req.get("tools") or []),
                req.get("tool_choice"), req.get("parallel_tool_calls"),
                len(req.get("messages") or []), _names[:40], r.text[:600])
        except Exception:  # noqa: BLE001
            pass
    if _url != _TOOL_BACKEND:
        try:
            r2 = await _post(_TOOL_BACKEND, _TOOL_BACKEND_MODEL)
            if r2.status_code == 200:
                log.info("client-tools: light-lane fallback succeeded after heavy non-200")
                return r2.json()
            log.warning("client-tools light-lane fallback -> HTTP %d: %s",
                        r2.status_code, r2.text[:400])
        except Exception as _e:  # noqa: BLE001
            log.warning("client-tools light-lane fallback failed: %s", _e)
    return {}

async def _client_tools_loop(body: dict, client_names: set, chat_id: str,
                             max_iters: int = 6) -> dict:
    """Hybrid server-side tool loop for a client-tools turn. Runs MiOS verbs
    server-side (dispatch_mios_verb) and loops; the moment the model emits a
    CLIENT tool_call (or plain content) it returns that assistant message for the
    caller to act on. So 'open notepad' executes via the MiOS launcher HERE, while
    'get_page_content' still rides back to the browser."""
    messages = _client_tools_inject_identity(list(body.get("messages") or []))
    _intent = ""
    for _m in reversed(body.get("messages") or []):
        if isinstance(_m, dict) and _m.get("role") == "user":
            _intent = str(_m.get("content") or "")
            break
    if not client_names and body.get("tools"):
        client_names = {((t.get("function") or {}).get("name") or t.get("name"))
                        for t in (body.get("tools") or []) if isinstance(t, dict)}

    if str(body.get("tool_choice") or "").strip().lower() == "none":
        tools = []
        _mios_sel = []
    else:
        has_mios_verbs = any(_name_is_verb(n) for n in client_names if n)
        if has_mios_verbs or len(client_names) >= DEFAULT_TOOL_CAP:
            log.info("client harness tools detected (%d tools, mios_verbs=%s) -> suppressing redundant _mios_sel",
                     len(client_names), has_mios_verbs)
            _mios_sel = []
        else:
            if callable(_select_child_tools):
                _mios_sel = await _select_child_tools(
                    _client_tools_mios_surface(), _intent, DEFAULT_TOOL_CAP)
                _mios_sel = [t for t in _mios_sel
                             if ((t.get("function") or {}).get("name") or t.get("name")) not in client_names]
            else:
                _mios_sel = []

        raw_tools = [t for t in (body.get("tools") or []) if isinstance(t, dict)] + _mios_sel
        seen_names = set()
        tools = []
        for t in raw_tools:
            tname = (t.get("function") or {}).get("name") or t.get("name")
            if tname and tname in seen_names:
                continue
            if tname:
                seen_names.add(tname)
            tools.append(t)

    base_req: dict = {"model": _TOOL_BACKEND_MODEL, "stream": False,
                      "parallel_tool_calls": False}
    if tools:
        base_req["tools"] = tools
    _tc_none = str(body.get("tool_choice") or "").strip().lower() == "none"
    for _k in ("temperature", "top_p", "max_tokens", "tool_choice", "parallel_tool_calls"):
        if _k == "tool_choice" and (_tc_none or not tools):
            continue  # a tool_choice with no tools makes OpenAI backends reject the call
        if _k in body:
            base_req[_k] = body[_k]
    base_req["chat_template_kwargs"] = {"enable_thinking": False}
    last: dict = {}
    _seen: set = set()
    for _ in range(max(1, max_iters)):
        req = dict(base_req)
        req["messages"] = messages
        resp = await _client_tools_backend(req)
        msg = ((resp.get("choices") or [{}])[0] or {}).get("message") or {}
        last = msg
        tcs = msg.get("tool_calls") or []
        if not tcs:
            if str(msg.get("content") or "").strip():
                return msg
            break
        if any(not _client_tools_is_mios(
                (tc.get("function") or {}).get("name", ""), client_names)
                for tc in tcs):
            return msg
        _sigs = [_tool_call_sig(_tc) for _tc in tcs]
        if _sigs and all(_s in _seen for _s in _sigs):
            messages.append(msg)
            for tc in tcs:
                messages.append({
                    "role": "tool", "tool_call_id": tc.get("id"),
                    "content": json.dumps({
                        "success": False,
                        "stderr": "Duplicate tool call detected. You have already called this tool with these arguments. Do not repeat tool calls. Take a different action or inform the user."
                    })
                })
            continue
        _seen.update(_sigs)
        messages.append(msg)
        for tc in tcs:
            fn = tc.get("function") or {}
            try:
                args = _loads_lenient(fn.get("arguments") or "{}")
            except Exception:  # noqa: BLE001
                args = {}
            try:
                result = await dispatch_mios_verb(
                    _resolve_verb_key(fn.get("name", "")), args, session_id=chat_id)
            except Exception as e:  # noqa: BLE001
                result = {"success": False, "stderr": f"dispatch error: {e}"}
            _err = _format_tool_error(result)
            if _err:
                result = _err
            messages.append({
                "role": "tool", "tool_call_id": tc.get("id"),
                "content": json.dumps(result)[:4000]})
    if not str((last or {}).get("content") or "").strip():
        try:
            _fr = dict(base_req)
            _fr.pop("tools", None)
            _fr.pop("tool_choice", None)
            _fr["chat_template_kwargs"] = {"enable_thinking": False}
            _fr["messages"] = messages
            _fresp = await _client_tools_backend(_fr)
            _fmsg = ((_fresp.get("choices") or [{}])[0] or {}).get("message") or {}
            if str(_fmsg.get("content") or "").strip():
                return _fmsg
            _orig_user = ""
            for _m in reversed(messages):
                if isinstance(_m, dict) and _m.get("role") == "user":
                    _orig_user = str(_m.get("content") or "")
                    break
            _mr = dict(base_req)
            _mr.pop("tools", None)
            _mr.pop("tool_choice", None)
            _mr["chat_template_kwargs"] = {"enable_thinking": False}
            _mr["messages"] = [
                {"role": "system", "content":
                 "You are the MiOS local agent -- a LOCAL open-weight model on this "
                 "machine (not Claude/GPT/Gemini). Answer the user directly."},
                {"role": "user", "content": _orig_user or "Introduce yourself briefly."}]
            _mresp = await _client_tools_backend(_mr)
            _mmsg = ((_mresp.get("choices") or [{}])[0] or {}).get("message") or {}
            if str(_mmsg.get("content") or "").strip():
                return _mmsg
        except Exception as _e:  # noqa: BLE001 -- degrade-open
            log.debug("client-tools final synthesis failed: %s", _e)
    if not str((last or {}).get("content") or "").strip() and not (last or {}).get("tool_calls"):
        return {"role": "assistant", "content":
                "I'm the MiOS local agent. I couldn't form a full reply just now -- "
                "please rephrase or ask again."}
    return last

def _client_tools_wrap(msg: dict, chat_id: str, model: str) -> dict:
    return {
        "id": chat_id, "object": "chat.completion", "model": model,
        "created": int(time.time()),
        "choices": [{
            "index": 0, "message": msg,
            "finish_reason": "tool_calls" if msg.get("tool_calls") else "stop"}],
    }

async def _client_tools_sse(msg: dict, chat_id: str,
                            model: str) -> AsyncGenerator[bytes, None]:
    base = {"id": chat_id, "object": "chat.completion.chunk", "created": int(time.time()), "model": model}

    def _chunk(delta: dict, finish: Optional[str] = None) -> bytes:
        return ("data: " + json.dumps({
            **base, "choices": [{"index": 0, "delta": delta,
                                 "finish_reason": finish}]}) + "\n\n").encode("utf-8")

    yield _chunk({"role": "assistant"})
    _rsn = msg.get("reasoning_content") or msg.get("reasoning")
    if _rsn:
        yield _chunk({"reasoning_content": _rsn, "reasoning": _rsn})
    tcs = msg.get("tool_calls") or []
    if tcs:
        for _i, tc in enumerate(tcs):
            fn = tc.get("function") or {}
            yield _chunk({"tool_calls": [{
                "index": _i, "id": tc.get("id"), "type": "function",
                "function": {"name": fn.get("name", ""),
                             "arguments": fn.get("arguments", "") or ""}}]})
        yield _chunk({}, finish="tool_calls")
    else:
        if msg.get("content"):
            yield _chunk({"content": msg["content"]})
        yield _chunk({}, finish="stop")
    yield b"data: [DONE]\n\n"

async def _client_tools_stream_relay(body: dict, chat_id: str, model: str) -> Any:
    _url, _mdl = await _pick_tool_backend()
    _ctx = _tool_ctx()
    tbody = dict(body)
    tbody["model"] = _mdl
    tbody["messages"] = _client_tools_inject_identity(list(body.get("messages") or []))
    tbody["chat_template_kwargs"] = {"enable_thinking": True}
    tbody["stream"] = True
    tbody.setdefault("parallel_tool_calls", False)
    for _k in ("mios_flags", "_allow_write", "num_ctx"):
        tbody.pop(_k, None)
    if str(tbody.get("tool_choice") or "").strip().lower() == "none":
        tbody.pop("tools", None)
        tbody.pop("tool_choice", None)
    try:
        tbody = _prune_request_to_context_budget(tbody, max_ctx=_ctx)
    except Exception as _e:  # noqa: BLE001
        log.warning("client-tools stream relay context pruning failed: %s", _e)
    headers = {"content-type": "application/json"}
    _hp = _url.split("://")[-1].split("/")[0]
    if _BACKEND_KEY and _hp in _AUTH_HOSTPORTS:
        headers["authorization"] = f"Bearer {_BACKEND_KEY}"
    url = f"{_url}/chat/completions"
    client = await _safe_get_client()

    async def _gen() -> AsyncGenerator[bytes, None]:
        try:
            async with client.stream(
                    "POST", url,
                    content=json.dumps(tbody).encode("utf-8"),
                    headers=headers) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk
        except Exception as e:  # noqa: BLE001
            log.warning("client-tools stream relay failed: %s", e)
            yield ("data: " + json.dumps(
                {"choices": [{"delta": {"content": f"[tool backend error: {e}]"}}]})
                + "\n\n").encode("utf-8")
            yield b"data: [DONE]\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")

async def _client_tools_complete(body: dict, streaming: bool, chat_id: str,
                                 model: str) -> Any:
    client_names: set = set()
    for _t in (body.get("tools") or []):
        try:
            client_names.add((_t.get("function") or {}).get("name") or _t.get("name"))
        except Exception:  # noqa: BLE001
            continue
    out_model = model or _TOOL_BACKEND_MODEL
    try:
        final_msg = await _client_tools_loop(body, client_names, chat_id)
        for _i, _tc in enumerate(final_msg.get("tool_calls") or []):
            if isinstance(_tc, dict) and not _tc.get("id"):
                _tc["id"] = f"call_{chat_id}_{_i}"
        if not streaming:
            return JSONResponse(
                content=_client_tools_wrap(final_msg, chat_id, out_model))
        return StreamingResponse(
            _client_tools_sse(final_msg, chat_id, out_model),
            media_type="text/event-stream")
    except Exception as e:  # noqa: BLE001
        log.warning("client-tools hybrid loop failed (%s) -> verbatim relay", e)
        return await _client_tools_relay(body, streaming)

async def _client_tools_relay(body: dict, streaming: bool) -> Any:
    """Degrade path: the original verbatim passthrough (browser tools only). Used
    when the hybrid loop errors so a smart-window browsing turn still works."""
    _ctx = _tool_ctx()
    tbody = dict(body)
    tbody["model"] = _TOOL_BACKEND_MODEL
    for _k in ("mios_flags", "_allow_write", "num_ctx"):
        tbody.pop(_k, None)
    if str(tbody.get("tool_choice") or "").strip().lower() == "none":
        tbody.pop("tools", None)
        tbody.pop("tool_choice", None)
    try:
        tbody = _prune_request_to_context_budget(tbody, max_ctx=_ctx)
    except Exception as _e:  # noqa: BLE001
        log.warning("client-tools relay context pruning failed: %s", _e)
    headers = {"content-type": "application/json"}
    _hp = _TOOL_BACKEND.split("://")[-1].split("/")[0]
    if _BACKEND_KEY and _hp in _AUTH_HOSTPORTS:
        headers["authorization"] = f"Bearer {_BACKEND_KEY}"
    url = f"{_TOOL_BACKEND}/chat/completions"
    client = await _safe_get_client()
    if not streaming:
        tbody["stream"] = False
        try:
            r = await client.post(
                url, content=json.dumps(tbody).encode("utf-8"), headers=headers)
            return JSONResponse(content=r.json(), status_code=r.status_code)
        except Exception as e:  # noqa: BLE001
            log.warning("client-tools relay backend failed: %s", e)
            return JSONResponse(
                content={"error": {"message": f"tool backend error: {e}",
                                   "type": "server_error"}}, status_code=502)

    async def _gen() -> AsyncGenerator[bytes, None]:
        tbody["stream"] = True
        try:
            async with client.stream(
                    "POST", url,
                    content=json.dumps(tbody).encode("utf-8"),
                    headers=headers) as resp:
                async for chunk in resp.aiter_bytes():
                    yield chunk
        except Exception as e:  # noqa: BLE001
            log.warning("client-tools relay stream failed: %s", e)
            yield ("data: " + json.dumps(
                {"choices": [{"delta": {"content": f"[tool backend error: {e}]"}}]})
                + "\n\n").encode("utf-8")
            yield b"data: [DONE]\n\n"

    return StreamingResponse(_gen(), media_type="text/event-stream")

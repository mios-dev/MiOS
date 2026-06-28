# AI-hint: VISION + CLIENT-TOOLS responders extracted VERBATIM from server.py (refactor R9 wave). Two image-/tool-bearing fast-path branches that BYPASS refine/council/polish: (1) the VISION branch -- _vision_complete proxies an image turn to the local VLM (OpenAI-compat, dGPU lane), inlining remote image/GIF/page URLs to base64 so the VLM can actually SEE them (_vision_inline_remote_images + _resolve_media_url_from_html), and an HONEST-ERROR gate (_vision_backend_failed / _vision_unavailable_response / _vision_msg_response) that returns a clear "vision unavailable / couldn't open that image" assistant turn instead of relaying a raw 5xx or fabricating a description; (2) the CLIENT-TOOLS hybrid loop -- _client_tools_complete runs an OpenAI client-tools turn (Zen smart-window / Hermes desktop) where MiOS asserts its own identity (_client_tools_inject_identity + _CLIENT_TOOLS_IDENTITY), merges the MiOS verb surface server-side (_client_tools_mios_surface), EXECUTES MiOS verbs HERE via the broker (_client_tools_loop), and rides only the caller's own tool_calls back (_client_tools_is_mios / _client_tools_wrap / _client_tools_sse), with a heavy->light backend fallback (_client_tools_backend), a live SSE relay for full-agent clients (_client_tools_stream_relay) and a verbatim degrade path (_client_tools_relay). Moved byte-identically -- NO consolidation, every comment/heuristic/guard preserved. Sibling helpers (_sse_chunk/_sse_done, _format_tool_error, loads_lenient, dispatch_mios_verb, _AUTH_HOSTPORTS/_TOOL_BACKEND/_TOOL_BACKEND_MODEL) are imported directly; every server-side dep (VISION_MODEL/VISION_ENDPOINT/_BACKEND_KEY, _VERB_CATALOG, _verb_to_openai_tool, _resolve_verb_key, _agent_contract, _pick_tool_backend, _select_child_tools, DEFAULT_TOOL_CAP, _tool_call_sig, _get_client) is dependency-INJECTED via configure() (one-way boundary -- this module NEVER imports server). server.py re-imports every moved name under its original alias (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_config.py, ./mios_sse.py, ./mios_toolexec.py, ./mios_jsonsalvage.py, ./mios_dispatch.py, ./mios_cua.py, ./test_mios_vision.py
# AI-functions: _messages_have_image, _vision_backend_failed, _vision_msg_response, _vision_unavailable_response, _resolve_media_url_from_html, _vision_inline_remote_images, _vision_complete, _has_client_tools, _client_tools_mios_surface, _client_tools_is_mios, _client_tools_inject_identity, _client_tools_backend, _client_tools_loop, _client_tools_wrap, _client_tools_sse, _name_is_verb, _client_tools_stream_relay, _client_tools_complete, _client_tools_relay, configure
"""VISION + CLIENT-TOOLS responders (refactor R9).

Extracted VERBATIM from ``server.py`` -- the two image-/tool-bearing fast-path
branches of ``/v1/chat/completions`` that bypass refine/council/polish. The
VISION branch (``_vision_complete`` + the inline-remote-image pre-step + the
honest-error gate) proxies an image turn to the local VLM and never fabricates a
description. The CLIENT-TOOLS hybrid loop (``_client_tools_complete`` and its
cluster) runs an OpenAI client-tools turn where MiOS asserts its identity, merges
its verb surface server-side, executes MiOS verbs via the broker, and rides only
the caller's own tool_calls back. Both clusters moved byte-identically.

Sibling helpers are imported directly; every server-side symbol is injected via
:func:`configure` (one-way boundary -- this module never imports ``server``).
``server.py`` re-imports every moved name under its original alias so the
importable surface is byte-identical.
"""

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


# -- Dependency-injection seam --------------------------------------
# The vision + client-tools responders read server.py's VLM-lane config
# (VISION_MODEL/VISION_ENDPOINT/_BACKEND_KEY), the live verb catalog, and call
# back into the verb-projection / verb-resolve / contract / tool-backend-pick /
# child-tool-select / tool-call-sig / http-client helpers. server.py calls
# configure() with those AFTER every one is defined (one-way boundary: this
# module never imports server). The placeholders below carry safe defaults so a
# standalone ``import mios_vision`` still succeeds; every consumer is
# async/runtime so nothing fires before configure() runs.

# config scalars (server SSOT/env-derived; injected at import-completion)
VISION_MODEL = ""
VISION_ENDPOINT = ""
_BACKEND_KEY = ""
DEFAULT_TOOL_CAP = 24

# mutable refs (injected BY REFERENCE -- the shared object stays live)
_VERB_CATALOG: dict = {}

# server-side helpers (injected)
_get_client = None
_verb_to_openai_tool = None
_resolve_verb_key = None
_agent_contract = None
_pick_tool_backend = None
_select_child_tools = None
_tool_call_sig = None


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


# Honest "vision unavailable" message ("FIX ALL VISION"): when
# the VLM is not provisioned / fails to load, the user must get a CLEAR assistant
# turn -- not the confusing raw "image inputs are not supported / required config
# missing" the leaf relayed. Generic + honest (no fabricated capability claim).
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


# Honest message when a remote image/GIF/page URL couldn't be fetched into a
# viewable image (a Tenor GIF PAGE url made the leaf guess
# from a web search instead of seeing it). Never fabricate a description.
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
    return JSONResponse(content={
        "id": f"chatcmpl-{chat_id}", "object": "chat.completion", "model": model,
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
    """Rewrite remote image_url URLs in `messages` to INLINED base64 data URLs the
    local llama.cpp VLM can actually see (it doesn't fetch URLs + rejects page URLs).
    Per image: fetch the URL; if it's a PAGE (text/html, e.g. a Tenor GIF page),
    resolve to its real media via HTML metadata then fetch that; for an animated
    GIF/WEBP extract a middle frame (Pillow); re-encode to PNG; inline. Mutates
    `messages` in place. Returns False if a REMOTE image could NOT be inlined, so the
    caller returns an honest 'couldn't fetch' turn instead of letting the VLM guess.
    Already-inlined data: URLs (OWUI) and non-image parts are untouched (no regress)."""
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
                    # a web PAGE -> resolve the real media asset (1 hop), then fetch it
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
    # Inline any REMOTE image/GIF/page URL so the local VLM can actually SEE it (it
    # reads only inlined base64; it rejects bare URLs + page links like a Tenor GIF
    # page). On a fetch/resolve failure, return an honest 'couldn't open that image'
    # turn rather than letting the model guess from the URL text.
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
    t = body.get("tools")
    return isinstance(t, list) and len(t) > 0


# Identity + capability preamble injected into a client-tools turn so MiOS AI
# never adopts the caller's persona (Zen's smart-window forwards a "you are
# Mozilla's Smart Window assistant" system prompt) and knows it owns the full
# MiOS verb surface -- not just the 2-3 browser tools the client shipped.
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
    """A returned tool_call is MiOS-executable SERVER-SIDE when it resolves to a real
    MiOS verb -- EVEN IF the client also shipped it. The Hermes desktop app ships the
    WHOLE MiOS MCP surface (launch_windows_app, windows_desktop_type_text, ...) as its
    own tools; relaying those back for it to self-execute via MCP was the failure path
    ('open notepad and type hello' mis-fired -- malformed/parallel calls, nothing ran,
). Running MiOS verbs HERE via the proven broker (dispatch_mios_
    verb) is reliable, ORDER-preserving, and does NOT double-execute (the loop appends
    the RESULT, not the tool_call, so nothing rides back for the client to re-run).
    Only genuinely non-MiOS client tools (browser_*, terminal, IDE ops) -- which the
    server CANNOT run -- ride back to the caller."""
    if not name:
        return False
    try:
        return _resolve_verb_key(name) in _VERB_CATALOG
    except Exception:  # noqa: BLE001
        return False


def _client_tools_inject_identity(messages: list) -> list:
    """Prepend the FULL MiOS root contract (/MiOS.md via _agent_contract) PLUS the
    client-tools addendum to the caller's leading system message (or add one).
    WS-B: the Zen path now gets the SAME root-MD grounding every other MiOS agent
    gets, instead of drifting on a bespoke identity string. Server-side only -- the
    client never sees it, so it can't accumulate across the multi-request loop."""
    _contract = _agent_contract()
    lead = (_contract + "\n\n" + _CLIENT_TOOLS_IDENTITY) if _contract else _CLIENT_TOOLS_IDENTITY
    msgs = [dict(m) for m in messages if isinstance(m, dict)]
    if msgs and msgs[0].get("role") == "system":
        base = str(msgs[0].get("content") or "")
        msgs[0]["content"] = lead + "\n\n" + base
        return msgs
    return [{"role": "system", "content": lead}] + msgs


async def _client_tools_backend(req: dict) -> dict:
    """One non-stream POST to the tool backend, with heavy->light FALLBACK on any
    non-200 + diagnostic logging. The heavy lane (SGLang) can 400 a tool surface it
 rejects (the Hermes REPL got 'No reply' because the loop
    treated a heavy-lane 400 as an empty completion). On a non-200 we LOG the body +
    a request summary (so the cause is finally visible) and retry the always-on light
    lane (a different engine often accepts what the heavy lane rejected). Returns {}
    (never raises) when neither lane yields a 200, so the loop's synthesis / never-
    empty fallback engages instead of the whole turn erroring out."""
    # Clamp the completion budget so input + max_tokens fit the lane context.
    # Hermes sends max_tokens = its context_length (65536 = the WHOLE window), so
    # input(~29.6k) + completion(65.5k) = ~95k > 65536 -> SGLang 400 ("Requested
    # token count exceeds the model's maximum context length",,
    # the REPL 'No reply'). Estimate input tokens (~4 chars/tok over messages +
    # tools) and cap the completion to what's left. Never blocks on the estimate.
    try:
        _ctx = int(os.environ.get("MIOS_AGENT_PIPE_TOOL_CTX", "65536") or 65536)
        # Estimate input tokens via the WS-A5 tokenizer seam (was an inline // 4):
        # count_text over the concatenated message + tool JSON == the prior
        # (len(messages_json) + len(tools_json)) // 4 under the heuristic backend.
        _in_tokens = mios_tokenize.count_text(
            json.dumps(req.get("messages") or [])
            + json.dumps(req.get("tools") or []))
        _cap = max(512, _ctx - _in_tokens - 1024)
        _req_mt = int(req.get("max_tokens") or 0)
        if _req_mt <= 0 or _req_mt > _cap:
            req = dict(req)
            req["max_tokens"] = _cap
    except Exception:  # noqa: BLE001 -- never block the call on the clamp
        pass
    _url, _mdl = await _pick_tool_backend()

    async def _post(url: str, mdl: str):
        rq = dict(req)
        rq["model"] = mdl
        headers = {"content-type": "application/json"}
        _hp = url.split("://")[-1].split("/")[0]
        if _BACKEND_KEY and _hp in _AUTH_HOSTPORTS:
            headers["authorization"] = f"Bearer {_BACKEND_KEY}"
        client = await _get_client()
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
    # Non-200 -> diagnose + fall back to the light lane.
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
    # Cap the MERGED MiOS surface to the intent-relevant subset, leaving EVERY client
    # tool untouched (client tools have no verb embeddings, so relevance-ranking them
    # would wrongly deprioritise e.g. Zen's browser tools). A small (8B) model handed
    # ALL ~60 MiOS verbs -- esp. the redundant launch cluster (open_app/launch_app/
    # launch_windows_app/launch_and_verify_app) -- alongside the client's ~137 tools
    # emitted MALFORMED parallel calls (open_app AND launch_windows_app for one app ->
    # nothing fired,). Relevance-selecting the MiOS verbs keeps the
    # ONE launch verb that fits the ask -> a clean single tool_call.
    _intent = ""
    for _m in reversed(body.get("messages") or []):
        if isinstance(_m, dict) and _m.get("role") == "user":
            _intent = str(_m.get("content") or "")
            break
    _mios_sel = await _select_child_tools(
        _client_tools_mios_surface(), _intent, DEFAULT_TOOL_CAP)
    tools = list(body.get("tools") or []) + _mios_sel
    # parallel_tool_calls=False by default: the loop executes MiOS verbs SEQUENTIALLY
    # server-side anyway, and an 8B model handed a big merged tool surface (the client's
    # own tools + the MiOS verbs) tends to emit MALFORMED parallel calls -- e.g. open_app
    # AND launch_windows_app for one app, serialized with missing names so NEITHER fires
    # ("nothing happened",). Forcing one call per turn keeps the
    # tool_call well-formed. The client can still override via its own parallel_tool_calls.
    base_req: dict = {"model": _TOOL_BACKEND_MODEL, "tools": tools, "stream": False,
                      "parallel_tool_calls": False}
    # WS-E #3/#4: forward the caller's tool_choice + parallel_tool_calls so a client
    # that forces a function (or forbids parallel) isn't silently overridden to auto.
    for _k in ("temperature", "top_p", "max_tokens", "tool_choice", "parallel_tool_calls"):
        if _k in body:
            base_req[_k] = body[_k]
    # Thinking OFF (the Hermes REPL "empty response" bug):
    # with thinking ON a reasoning model (Qwen3-8B on the heavy lane) spends the
    # CALLER's whole max_tokens budget inside the <think> block and hits the length
    # limit BEFORE emitting any content OR tool_call -> the client gets "empty
    # response after retries / No reply". Proven live on the heavy lane: tools-less
    # max_tokens=250 think-ON -> content_len=0 reasoning_len=1133 finish=length, vs
    # think-OFF -> content_len=1114. The Hermes client sets a tight budget, so
    # thinking MUST be off here. Tool-calling works fine without thinking; the
    # final-synthesis fallback below is also thinking-off.
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
            # No tool_calls AND empty content (a small 8B handed the big merged client+
            # MiOS tool surface can return nothing, esp. with thinking on). Do NOT hand
            # back an empty reply (the Hermes desktop "no reply" bug) -- break to the final
            # tools-less synthesis below, which forces a content answer.
            break
        if any(not _client_tools_is_mios(
                (tc.get("function") or {}).get("name", ""), client_names)
                for tc in tcs):
            # A client tool is requested -> hand the whole message back so the
            # caller fulfills it (and re-enters this loop with the result).
            return msg
        # All MiOS verbs -> execute server-side, append results, continue.
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
    # Robustness (Hermes desktop "empty response"): reaching here
    # means the loop exhausted max_iters on MiOS-verb tool_calls WITHOUT the model ever
    # emitting plain content or a CLIENT tool_call (a small 8B can spin on the merged
    # surface). `last` is then a MiOS-tool-call message with NO content -> the caller (the
    # desktop agent) gets an EMPTY reply. Make ONE final tools-LESS call so the model must
    # synthesise a content answer from the tool results already in `messages`. Degrade-open.
    if not str((last or {}).get("content") or "").strip():
        try:
            _fr = dict(base_req)
            _fr.pop("tools", None)
            _fr.pop("tool_choice", None)
            # Thinking OFF for the synthesis: the whole token budget goes to the
            # CONTENT answer (with thinking on, an 8B spends it reasoning and emits a
            # truncated/terse reply).
            _fr["chat_template_kwargs"] = {"enable_thinking": False}
            _fr["messages"] = messages
            _fresp = await _client_tools_backend(_fr)
            _fmsg = ((_fresp.get("choices") or [{}])[0] or {}).get("message") or {}
            if str(_fmsg.get("content") or "").strip():
                return _fmsg
            # Last resort: synthesize over a MINIMAL prompt -- drop the heavy SOUL +
            # accumulated tool-result context that may have choked the model -- so a
            # content answer is essentially guaranteed.
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
    # NEVER hand the client an empty reply (Hermes shows "No reply" + retries 3x).
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
    # Relay the backend's thinking so a client that renders it (Hermes desktop)
    # shows the thinking stream; emit both field conventions. Zen ignores both.
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


def _name_is_verb(name) -> bool:
    """True if a tool name resolves to a real MiOS verb (the client already carries
    the MiOS surface -- e.g. Hermes via its mios MCP client)."""
    if not name:
        return False
    try:
        return _resolve_verb_key(str(name)) in _VERB_CATALOG
    except Exception:  # noqa: BLE001
        return False


async def _client_tools_stream_relay(body: dict, chat_id: str, model: str) -> Any:
    """STREAM the backend response verbatim for a full-agent client that carries its
    OWN MiOS tools (Hermes desktop app): inject MiOS identity, enable thinking, forward
    the client's tools, and relay the SSE byte-for-byte so content / reasoning /
    tool_calls stream LIVE -- no compute-then-burst dead wait. The client executes its
    own tool_calls in its own loop (it has the tools), so no server-side merge is
    needed; that merge is only for tool-less clients (Zen) via the hybrid loop."""
    _url, _mdl = await _pick_tool_backend()
    tbody = dict(body)
    tbody["model"] = _mdl
    tbody["messages"] = _client_tools_inject_identity(list(body.get("messages") or []))
    tbody["chat_template_kwargs"] = {"enable_thinking": True}
    tbody["stream"] = True
    # Force ONE well-formed tool call per turn (the client runs its own loop, executing
    # each step then re-calling). A small model handed the full client+MiOS surface on a
    # multi-step ask ("open notepad AND type hello") emits MALFORMED parallel calls (the
    # Hermes-desktop "LIAR" failure: two open_app calls, no type, nothing fires). The
    # client may override..
    tbody.setdefault("parallel_tool_calls", False)
    for _k in ("mios_flags", "_allow_write", "num_ctx"):
        tbody.pop(_k, None)
    headers = {"content-type": "application/json"}
    _hp = _url.split("://")[-1].split("/")[0]
    if _BACKEND_KEY and _hp in _AUTH_HOSTPORTS:
        headers["authorization"] = f"Bearer {_BACKEND_KEY}"
    url = f"{_url}/chat/completions"
    client = await _get_client()

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
    """OpenAI client-tool turn (Zen smart-window et al.) as a HYBRID loop: MiOS
    asserts its own identity, the MiOS verb surface is merged alongside the
    caller's browser tools, MiOS verbs execute server-side (so 'open notepad'
    actually launches), and only the caller's own tool_calls ride back to it.
    Falls back to a verbatim relay if the loop errors so browsing never regresses.
    NEVER runs refine/council/polish. Twin of _vision_complete."""
    client_names: set = set()
    for _t in (body.get("tools") or []):
        try:
            client_names.add((_t.get("function") or {}).get("name") or _t.get("name"))
        except Exception:  # noqa: BLE001
            continue
    out_model = model or _TOOL_BACKEND_MODEL
    # ROUTING (- the Hermes desktop "open notepad and type"
    # failures): ALWAYS use the HYBRID loop for a client-tools turn; NEVER the verbatim
    # relay. The desktop app's actual tool surface is the hermes-cli builtins
    # (browser_*, terminal, text_to_speech, ...) and does NOT contain the MiOS verbs --
    # its mios MCP tools fail to register, proven by the live error "Tool 'open_url'
    # does not exist. Available tools: browser_back ... write_file" (no open_app /
    # pc_type / launch_* anywhere). The model is told by its system prompt to call MiOS
    # launch tools, so it emits open_url / open_app / windows_desktop_type_text -- verbs
    # ABSENT from its surface -> "does not exist" -> nothing runs. The verbatim relay
    # only forwarded that MiOS-less surface, so it could NEVER work. The hybrid loop
    # MERGES the MiOS verb surface server-side (_client_tools_mios_surface) so open_app/
    # pc_type are actually present and EXECUTE via the broker (notepad opens + types),
    # while genuine client-only tools (browser_*) still ride back to the caller. Tradeoff
    # vs the old relay: the final answer bursts instead of token-streaming -- acceptable
    # for a turn that now actually WORKS.
    try:
        final_msg = await _client_tools_loop(body, client_names, chat_id)
        # WS-E #2: a strict client matches its follow-up role:tool message by
        # tool_call_id; if the backend omitted an id, synthesize a stable one so the
        # client's next turn validates instead of 400-ing on id=null.
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
    tbody = dict(body)
    tbody["model"] = _TOOL_BACKEND_MODEL
    for _k in ("mios_flags", "_allow_write", "num_ctx"):
        tbody.pop(_k, None)
    headers = {"content-type": "application/json"}
    _hp = _TOOL_BACKEND.split("://")[-1].split("/")[0]
    if _BACKEND_KEY and _hp in _AUTH_HOSTPORTS:
        headers["authorization"] = f"Bearer {_BACKEND_KEY}"
    url = f"{_TOOL_BACKEND}/chat/completions"
    client = await _get_client()
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

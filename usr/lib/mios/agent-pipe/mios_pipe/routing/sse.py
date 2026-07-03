# AI-hint: OpenAI streaming SSE chunk + status-emit primitives extracted from server.py (refactor WS R2 leaf wave). Encodes chat-completion deltas in the OpenAI streaming protocol so any gateway (OWUI/Discord/Slack) consumes them with its stock client: _sse_chunk (delta builder, dual reasoning_content+reasoning fields), _sse_reasoning (thinking stream), _sse_status/_sse_status_phase (content-empty mios_status pills + persistent reasoning-log lines, humanistic emoji labels from _load_status_labels/_HUMAN_LABELS), _enrich_step_emits/_node_context/_node_status (per-step + per-AI-node live emitters), _stream_answer (char-paced final answer), _iter_answer_chunks (word-boundary answer chunker for the native-loop stream), _sse_done, and _tail_latest_status (hermes-tail checkpoint -> live status). STATUS_AS_REASONING moves here (its sole consumer is _sse_status). Pure stdlib + json + re; no server.py state, no DB -- server re-imports every name verbatim (surface-parity zero-diff).
# AI-related: ./server.py, ./mios_aci.py, ./mios_native_loop.py, ./test_mios_sse.py
# AI-functions: _sse_chunk, _sse_reasoning, _load_status_labels, _sse_status_phase, _sse_status, _enrich_step_emits, _node_context, _node_status, _stream_answer, _iter_answer_chunks, _sse_done, _tail_latest_status
"""OpenAI-streaming SSE chunk + status-emit primitives (extracted from server.py).

Every builder returns ``bytes`` ready to write to the SSE response stream, or (for
``_stream_answer``) async-yields them. Moved verbatim from ``server.py``; the
module is pure (stdlib + ``json`` only) and ``server.py`` re-imports every name so
its public surface is unchanged.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from typing import Any, Optional

# persist each phase emit ALSO as a reasoning line so the OWUI
# Thinking dropdown keeps the live activity log (status pills are transient). Sole
# consumer is _sse_status below; moved here with the emit cluster.
STATUS_AS_REASONING = os.environ.get(
    "MIOS_STATUS_AS_REASONING", "true").lower() not in {"false", "0", "no"}

_DEBUG_ENABLE = False


# ── SSE chunk builders ─────────────────────────────────────────────
# Encode chat completion deltas in the OpenAI streaming protocol so
# any gateway (OWUI, Hermes Discord, Slack/Telegram, ...) consumes
# the response with its existing OpenAI client. The dispatch fast-
# path emits a single delta containing the structured tool_calls
# envelope as content (rendered as a <details type="tool_calls">
# block markdown can collapse natively).

def _sse_chunk(content: Optional[str], *, chat_id: str, model: str,
               role: Optional[str] = None,
               finish_reason: Optional[str] = None,
               mios_status: Optional[dict] = None,
               reasoning: Optional[str] = None) -> bytes:
    """Build an OpenAI-streaming SSE chunk. `reasoning` populates the
    standard `delta.reasoning_content` field (OpenAI/OpenRouter/DeepSeek
    convention) -- OWUI renders it as a native Thinking dropdown and
    strict clients (Firefox Smart Window) ignore it, showing only the
    clean `content` answer. Optional `mios_status` carries pipe-internal
    phase emits (👂 prompt, 🧭 route, 🛠️ tool, ✅) that translator gateways
    lift into their native status surfaces; stock clients ignore it."""
    delta: dict[str, Any] = {}
    if role:
        delta["role"] = role
    if reasoning is not None:
        # Emit BOTH reasoning field conventions so EVERY client renders the
        # thinking stream: `reasoning_content` (DeepSeek/OWUI) AND `reasoning`
        # (OpenRouter / newer OpenAI / the Hermes desktop app + Cursor). A client
        # parses whichever it knows and ignores the other; strict clients (Zen
        # Smart Window) ignore both and show only `content`.
        # Hermes thinking wasn't streaming because it reads `delta.reasoning`, not
        # `reasoning_content`.
        delta["reasoning_content"] = reasoning
        delta["reasoning"] = reasoning
    if content is not None:
        delta["content"] = content
    chunk = {
        "id": chat_id,
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "delta": delta,
            "finish_reason": finish_reason,
        }],
    }
    if mios_status:
        chunk["mios_status"] = mios_status
    return ("data: " + json.dumps(chunk) + "\n\n").encode("utf-8")


def _sse_reasoning(text: str, *, chat_id: str, model: str,
                   reasoning_ok: Optional[bool] = None) -> bytes:
    """Stream a reasoning/trace delta on the correct channel for the surface.

    ``reasoning_ok`` carries the consuming surface's capability (set per-request
    from the ``x-mios-reasoning-ok`` hint the OWUI pipe advertises; ``None`` when
    unknown):

    * ``True``  -- reasoning-aware surface (OWUI / Hermes desktop): pin the trace
      to ``delta.reasoning_content`` REGARDLESS of ``[observability].debug`` so it
      renders live in the native Thinking pane and never pollutes the answer
      ``content`` (final answer stays the only thing in ``content`` -- KV-safe,
      OWUI #21815). Full visibility, replay-safe.
    * ``False`` -- a surface that DECLARED itself content-only: fold the trace
      inline as ``content`` so strict clients (which ignore ``reasoning_content``)
      still render it. Visibility preserved; MiOS owns the replay-strip.
    * ``None``  -- unknown surface: legacy routing, ``[observability].debug``
      decides (byte-identical to before the hint existed -- degrade-open).

    The mandate is full visibility on EVERY surface; this only routes WHICH
    channel carries the trace, never suppresses it."""
    if reasoning_ok is True:
        return _sse_chunk(None, chat_id=chat_id, model=model, reasoning=text)
    if reasoning_ok is False:
        return _sse_chunk(text, chat_id=chat_id, model=model)
    if _DEBUG_ENABLE:
        return _sse_chunk(text, chat_id=chat_id, model=model)
    return _sse_chunk(None, chat_id=chat_id, model=model, reasoning=text)


# Phase keys -> humanistic casual labels for the SSE status strip.
# MiOS is for non-technical users; the strip should read like the
# system is THINKING and DOING, not like a debugger output. Model
# names, timings, arg JSONs, intent labels stay in the
# event payloads for debug -- they NEVER reach the visible strip.
#
# Add a phase key here when wiring a new emit site instead of
# inlining label strings -- keeps the operator-visible voice
# consistent across every dispatch path.
def _load_status_labels() -> dict:
    """Phase -> (emoji, label) for the SSE status strip. Personable
    defaults here; each phase is OVERRIDABLE from mios.toml
    [owui.status_phases.<phase>] = { emoji = "..", label = ".." } so the
    operator tunes MiOS-Agent's voice without touching code (SSOT; no
 hardcoded UI strings locked in the hot path).
    'better emitters / more detailed and personable'."""
    # EMOJI ONLY -- no hardcoded English narrative, no TOML label map.
    # "nothing hardcoded -- pure streamed +
    # generative". The chip is the emoji plus any GENERATIVE `detail` the
    # emit site passes (the actual verb / refined intent / plan); the rich
    # agent-path activity comes from the live hermes-tail stream in the
    # OWUI pipe. Emojis are locale-neutral glyphs, not English strings.
    return {
        "prompt":         ("👂", ""),
        "refine":         ("✨", ""),
        "route":          ("🧭", ""),
        "plan":           ("🗺️", ""),
        "agent_target":   ("🤖", ""),
        "tool":           ("🛠️", ""),
        "tool_done":      ("✅", ""),
        "tool_done_warn": ("😅", ""),
        "chat":           ("💬", ""),
        "chat_done":      ("✅", ""),
        "dag_done":       ("✅", ""),
        "dag_done_warn":  ("😅", ""),
        "reflect":        ("🤔", ""),
        "subagent_done":  ("✅", ""),
    }


_HUMAN_LABELS = _load_status_labels()


def _sse_status_phase(*, chat_id: str, model: str, phase: str,
                      done: bool = False,
                      detail: Optional[str] = None) -> bytes:
    """Humanistic-label variant of _sse_status. Looks up the phase
    in _HUMAN_LABELS, emits the casual label + emoji. `detail` is
    optional and should ALSO be human-facing prose (e.g. "for 22
    seconds", "almost there") -- NOT a model id / args JSON /
    intent token. If you find yourself wanting to thread technical
    info through here, log it to the event table instead."""
    emoji, label = _HUMAN_LABELS.get(phase, ("·", phase))
    return _sse_status(chat_id=chat_id, model=model, emoji=emoji,
                       label=label, done=done, detail=detail)


def _sse_status(*, chat_id: str, model: str, emoji: str, label: str,
                done: bool = False, detail: Optional[str] = None) -> bytes:
    """Emit a content-empty SSE chunk whose only purpose is the
    `mios_status` field. Standard OpenAI clients see a no-op delta
    + ignore the extra field. Translator gateways pull the phase
    info from `mios_status` and surface it natively (OWUI's
    event_emitter status, Hermes Discord's reactions, etc.).

    Prefer _sse_status_phase() for new emit sites -- it picks the
    canonical humanistic label from _HUMAN_LABELS. This raw form
    stays available for one-off cases where the phase mapping
    doesn't fit."""
    payload = {"emoji": emoji, "label": label, "done": done}
    _desc = f"{emoji} {label}".strip()
    if detail:
        d = str(detail).strip()
        if d:
            payload["detail"] = d[:80]
            # Append to label for clients that only render `label`. " · "
            # separator (was a bare double-space that read as a layout glitch).
            payload["label"] = f"{label} · {d[:80]}" if label else d[:80]
            _desc = f"{_desc} · {d[:80]}".strip(" ·")
    # ALSO stream the emit as a PERSISTENT reasoning line (
    # OWUI status pills are TRANSIENT -- one line, replaced each event, gone on
    # done -- so the operator never sees the activity LOG). reasoning_content
    # persists in OWUI's <details> Thinking block (and strict OpenAI clients
    # ignore it), so the live phase log stays visible WITH context. Skip the
    # terminal done marker -- it lands after the answer starts, where the OWUI
    # bridge drops late reasoning.
    # ONLY persist an emit that carries REAL content -- a label or a detail.
    # A BARE phase marker (👂/✨/🧭/🤖 = prompt/refine/route/agent_target, which
    # have empty labels + no detail) is noise in the dropdown (operator
    # "the same hardcoded bunch of generic emits that do nothing").
    # Such contentless markers still emit as a transient mios_status pill (the
    # progress signal) -- they just no longer clutter the persistent log. The
    # meaningful emits (🔎 search · query, 🕷️ crawl · url, 🛰️ <node>, ✅) all
    # carry a label/detail and are unaffected. No hardcoded emoji list -- the
    # test is purely "does this emit say anything".
    _has_content = bool((label and str(label).strip())
                        or (detail and str(detail).strip()))
    _content = None
    _reason = None
    if STATUS_AS_REASONING and _has_content and not done:
        if _DEBUG_ENABLE:
            _content = (_desc + "\n")
        else:
            _reason = (_desc + "\n")
    return _sse_chunk(
        _content, chat_id=chat_id, model=model,
        mios_status=payload, reasoning=_reason,
    )


def _enrich_step_emits(refined: Optional[dict], *, chat_id: str, model: str):
    """Yield ONE _sse_status per recorded enrich STEP ("need
    emitters for every step end-to-end" -- not one whole-loop summary). Covers
    the web steps (search / each page read / each deep-crawl / each drill pass,
    recorded by _web_research_enrich) and the READ-only tool runs (recorded by
    _read_tool_enrich). Each emit also persists in the reasoning log via
    _sse_status. Yields nothing when no steps ran."""
    if not isinstance(refined, dict):
        return
    steps = ((refined.get("_web_steps") or [])
             + (refined.get("_readtool_steps") or [])
             + (refined.get("_verity_steps") or []))
    for s in steps:
        if not isinstance(s, dict):
            continue
        yield _sse_status(
            chat_id=chat_id, model=model,
            emoji=str(s.get("emoji", "·")), label=str(s.get("label", "")),
            detail=(str(s.get("detail", "")) or None))


def _node_context(node: dict) -> str:
    """SHORT, operator-facing description of what a DAG node is DOING -- the
 active step's CONTEXT ("emits should show actual steps
    relevant to the current active step's context"). Derived from the node's
    OWN data -- an agent node's sub-task, or a verb node's key arg -- NOT the
    internal model/endpoint (which read as a leak). No LLM call, no hardcoded
    topic text: it's the step's literal intent."""
    if not isinstance(node, dict):
        return ""
    if node.get("agent"):
        # Prefer the CLEAN facet `title` -- `prompt` gets a LIVE-GROUNDING prefix
        # prepended at dispatch, which would otherwise leak into the emit (operator
        # "DAG emits leak the grounding text instead of clean labels").
        return str(node.get("title") or node.get("prompt")
                   or node.get("task") or "").strip()[:64]
    args = node.get("args") or {}
    if isinstance(args, dict):
        for _k in ("query", "id", "name", "path", "url", "title", "unit",
                   "text", "content", "script"):
            _v = args.get(_k)
            if _v:
                return f"{_k}={str(_v)[:48]}"
        for _v in args.values():
            if _v:
                return str(_v)[:48]
    return ""


def _node_status(*, chat_id: str, model: str, name: str, cfg: dict,
                 state: str, context: str = "") -> bytes:
    """Per-endpoint live emitter ("endpoint emitters for
    each ai endpoint/node"). One status event naming an AI node as the chain
 ENGAGES it / it RESPONDS / goes silent. `context` is
    a short description of the node's CURRENT STEP -- its sub-task or the verb
    arg -- so the emit reflects the active step's context, not just a glyph.
    The lane/model/endpoint internals stay OUT (they read as a leak); context
    is the WHAT (operator-facing), not the HOW (plumbing).

 the LABEL must be GENERATIVE -- indicative of the
    FUNCTION being performed, NOT the internal agent/function name (research-
    dgpu-1, hermes, opencode, ...). So the label = the node's actual sub-task
    (`context`), falling back to its semantic ROLE as a plain word (research /
    reasoning / coding -- a capability descriptor, not a node name) and never
    the registry key. The internal name is dropped entirely from the emit."""
    # Casual, end-user-obvious glyphs ("more casual + useful
    # to end-users"): an AI is working on it (🤖) -> done (✅) -> went quiet (💤).
    emoji = {"engage": "🤖", "ok": "✅", "down": "💤"}.get(state, "🤖")
    _ctx = str(context or "").strip()
    _role = str((cfg or {}).get("role") or "").strip()
    _label = _ctx or _role or "working"
    # context already IS the label -> don't repeat it as detail.
    _detail = "" if _label == _ctx else _ctx
    return _sse_status(chat_id=chat_id, model=model, emoji=emoji,
                       label=_label[:80], detail=_detail[:80])


async def _stream_answer(text: str, *, chat_id: str, model: str):
    """Yield the final answer in small character-exact chunks so OWUI renders
    it progressively (live 'typing') instead of one end-of-turn burst -- the
    "thinking prints then switches to the refined copy" jolt (operator
). Pacing is bounded so long answers stream in ~1.2s, not slower.
    Char-slicing preserves the text byte-for-byte (markdown/code intact)."""
    if not text:
        return
    size = int(os.environ.get("MIOS_ANSWER_CHUNK_CHARS", "48"))
    chunks = [text[i:i + size] for i in range(0, len(text), max(1, size))]
    delay = min(0.03, 1.2 / max(1, len(chunks)))
    for ch in chunks:
        yield _sse_chunk(ch, chat_id=chat_id, model=model)
        if delay:
            await asyncio.sleep(delay)


def _sse_done() -> bytes:
    return b"data: [DONE]\n\n"


# Hermes-tail -> live checkpoint status. During the buffered sub-agent
# call the agent-pipe would otherwise send bare ': keepalive' COMMENT
# lines (no data) while it waits -- OWUI then renders nothing until the
# very end ("emitters haven't worked once; thinking
# + emits only mass-print at the end"). Emitting a REAL mios_status data
# chunk on each checkpoint, sourced from the AI's actual latest tool
# step, forces the emit to flush + stream live instead of dumping at the
# end -- the "checkpoint/status interrupt" the operator asked for.
_TAIL_KIND_EMOJI = {
    "max_retries":    "❌",
    "invalid_tool":   "⚠️",
    "retry":          "↻",
    "delegate_spawn": "🚀",
    "synthesis":      "🔀",
    "subagent_done":  "✅",
    "tool_call":      "🛠️",
}
_HERMES_TAIL_PATH = os.environ.get(
    "MIOS_HERMES_TAIL_PATH", "/var/lib/mios/hermes-tail/latest.json")


def _tail_latest_status(seen_ts: float, *, chat_id: str,
                        model: str) -> tuple[Optional[bytes], float]:
    """If the hermes-tail holds an event newer than seen_ts, return its
    mios_status SSE chunk (emoji + generative detail) and the advanced
    ts; otherwise (None, seen_ts). Best-effort -- any read/parse error
    just yields no chunk."""
    try:
        with open(_HERMES_TAIL_PATH) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError, ValueError):
        return None, seen_ts
    newest = None
    new_ts = seen_ts
    for ev in data.get("events", []):
        ts = ev.get("ts", 0)
        if ts > new_ts:
            new_ts = ts
            newest = ev
    if newest is None:
        return None, seen_ts
    emoji = _TAIL_KIND_EMOJI.get(str(newest.get("kind", "")), "·")
    detail = str(newest.get("detail", "")).strip()
    return (_sse_status(chat_id=chat_id, model=model, emoji=emoji,
                        label="", done=False, detail=detail), new_ts)


def _iter_answer_chunks(text: str, size: int):
    """Split `text` into ~size-char pieces at WORD boundaries so the final answer
 TYPES OUT smoothly in the front-ends (token-by-token).
    Whitespace is preserved (split keeps the separators). size<=0 -> one chunk."""
    if size <= 0 or len(text) <= size:
        yield text
        return
    buf = ""
    for tok in re.split(r"(\s+)", text):   # words + their trailing whitespace
        if buf and len(buf) + len(tok) > size:
            yield buf
            buf = ""
        buf += tok
    if buf:
        yield buf


def configure(*, debug_enable: bool = True, **kwargs) -> None:
    # Full-visibility posture: server.py resolves [observability].debug (default
    # on) and passes it here; when on, reasoning/thinking/tool-io/status stream
    # as visible content to every chat surface. Set debug=false in mios.toml for
    # answer-only replies (reasoning then rides delta.reasoning_content instead).
    global _DEBUG_ENABLE
    _DEBUG_ENABLE = bool(debug_enable)

# AI-hint: Agent scratchpad blackboard extracted from server.py.
# AI-related: usr/lib/mios/agent-pipe/server.py, usr/lib/mios/agent-pipe/mios_pipe/context/scratchpad.py
"""Agent scratchpad blackboard module."""

from __future__ import annotations

import collections
import time
from typing import Optional

_SCRATCHPADS: collections.OrderedDict[str, collections.deque] = collections.OrderedDict()
_REHYDRATED_CHATS: set[str] = set()

SCRATCHPAD_ENABLE = True
SCRATCHPAD_PERSIST = True
SCRATCHPAD_MAX = 20
SCRATCHPAD_MAX_CHATS = 100
SCRATCHPAD_SUMMARY_CHARS = 300
SCRATCHPAD_TTL_S = 3600
SCRATCHPAD_INJECT = 5

_conv_key_var = None
_mios_pg = None
_db_write = None


def configure(*, scratchpad_enable=None, scratchpad_persist=None,
              scratchpad_max=None, scratchpad_max_chats=None,
              scratchpad_summary_chars=None, scratchpad_ttl_s=None,
              scratchpad_inject=None, conv_key_var=None,
              mios_pg=None, db_write=None) -> None:
    """Inject config scalars, contextvars, and DB writer helpers."""
    global SCRATCHPAD_ENABLE, SCRATCHPAD_PERSIST, SCRATCHPAD_MAX
    global SCRATCHPAD_MAX_CHATS, SCRATCHPAD_SUMMARY_CHARS, SCRATCHPAD_TTL_S
    global SCRATCHPAD_INJECT, _conv_key_var, _mios_pg, _db_write

    if scratchpad_enable is not None:
        SCRATCHPAD_ENABLE = scratchpad_enable
    if scratchpad_persist is not None:
        SCRATCHPAD_PERSIST = scratchpad_persist
    if scratchpad_max is not None:
        SCRATCHPAD_MAX = scratchpad_max
    if scratchpad_max_chats is not None:
        SCRATCHPAD_MAX_CHATS = scratchpad_max_chats
    if scratchpad_summary_chars is not None:
        SCRATCHPAD_SUMMARY_CHARS = scratchpad_summary_chars
    if scratchpad_ttl_s is not None:
        SCRATCHPAD_TTL_S = scratchpad_ttl_s
    if scratchpad_inject is not None:
        SCRATCHPAD_INJECT = scratchpad_inject
    if conv_key_var is not None:
        _conv_key_var = conv_key_var
    if mios_pg is not None:
        _mios_pg = mios_pg
    if db_write is not None:
        _db_write = db_write


def _scratchpad_key(body: dict, fallback: str = "default") -> str:
    """Per-chat scratchpad key: the OpenAI-standard metadata.chat_id."""
    meta = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}
    return str(meta.get("chat_id") or meta.get("session_id")
               or body.get("chat_id") or fallback)


def _scratchpad_for(key: str) -> collections.deque:
    dq = _SCRATCHPADS.get(key)
    if dq is None:
        dq = collections.deque(maxlen=max(1, SCRATCHPAD_MAX))
        _SCRATCHPADS[key] = dq
        while len(_SCRATCHPADS) > max(1, SCRATCHPAD_MAX_CHATS):
            _SCRATCHPADS.popitem(last=False)
    else:
        _SCRATCHPADS.move_to_end(key)
    return dq


async def _scratchpad_rehydrate(key: str) -> None:
    """On the FIRST turn of a chat after an agent-pipe restart, repopulate
    the in-memory scratchpad from the durable pg `scratch` table."""
    if not (SCRATCHPAD_ENABLE and SCRATCHPAD_PERSIST and key):
        return
    if key in _REHYDRATED_CHATS:
        return
    _REHYDRATED_CHATS.add(key)
    if _SCRATCHPADS.get(key):
        return
    if not _mios_pg:
        return
    try:
        rows = await _mios_pg.execute(
            "SELECT agent, lane, phase, note, extract(epoch from ts) AS ts "
            "FROM scratch WHERE chat_id = %(cid)s AND note IS NOT NULL "
            "ORDER BY ts DESC LIMIT %(lim)s",
            {"cid": key, "lim": max(1, SCRATCHPAD_MAX)}, fetch=True)
    except Exception:
        return
    if not rows:
        return
    dq = _scratchpad_for(key)
    for r in reversed(rows):
        try:
            dq.append({
                "ts": float(r.get("ts") or time.time()),
                "agent": str(r.get("agent") or "?"),
                "lane": str(r.get("lane") or ""),
                "phase": str(r.get("phase") or ""),
                "note": str(r.get("note") or ""),
            })
        except Exception:
            continue


def _scratchpad_note(agent: str, text: str, *, lane: str = "",
                     phase: str = "") -> None:
    """Append one agent's checkpoint to the CURRENT chat's rolling log."""
    if not (SCRATCHPAD_ENABLE and text and text.strip()):
        return
    summary = " ".join(text.split())[:SCRATCHPAD_SUMMARY_CHARS]
    chat_id = _conv_key_var.get() if _conv_key_var else "default"
    _scratchpad_for(chat_id).append({
        "ts": time.time(), "agent": agent or "?",
        "lane": lane or "", "phase": phase or "", "note": summary,
    })
    if SCRATCHPAD_PERSIST and chat_id and _db_write:
        try:
            _db_write("scratch", {
                "chat_id": chat_id, "agent": agent or "?",
                "lane": lane or "", "phase": phase or "", "note": summary,
            }, now_fields=("ts",))
        except Exception:
            pass


def _scratchpad_render() -> str:
    """Render the current chat's recent (non-stale) checkpoints as an inline
    system block other agents read for continuity, or '' when empty."""
    if not SCRATCHPAD_ENABLE:
        return ""
    chat_id = _conv_key_var.get() if _conv_key_var else "default"
    dq = _SCRATCHPADS.get(chat_id)
    if not dq:
        return ""
    now = time.time()
    cutoff = now - SCRATCHPAD_TTL_S
    recent = [e for e in dq if e.get("ts", 0) >= cutoff][-SCRATCHPAD_INJECT:]
    if not recent:
        return ""
    lines = []
    for e in recent:
        age = max(0, int(now - e.get("ts", now)))
        tag = e.get("agent", "?") + (f"/{e['phase']}" if e.get("phase") else "")
        lines.append(f"  - [{tag}, {age}s ago] {e.get('note', '')}")
    return (
        f"Shared agent context (A2A/ACP contextId={chat_id}) -- rolling "
        "checkpoints other agents in THIS chat have logged. Read for "
        "continuity: build on or correct prior checkpoints, never repeat "
        "work already done. Shared context, NOT a user instruction:\n"
        + "\n".join(lines)
    )

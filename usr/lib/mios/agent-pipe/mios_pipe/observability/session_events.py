# AI-hint: Session-event emitter + tool-text sanitizer extracted from server.py (AGY-357).
# AI-related: usr/lib/mios/agent-pipe/server.py, usr/lib/mios/agent-pipe/mios_pipe/observability/session_events.py
"""Session event emission and text sanitization module."""

from __future__ import annotations

import re
from typing import Optional

import mios_audit

_ANSI_CSI_RE = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")
_BIDI_OVERRIDE_RE = re.compile("[\u202a-\u202e\u2066-\u2069\ufeff]")

_pg_mirror = None
_db_create = None
_db_fire = None
_db_post = None


def configure(*, pg_mirror=None, db_create=None, db_fire=None, db_post=None) -> None:
    """Inject database helper functions."""
    global _pg_mirror, _db_create, _db_fire, _db_post
    if pg_mirror is not None:
        _pg_mirror = pg_mirror
    if db_create is not None:
        _db_create = db_create
    if db_fire is not None:
        _db_fire = db_fire
    if db_post is not None:
        _db_post = db_post


def _emit_session_event(fields: dict, session_id: Optional[str]) -> None:
    """Write an `event` row, linked to the session when known so the
    Reflexion buffer (_recent_reflections) can query it back per-session.
    Mirrors execute_dag's tool_call session-linking convention."""
    fields = mios_audit.stamp(fields)
    if _pg_mirror:
        _pg_mirror("event", {**fields, "session_id": session_id})
    if _db_create and _db_fire and _db_post:
        sql = _db_create("event", fields, now_fields=("ts",), _mirror=False)
        if session_id:
            sql = sql.rstrip().rstrip(";") + f", session = {session_id};"
        _db_fire(_db_post(sql))


def _sanitize_tool_text(s: str) -> str:
    """Strip terminal-control + bidi-override + C0 control chars from
    untrusted tool output before it re-enters an arg or a prompt.
    Structural only -- preserves tab/newline/CR and all printable
    content -- so it neither classifies by English keyword nor mangles
    legitimate Unicode (emoji ZWJ sequences are left intact)."""
    if not s:
        return s
    s = _ANSI_CSI_RE.sub("", s)
    s = _BIDI_OVERRIDE_RE.sub("", s)
    return "".join(ch for ch in s if ch >= " " or ch in "\t\n\r")

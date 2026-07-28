# AI-hint: Database writer layer extracted from server.py.
# AI-related: usr/lib/mios/agent-pipe/server.py, usr/lib/mios/agent-pipe/mios_pipe/dbwrite.py
"""Database writer layer module."""

from __future__ import annotations

import asyncio
import json
from typing import Optional

import mios_audit
import mios_pg

_PG_ENABLED: bool = True
_PG_PRIMARY: bool = False

_current_trace_id = None
_span_id_var = None
_passport_sign = None
_db_post = None


def configure(*, pg_enabled=None, pg_primary=None, current_trace_id=None,
              span_id_var=None, passport_sign=None, db_post=None) -> None:
    """Inject configuration and callbacks."""
    global _PG_ENABLED, _PG_PRIMARY, _current_trace_id
    global _span_id_var, _passport_sign, _db_post

    if pg_enabled is not None:
        _PG_ENABLED = pg_enabled
    if pg_primary is not None:
        _PG_PRIMARY = pg_primary
    if current_trace_id is not None:
        _current_trace_id = current_trace_id
    if span_id_var is not None:
        _span_id_var = span_id_var
    if passport_sign is not None:
        _passport_sign = passport_sign
    if db_post is not None:
        _db_post = db_post


def _db_fire(coro) -> None:
    """Schedule a DB coroutine fire-and-forget."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro)
    except RuntimeError:
        if asyncio.iscoroutine(coro):
            coro.close()


def _pg_mirror(table: str, fields: dict, *, rls_owner: Optional[str] = None) -> None:
    """Fire-and-forget mirror of an agent-plane write to Postgres+pgvector (WS-9c dual-write)."""
    if not _PG_ENABLED:
        return
    try:
        row = {k: v for k, v in fields.items() if v is not None}
        if row:
            _db_fire(mios_pg.insert(table, row, rls_owner=rls_owner))
    except Exception:
        pass


def _db_create(table: str, fields: dict, *,
               now_fields: tuple = (),
               extra: str = "",
               passport_sign: bool = True,
               _mirror: bool = True) -> str:
    """Build `CREATE <table> SET ...` with time::now() for datetime fields."""
    if table == "event":
        if _current_trace_id:
            _tid = _current_trace_id()
            if _tid:
                fields = dict(fields)
                fields.setdefault("trace_id", _tid)
                _sid = _span_id_var.get() if _span_id_var else ""
                if _sid:
                    fields.setdefault("span_id", _sid)
        fields = mios_audit.stamp(fields)
    elif table == "session":
        fields = mios_audit.stamp_session(fields)
    if passport_sign and _passport_sign:
        hash_fields = {k: "time::now()" for k in now_fields}
        for k, v in fields.items():
            if k in now_fields or v is None:
                continue
            hash_fields[k] = v
        envelope = _passport_sign(table, hash_fields)
        if envelope is not None:
            fields = dict(fields)
            fields["passport"] = envelope
    parts = [f"{k} = time::now()" for k in now_fields]
    for k, v in fields.items():
        if k in now_fields or v is None:
            continue
        parts.append(f"{k} = {json.dumps(v, default=str)}")
    sql = f"CREATE {table} SET " + ", ".join(parts)
    if extra:
        sql += " " + extra
    if _mirror:
        _pg_mirror(table, fields)
    return sql + ";"


def _db_write(table: str, fields: dict, *, now_fields: tuple = (),
              extra: str = "", passport_sign: bool = True) -> None:
    """Unified agent-plane WRITE seam (WS-9c full cutover)."""
    sql = _db_create(table, fields, now_fields=now_fields,
                     extra=extra, passport_sign=passport_sign)
    if not _PG_PRIMARY and _db_post:
        _db_fire(_db_post(sql))

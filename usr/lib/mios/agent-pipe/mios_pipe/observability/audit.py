# AI-hint: SEC-03 tamper-evident SHA-256 hash chain over the agent-plane `event` stream.
# AI-doc: usr/share/doc/mios/manual/observability.md

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Iterable, Optional

log = logging.getLogger("mios-agent-pipe")

try:  # real router in-process; shim keeps the PURE primitives importable headless
    from fastapi import APIRouter
    from fastapi.responses import JSONResponse
except Exception:  # noqa: BLE001 -- web stack absent (CLI / unit-test reuse): mirror mios_pg's lazy psycopg
    class _RouterShim:
        """Inert stand-in: ``.get()`` returns a passthrough decorator so the route
        definitions below load (but bind nothing) when fastapi is unavailable."""

        def get(self, *_a, **_k):
            def _decorator(fn):
                return fn
            return _decorator

    def APIRouter(*_a, **_k):  # noqa: N802 -- match the fastapi constructor name
        return _RouterShim()

    def JSONResponse(content=None, status_code=200):  # noqa: N802
        return content

CHAIN_ENABLE = True

_pg_execute = None

GENESIS = hashlib.sha256(b"").hexdigest()

CORE_FIELDS = ("source", "kind", "severity", "summary", "payload")

_VERIFY_COLS = ("chain_seq", "prev_hash", "chain_hash") + CORE_FIELDS

SESSION_CORE_FIELDS = ("id", "kind", "owui_chat_id", "meta")
_SESSION_VERIFY_COLS = ("chain_seq", "prev_hash", "chain_hash") + SESSION_CORE_FIELDS

def canonical_core(row: dict) -> str:
    core = {k: row[k] for k in CORE_FIELDS
            if isinstance(row, dict) and row.get(k) is not None}
    pl = core.get("payload")
    if isinstance(pl, str):
        try:
            core["payload"] = json.loads(pl)
        except (ValueError, TypeError):
            pass  # genuine free-text (non-JSON) payload -> hash the string as-is
    return json.dumps(core, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str)

def canonical_core_session(row: dict) -> str:
    core = {k: row[k] for k in SESSION_CORE_FIELDS
            if isinstance(row, dict) and row.get(k) is not None}
    meta = core.get("meta")
    if isinstance(meta, str):
        try:
            core["meta"] = json.loads(meta)
        except (ValueError, TypeError):
            pass
    return json.dumps(core, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str)

def link_hash(prev: Optional[str], core_str: str) -> str:
    """A single chain link: ``sha256(prev_hash || canonical_core)`` as hex."""
    return hashlib.sha256(((prev or "") + core_str).encode("utf-8")).hexdigest()

class EventChainer:
    """In-memory chain head. Holds the last assigned ``seq`` and the last
    ``chain_hash`` so a new event links to its predecessor WITHOUT a per-insert
    SELECT-max. Seeded once from the DB at startup; a single event loop serialises
    ``stamp`` so no lock is needed."""

    def __init__(self) -> None:
        self._prev: Optional[str] = None
        self._seq: int = 0
        self._seeded: bool = False

    @property
    def seeded(self) -> bool:
        return self._seeded

    def seed(self, seq, prev) -> None:
        """Warm the head from the persisted max(chain_seq). Marks the chainer ACTIVE;
        ``stamp`` only links once seeded so a startup DB miss never restarts the chain
        at seq=1 and collides with existing rows."""
        try:
            self._seq = int(seq or 0)
        except (TypeError, ValueError):
            self._seq = 0
        self._prev = prev or GENESIS
        self._seeded = True

    def stamp(self, fields: dict) -> dict:
        """Return a COPY of ``fields`` with ``chain_seq``/``prev_hash``/``chain_hash``
        added, advancing the in-memory head. Degrade-open: disabled, already-stamped
        (idempotent -- the ``_emit_session_event`` pre-stamp), not-yet-seeded, or any
        error returns ``fields`` UNCHANGED so the event still logs."""
        if not CHAIN_ENABLE or not isinstance(fields, dict):
            return fields
        if "chain_hash" in fields:           # already stamped -> do NOT advance twice
            return fields
        if not self._seeded:                 # startup race / DB miss -> unchained, safe
            return fields
        try:
            prev = self._prev if self._prev is not None else GENESIS
            chash = link_hash(prev, canonical_core(fields))
            seq = self._seq + 1
            out = dict(fields)
            out["chain_seq"] = seq
            out["prev_hash"] = prev
            out["chain_hash"] = chash
            self._prev = chash
            self._seq = seq
            return out
        except Exception:  # noqa: BLE001 -- tamper-evidence is best-effort; never block logging
            log.warning("event chain stamp failed (degrade-open: event logged unchained)",
                        exc_info=True)
            return fields

_CHAINER = EventChainer()

def stamp(fields: dict) -> dict:
    """Stamp an event row at the persist chokepoint (server._db_create / _emit_session_event)."""
    return _CHAINER.stamp(fields)

def verify_chain(rows: Iterable[dict]) -> dict:
    """Walk events in chain_seq order, recomputing each link from its predecessor."""
    prev = GENESIS
    checked = 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        expect = link_hash(prev, canonical_core(r))
        stored = r.get("chain_hash")
        stored_prev = r.get("prev_hash")
        if stored != expect or (stored_prev is not None and stored_prev != prev):
            seq = r.get("chain_seq")
            try:
                broken = int(seq) if seq is not None else None
            except (TypeError, ValueError):
                broken = None
            return {"ok": False, "checked": checked, "first_broken_seq": broken}
        prev = stored
        checked += 1
    return {"ok": True, "checked": checked, "first_broken_seq": None}

class SessionChainer:
    """In-memory chain head for the session table."""

    def __init__(self) -> None:
        self._prev: Optional[str] = None
        self._seq: int = 0
        self._seeded: bool = False

    @property
    def seeded(self) -> bool:
        return self._seeded

    def seed(self, seq, prev) -> None:
        try:
            self._seq = int(seq or 0)
        except (TypeError, ValueError):
            self._seq = 0
        self._prev = prev or GENESIS
        self._seeded = True

    def stamp(self, fields: dict) -> dict:
        if not CHAIN_ENABLE or not isinstance(fields, dict):
            return fields
        if "chain_hash" in fields:
            return fields
        if not self._seeded:
            return fields
        try:
            prev = self._prev if self._prev is not None else GENESIS
            chash = link_hash(prev, canonical_core_session(fields))
            seq = self._seq + 1
            out = dict(fields)
            out["chain_seq"] = seq
            out["prev_hash"] = prev
            out["chain_hash"] = chash
            self._prev = chash
            self._seq = seq
            return out
        except Exception:
            log.warning("session chain stamp failed (degrade-open)", exc_info=True)
            return fields

_SESSION_CHAINER = SessionChainer()

def stamp_session(fields: dict) -> dict:
    return _SESSION_CHAINER.stamp(fields)

def verify_session_chain(rows: Iterable[dict]) -> dict:
    """Walk session rows in chain_seq order, recomputing each link from its predecessor."""
    prev = GENESIS
    checked = 0
    for r in rows:
        if not isinstance(r, dict):
            continue
        expect = link_hash(prev, canonical_core_session(r))
        stored = r.get("chain_hash")
        stored_prev = r.get("prev_hash")
        if stored != expect or (stored_prev is not None and stored_prev != prev):
            seq = r.get("chain_seq")
            try:
                broken = int(seq) if seq is not None else None
            except (TypeError, ValueError):
                broken = None
            return {"ok": False, "checked": checked, "first_broken_seq": broken}
        prev = stored
        checked += 1
    return {"ok": True, "checked": checked, "first_broken_seq": None}

async def seed_from_db(pg_execute=None) -> None:
    if not CHAIN_ENABLE:
        return
    ex = pg_execute or _pg_execute
    if ex is None:
        return
    try:
        rows = await ex(
            "SELECT chain_seq, chain_hash FROM event "
            "WHERE chain_hash IS NOT NULL ORDER BY chain_seq DESC LIMIT 1",
            fetch=True)
    except Exception:  # noqa: BLE001
        log.warning("event chain seed query failed (chain stays off until restart)",
                    exc_info=True)
        return
    if rows is None:
        return
    if rows:
        head = rows[0] or {}
        _CHAINER.seed(head.get("chain_seq") or 0, head.get("chain_hash") or GENESIS)
    else:
        _CHAINER.seed(0, GENESIS)

async def seed_session_from_db(pg_execute=None) -> None:
    if not CHAIN_ENABLE:
        return
    ex = pg_execute or _pg_execute
    if ex is None:
        return
    try:
        rows = await ex(
            "SELECT chain_seq, chain_hash FROM session "
            "WHERE chain_hash IS NOT NULL ORDER BY chain_seq DESC LIMIT 1",
            fetch=True)
    except Exception:  # noqa: BLE001
        log.warning("session chain seed query failed (chain stays off until restart)",
                    exc_info=True)
        return
    if rows is None:
        return
    if rows:
        head = rows[0] or {}
        _SESSION_CHAINER.seed(head.get("chain_seq") or 0, head.get("chain_hash") or GENESIS)
    else:
        _SESSION_CHAINER.seed(0, GENESIS)

async def _read_chain_rows(pg_execute=None) -> Optional[list]:
    ex = pg_execute or _pg_execute
    if ex is None:
        return None
    try:
        return await ex(
            "SELECT " + ", ".join(_VERIFY_COLS) + " FROM event "
            "WHERE chain_hash IS NOT NULL ORDER BY chain_seq",
            fetch=True)
    except Exception:  # noqa: BLE001
        return None

async def _read_session_chain_rows(pg_execute=None) -> Optional[list]:
    ex = pg_execute or _pg_execute
    if ex is None:
        return None
    try:
        return await ex(
            "SELECT " + ", ".join(_SESSION_VERIFY_COLS) + " FROM session "
            "WHERE chain_hash IS NOT NULL ORDER BY chain_seq",
            fetch=True)
    except Exception:  # noqa: BLE001
        return None

async def chain_verify_logic(table: str = "event", pg_execute=None):
    if table == "session":
        rows = await _read_session_chain_rows(pg_execute)
        res = verify_session_chain(rows or [])
    else:
        rows = await _read_chain_rows(pg_execute)
        res = verify_chain(rows or [])
    return JSONResponse({"object": f"mios.audit.{table}.chain", "enabled": bool(CHAIN_ENABLE),
                         **res})

def configure(*, chain_enable=None, pg_execute=None) -> None:
    global CHAIN_ENABLE, _pg_execute
    if chain_enable is not None:
        CHAIN_ENABLE = chain_enable
    if pg_execute is not None:
        _pg_execute = pg_execute

audit_router = APIRouter()

@audit_router.get("/v1/audit/chain/verify")
async def chain_verify(table: str = "event"):
    return await chain_verify_logic(table=table)

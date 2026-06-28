# AI-hint: SEC-03 tamper-evident SHA-256 hash chain over the agent-plane `event` stream. Holds the PURE, dependency-free chain primitives (canonical_core over a row's immutable content fields, link_hash = sha256(prev || core), the EventChainer in-memory head that stamps each event with chain_seq/prev_hash/chain_hash at the single _db_create persist chokepoint, and verify_chain which walks rows in chain_seq order and reports the first broken link) PLUS the admin-gated GET /v1/audit/chain/verify route on its own co-located audit_router. The crypto is stdlib-only (hashlib/json) so the verifier reuses the SAME algorithm headless -- mios-chain-verify (a confined CLI) and the unit suite import it WITHOUT the web stack, mirroring mios_pg's lazy-psycopg testability (fastapi is imported behind a degrade-open shim). Degrade-open everywhere: a stamp/seed/verify failure NEVER breaks event logging (tamper-evidence is best-effort; the event must always land). The chain head is seeded once from max(chain_seq) at startup so the hot path never does a SELECT-max per insert.
# AI-related: ./server.py, ./mios_pg.py, ./mios_http_caps.py, ./test_mios_audit.py, ../../../libexec/mios/mios-chain-verify, ../../../share/mios/postgres/schema-init.sql, ../../../share/mios/ai/v1/surface.generated.json
# AI-functions: canonical_core, link_hash, EventChainer.seed, EventChainer.stamp, stamp, seed_from_db, verify_chain, chain_verify_logic, chain_verify, configure
"""mios_audit -- SHA-256 tamper-evident hash chaining for the MiOS event bus (SEC-03).

The agent-plane ``event`` table is an append-only observability stream. This module
makes it tamper-EVIDENT: every persisted event is linked to its predecessor by a
SHA-256 hash chain, so any later insert / delete / reorder / content edit breaks the
chain at a detectable point. It is the integrity substrate the record-replay,
self-improve-act and DGM workstreams build on (a replay you cannot trust the order of
is worthless).

DESIGN (single chokepoint, hot-path-safe, degrade-open):

* The chain is computed at the ONE place every event row is built -- ``server._db_create``
  for ``table == "event"`` (and the session-linked ``_emit_session_event``, which
  pre-stamps so its own pgvector mirror carries the chain columns). ``stamp()`` adds
  three columns to the row: ``chain_seq`` (a monotonic position assigned in WRITE order,
  not DB-insert order, since the mirror INSERT is fire-and-forget and may reorder),
  ``prev_hash`` (the predecessor's ``chain_hash``), and
  ``chain_hash = sha256(prev_hash || canonical_core(row))``.

* ``canonical_core`` hashes only the IMMUTABLE CONTENT columns
  (``source/kind/severity/summary/payload``) as sorted-keys compact JSON -- never the
  volatile / DB-assigned fields (``ts`` is set by the DB clock and is not reproducible
  at write parity, so temporal ORDER is bound by the chain itself rather than a
  self-reported timestamp; ``trace_id``/``span_id``/``passport``/``id`` are correlation
  metadata). The same canonicalization runs at verify time over the stored columns, so
  the verifier reproduces each hash deterministically.

* The chain head (last seq + last hash) lives in an in-memory ``EventChainer``, seeded
  ONCE from ``max(chain_seq)`` at startup -- so the hot path never issues a SELECT-max
  per insert. A single asyncio event loop serialises the synchronous ``stamp()``, so the
  counter needs no lock.

* DEGRADE-OPEN is absolute: a hashing error, an unseeded head (startup DB miss), or the
  feature being disabled returns the row UNCHANGED so the event still logs. Tamper-
  evidence is best-effort; event logging must never fail because of it.

The PURE primitives (``canonical_core`` / ``link_hash`` / ``EventChainer`` /
``verify_chain``) are stdlib-only and carry NO server/DB/web dependency, so the verify
CLI and the unit tests reuse the exact same algorithm. ``fastapi`` is imported behind a
degrade-open shim purely so this module also imports on a host without the web stack
(the live agent-pipe always has fastapi, so the real router binds in-process).
"""

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


# ── chain configuration (SSOT [audit] -> injected by server.configure) ────────
# Default ON: the per-event overhead is a single sha256 over a small JSON string +
# an in-memory cache update (no extra DB round-trip -- the chain columns ride the
# existing INSERT), and tamper-evident audit is a security primitive other
# workstreams depend on. Flip [audit].chain_enable=false to disable.
CHAIN_ENABLE = True

# Async pg read callable injected from server (mios_pg.execute): (sql, params=None,
# *, fetch=False) -> rows|None. Used for the startup seed + the verify endpoint read.
_pg_execute = None

# Genesis seed: the prev_hash of the first-ever event. sha256 of the empty input --
# a fixed, structural anchor (NOT a tunable / secret), so any independent verifier
# starts the walk from the identical constant.
GENESIS = hashlib.sha256(b"").hexdigest()

# The IMMUTABLE content columns the chain hash binds. An allowlist (not a denylist)
# guarantees write-time and verify-time hash the SAME field set regardless of which
# correlation/metadata columns happen to be present on the row.
CORE_FIELDS = ("source", "kind", "severity", "summary", "payload")

# Columns the verify read pulls back (content + chain), ordered by chain_seq.
_VERIFY_COLS = ("chain_seq", "prev_hash", "chain_hash") + CORE_FIELDS


# ── pure chain primitives (stdlib only; reused by server, CLI and tests) ──────
def canonical_core(row: dict) -> str:
    """Deterministic serialization of an event row's immutable CONTENT fields.

    Sorted-keys, compact-separator JSON over the present (non-None) ``CORE_FIELDS``.
    ``default=str`` matches how the row is serialized into storage (so a value the
    write path coerced to text, e.g. a datetime, reproduces identically here);
    ``ensure_ascii=False`` keeps unicode byte-stable on both sides.

    NG-3 payload normalisation: ``payload`` is a jsonb column. A write call-site may
    hand it in EITHER form -- a parsed dict/list (the common case) OR a pre-serialised
    JSON STRING -- but mios_pg binds a string into jsonb and psycopg reads it back as
    the PARSED object at verify time. So a string payload is parsed (``json.loads``) to
    its structural form before hashing, so WRITE and VERIFY canonicalize the SAME
    structure regardless of which form the row carried (otherwise a string-vs-dict
    asymmetry reports a spurious "broken" link). A string that is NOT valid JSON (a
    genuine free-text payload) is left unchanged; any other non-dict payload
    (number/list) is just another JSON value under the ``payload`` key, unchanged."""
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


# Module-global head (one chain per process; server seeds + drives it).
_CHAINER = EventChainer()


def stamp(fields: dict) -> dict:
    """Stamp an event row at the persist chokepoint (server._db_create / _emit_session_event)."""
    return _CHAINER.stamp(fields)


def verify_chain(rows: Iterable[dict]) -> dict:
    """Walk events in chain_seq order, recomputing each link from its predecessor.

    ``rows`` MUST already be ordered by ``chain_seq`` (the reader SELECTs ORDER BY
    chain_seq). Returns ``{ok, checked, first_broken_seq}``. A link is broken when the
    stored ``chain_hash`` does not equal ``sha256(prev || canonical_core(row))`` OR the
    stored ``prev_hash`` does not point at the predecessor's hash -- i.e. an inserted,
    deleted, reordered, or content-edited row. ``first_broken_seq`` is the chain_seq of
    the first failing row (``None`` when the whole chain verifies)."""
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


# ── startup seed + endpoint read (async; pg access injected) ──────────────────
async def seed_from_db(pg_execute=None) -> None:
    """Warm the in-memory chain head from the persisted ``max(chain_seq)`` ONCE at
    startup, so the hot path never does a SELECT-max per insert. Best-effort: on a DB
    miss (rows is None) the chainer stays UNSEEDED -- ``stamp`` then degrades to
    unchained rather than restarting at seq=1 and colliding with existing rows. An
    empty table seeds genesis (chain starts active)."""
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
    except Exception:  # noqa: BLE001 -- degrade-open: chain stays off this session
        log.warning("event chain seed query failed (chain stays off until restart)",
                    exc_info=True)
        return
    if rows is None:                 # DB down/absent -> stay unseeded (no dup-seq restart)
        return
    if rows:
        head = rows[0] or {}
        _CHAINER.seed(head.get("chain_seq") or 0, head.get("chain_hash") or GENESIS)
    else:
        _CHAINER.seed(0, GENESIS)    # fresh table -> genesis, chain active


async def _read_chain_rows(pg_execute=None) -> Optional[list]:
    """Read all chained event rows in chain_seq order for verification. Degrade-open
    -> None on any error (the endpoint then reports an empty, trivially-OK chain)."""
    ex = pg_execute or _pg_execute
    if ex is None:
        return None
    try:
        return await ex(
            "SELECT " + ", ".join(_VERIFY_COLS) + " FROM event "
            "WHERE chain_hash IS NOT NULL ORDER BY chain_seq",
            fetch=True)
    except Exception:  # noqa: BLE001 -- degrade-open
        log.warning("event chain verify read failed (degrade-open)", exc_info=True)
        return None


async def chain_verify_logic(pg_execute=None):
    """Verify the persisted event chain end-to-end. Reads every chained row via the
    injected pg access path, walks it with :func:`verify_chain`, and returns the
    JSON verdict ``{ok, checked, first_broken_seq, enabled}``."""
    rows = await _read_chain_rows(pg_execute)
    res = verify_chain(rows or [])
    return JSONResponse({"object": "mios.audit.chain", "enabled": bool(CHAIN_ENABLE),
                         **res})


# ── DI seam (server injects the pg reader + the SSOT enable flag) ─────────────
def configure(*, chain_enable=None, pg_execute=None) -> None:
    """Inject server.py's ``[audit].chain_enable`` SSOT flag + the mios_pg async
    execute callable the seed/verify reads use (one-way boundary: this module never
    imports server)."""
    global CHAIN_ENABLE, _pg_execute
    if chain_enable is not None:
        CHAIN_ENABLE = chain_enable
    if pg_execute is not None:
        _pg_execute = pg_execute


# ── admin route (co-located router; mounted once via app.include_router) ───────
# Gated like every other /v1/* admin route by server's _inbound_auth_mw (credential
# required when [security].api_require_auth is on) -- mounting under /v1/audit puts it
# behind the SAME gate; no per-route auth code is restated here.
audit_router = APIRouter()


@audit_router.get("/v1/audit/chain/verify")
async def chain_verify():
    """SEC-03: walk the event hash chain and report integrity. Returns
    ``{ok, checked, first_broken_seq, enabled}`` -- ``first_broken_seq`` names the
    first tampered (inserted/deleted/reordered/edited) event, or is null when clean."""
    return await chain_verify_logic()

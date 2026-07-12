# AI-hint: Standalone unit test for mios_pg to verify pure-python PostgreSQL helper logic, including DSN construction, vector literal formatting, and SQL insert generation for knowledge and event tables.
# AI-related: mios_pg
# AI-functions: _check, t_config_dsn, t_vector_literal, t_build_insert, t_build_insert_jsonb, t_build_recall, t_build_recall_emb_version, t_recall_tuning, t_rid_to_pg_id, t_rls_owner_scope, main
"""Standalone unit test for mios_pg pure helpers (WS-9 Postgres client).

Pure stdlib + the sibling module only -- no psycopg, no live Postgres (the I/O is
verified by the operator on MiOS-DEV). Run:  python test_mios_pg.py
"""

import asyncio
import os
import sys
import types

import mios_pg as P

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_config_dsn() -> None:
    env = {"MIOS_PG_HOST": "h", "MIOS_PORT_PGVECTOR": "5544",
           "MIOS_PG_USER": "u", "MIOS_PG_PASS": "p", "MIOS_PG_DB": "d"}
    c = P.pg_config(env)
    _check("config: parsed", c == {"host": "h", "port": 5544, "user": "u",
                                   "password": "p", "dbname": "d"}, str(c))
    _check("dsn: built", P.dsn(c) == "postgresql://u:p@h:5544/d", P.dsn(c))
    d = P.pg_config({})
    _check("config: local defaults", d["host"] == "localhost" and d["port"] == 8432
           and d["user"] == "mios" and d["dbname"] == "mios", str(d))


def t_vector_literal() -> None:
    _check("vec: format", P.vector_literal([0.1, 0.2, 0.3]) == "[0.1,0.2,0.3]",
           P.vector_literal([0.1, 0.2, 0.3]))
    _check("vec: empty", P.vector_literal([]) == "[]")
    _check("vec: coerces ints", P.vector_literal([1, 2]) == "[1.0,2.0]")


def t_build_insert() -> None:
    sql, params = P.build_insert("knowledge",
                                 {"q": "hi", "answer": "yo", "tier": "warm",
                                  "emb": [0.1, 0.2]})
    _check("insert: cols", "INSERT INTO knowledge (q, answer, tier, emb)" in sql, sql)
    _check("insert: emb cast", "%(emb)s::vector" in sql, sql)
    _check("insert: returning id", sql.strip().endswith("RETURNING id;"))
    _check("insert: no value interpolation", "hi" not in sql and "yo" not in sql)
    _check("insert: params bound", params["q"] == "hi" and params["answer"] == "yo")
    _check("insert: emb -> literal", params["emb"] == "[0.1,0.2]", str(params["emb"]))


def t_build_insert_jsonb() -> None:
    sql, params = P.build_insert("event",
                                 {"kind": "x", "payload": {"a": 1, "b": [2, 3]},
                                  "sources": ["u:remember", "url"]})
    _check("jsonb: dict cast", "%(payload)s::jsonb" in sql, sql)
    _check("jsonb: list cast", "%(sources)s::jsonb" in sql, sql)
    _check("jsonb: scalar plain", "%(kind)s," in sql or "%(kind)s)" in sql, sql)
    _check("jsonb: dict serialized", params["payload"] == '{"a": 1, "b": [2, 3]}',
           str(params["payload"]))
    _check("jsonb: list serialized", params["sources"] == '["u:remember", "url"]',
           str(params["sources"]))


def t_build_recall() -> None:
    sql, params = P.build_recall("knowledge", k=5)
    _check("recall: cosine op", "emb <=> %(qvec)s::vector" in sql, sql)
    _check("recall: similarity expr", "1 - (emb <=> %(qvec)s::vector) AS score" in sql)
    _check("recall: order+limit", "ORDER BY emb <=> %(qvec)s::vector LIMIT %(k)s" in sql)
    _check("recall: filters null emb", "WHERE emb IS NOT NULL" in sql)
    _check("recall: k bound", params["k"] == 5)


def t_build_recall_emb_version() -> None:
    # A3 embedding-version hygiene: with an ACTIVE emb_version + a versioned table,
    # recall scopes to the active embedding space (+ NULL/un-stamped rows), so a
    # model/dim change can't mix incompatible vector spaces in one cosine query.
    sql, params = P.build_recall("knowledge", k=3, emb_version="v2")
    _check("emb_ver: filter present",
           "(emb_version = %(emb_version)s OR emb_version IS NULL)" in sql, sql)
    _check("emb_ver: bound param", params.get("emb_version") == "v2", str(params))
    # DEGRADE-OPEN: no active version -> byte-identical to the unfiltered query.
    sql0, p0 = P.build_recall("knowledge", k=3)
    _check("emb_ver: none -> no filter",
           "emb_version" not in sql0 and "emb_version" not in p0, sql0)
    sqle, pe = P.build_recall("knowledge", k=3, emb_version="")
    _check("emb_ver: empty -> no filter (degrade-open)",
           "emb_version" not in sqle and "emb_version" not in pe, sqle)
    # agent_memory is versioned too; mios_rag has NO emb_version column -> never filtered
    # (filtering it would raise UndefinedColumn and arm the degrade-open backoff).
    sql_am, _ = P.build_recall("agent_memory", k=3, emb_version="v2")
    _check("emb_ver: agent_memory filtered", "emb_version = %(emb_version)s" in sql_am, sql_am)
    sql_rag, p_rag = P.build_recall("mios_rag", k=3, emb_version="v2")
    _check("emb_ver: mios_rag NOT filtered (no column)",
           "emb_version" not in sql_rag and "emb_version" not in p_rag, sql_rag)
    # Semantic check mirroring `emb_version = active OR emb_version IS NULL`: a
    # matching row + a NULL row are KEPT; a mismatched row is EXCLUDED.
    def _kept(row_ver, active="v2"):
        return row_ver is None or row_ver == active
    _check("emb_ver: keeps matching row", _kept("v2") is True)
    _check("emb_ver: keeps NULL/un-stamped row", _kept(None) is True)
    _check("emb_ver: excludes mismatched row", _kept("v1") is False)


def t_build_fts_query() -> None:
    # knowledge (default)
    sql, params = P.build_fts_query("knowledge", k=5)
    _check("fts: expr on knowledge", "fts @@ plainto_tsquery('simple', %(query_text)s)" in sql, sql)
    _check("fts: ts_rank score", "ts_rank(fts, plainto_tsquery('simple', %(query_text)s)) AS score" in sql, sql)
    _check("fts: order by score", "ORDER BY score DESC LIMIT %(k)s" in sql, sql)
    _check("fts: k bound", params["k"] == 5)

    # mios_rag
    sql_rag, _ = P.build_fts_query("mios_rag", k=3)
    _check("fts: expr on mios_rag", "to_tsvector('simple', coalesce(content, '')) @@ plainto_tsquery" in sql_rag, sql_rag)

    # agent_memory
    sql_am, _ = P.build_fts_query("agent_memory", k=3, emb_version="v2")
    _check("fts: expr on agent_memory", "to_tsvector('simple', coalesce(fact, '') || ' ' || coalesce(scope, ''))" in sql_am, sql_am)
    _check("fts: emb_version on agent_memory", "emb_version = %(emb_version)s" in sql_am, sql_am)


def t_recall_tuning() -> None:
    _check("tuning: ef_search", P.recall_tuning(120) == "SET hnsw.ef_search = 120;",
           P.recall_tuning(120))


def t_rid_to_pg_id() -> None:
    # legacy record-string -> trailing bigint
    _check("rid: legacy numeric tail", P.rid_to_pg_id("knowledge:123") == 123)
    _check("rid: pending_action tail", P.rid_to_pg_id("pending_action:42") == 42)
    # bare bigint (int or str) -> itself
    _check("rid: bare int", P.rid_to_pg_id(789) == 789)
    _check("rid: bare numeric str", P.rid_to_pg_id("456") == 456)
    # non-numeric / missing -> None (caller skips the pg write)
    _check("rid: alpha legacy id -> None", P.rid_to_pg_id("knowledge:abc") is None)
    _check("rid: None -> None", P.rid_to_pg_id(None) is None)
    _check("rid: empty -> None", P.rid_to_pg_id("") is None)


def t_rls_owner_scope() -> None:
    # T-068 DB-side RLS: build_set_owner emits a PARAMETER-bound set_config with
    # is_local=true (SET LOCAL semantics) -- neither the GUC name nor the owner is
    # spliced into the SQL text.
    sql, params = P.build_set_owner("alice")
    _check("rls: set_config call shape",
           "set_config(%(guc)s, %(owner)s, true)" in sql, sql)
    _check("rls: guc bound, not spliced",
           params["guc"] == "mios.owner_user" and "mios.owner_user" not in sql, sql)
    _check("rls: owner bound, not spliced",
           params["owner"] == "alice" and "alice" not in sql, sql)

    # rls_enabled reads the env (default OFF); only the truthy set turns it on.
    _check("rls: disabled by default (no env)", P.rls_enabled({}) is False)
    _check("rls: enabled on truthy",
           P.rls_enabled({"MIOS_DB_RLS_ENABLE": "true"}) is True
           and P.rls_enabled({"MIOS_DB_RLS_ENABLE": "1"}) is True
           and P.rls_enabled({"MIOS_DB_RLS_ENABLE": "ON"}) is True)
    _check("rls: disabled on falsy",
           P.rls_enabled({"MIOS_DB_RLS_ENABLE": "0"}) is False
           and P.rls_enabled({"MIOS_DB_RLS_ENABLE": "false"}) is False
           and P.rls_enabled({"MIOS_DB_RLS_ENABLE": ""}) is False)

    # P2-1: _owner_scope emits SET LOCAL ONLY when rls_enable AND the principal is
    # enforce-verified ([security].principal_bind_mode=enforce, read via the SSOT seam
    # mios_grounding._principal_bind_mode -> the MIOS_PRINCIPAL_BIND_MODE env here). The
    # bind mode is controlled through os.environ (the live request path resolves it the
    # same way); snapshot+restore so order can't leak. The owner GUC must NEVER be
    # emitted for an unverified (spoofable) owner -- that would be FALSE DB isolation.
    _prior_bm = os.environ.get("MIOS_PRINCIPAL_BIND_MODE")
    try:
        # rls_enable=false short-circuits FIRST -> byte-identical no-op even under
        # enforce (the default-off path is unchanged regardless of bind mode).
        os.environ["MIOS_PRINCIPAL_BIND_MODE"] = "enforce"
        _check("rls: scope None when rls_enable=false (byte-identical no-op, even w/ enforce)",
               P._owner_scope("alice", {}) is None
               and P._owner_scope("alice", {"MIOS_DB_RLS_ENABLE": "0"}) is None)

        # rls_enable=true + enforce-verified + owner -> the param-bound set_config tuple
        # IS emitted (the ONLY path that DB-scopes rows), and NO false-warn fires.
        P._RLS_UNVERIFIED_WARNED = False
        sc = P._owner_scope("alice", {"MIOS_DB_RLS_ENABLE": "1"})
        _check("rls: scope emitted when enabled+enforce+owner",
               sc is not None and "set_config" in sc[0]
               and sc[1] == {"guc": "mios.owner_user", "owner": "alice"}, str(sc))
        _check("rls: no false-warn on the verified emit path",
               P._RLS_UNVERIFIED_WARNED is False)

        # FOOTGUN CLOSED: rls_enable=true but bind-mode NOT enforce (off OR verify) ->
        # the owner is UNVERIFIED/spoofable -> emit NOTHING (degrade to permissive =
        # honest, no false isolation) + log a ONE-TIME loud WARN.
        for _mode in ("off", "verify"):
            os.environ["MIOS_PRINCIPAL_BIND_MODE"] = _mode
            P._RLS_UNVERIFIED_WARNED = False
            sc_unv = P._owner_scope("victim", {"MIOS_DB_RLS_ENABLE": "1"})
            _check(f"rls: NO scope when enabled but bind-mode={_mode} (no false isolation)",
                   sc_unv is None, str(sc_unv))
            _check(f"rls: one-time WARN fired (bind-mode={_mode})",
                   P._RLS_UNVERIFIED_WARNED is True)

        # enabled + enforce + NO owner -> None (DEGRADE-OPEN: a system/daemon/seeding
        # connection leaves the GUC unset -> the schema policy stays permissive -> never
        # locked out). Owner-less is intentional, NOT a misconfig -> no warn.
        os.environ["MIOS_PRINCIPAL_BIND_MODE"] = "enforce"
        P._RLS_UNVERIFIED_WARNED = False
        _check("rls: scope None when enabled+no-owner (degrade-open, no lockout)",
               P._owner_scope(None, {"MIOS_DB_RLS_ENABLE": "1"}) is None
               and P._owner_scope("", {"MIOS_DB_RLS_ENABLE": "1"}) is None
               and P._owner_scope("   ", {"MIOS_DB_RLS_ENABLE": "1"}) is None)
        _check("rls: no warn on the owner-less (intentional) path",
               P._RLS_UNVERIFIED_WARNED is False)
    finally:
        if _prior_bm is None:
            os.environ.pop("MIOS_PRINCIPAL_BIND_MODE", None)
        else:
            os.environ["MIOS_PRINCIPAL_BIND_MODE"] = _prior_bm
        P._RLS_UNVERIFIED_WARNED = False


# ── opt-in connection pool (mios_pg.AsyncConnPool / _conn) ───────────────────
# psycopg is NOT installed in this offline harness, so the pool's I/O path is
# exercised against a FAKE psycopg injected into sys.modules. The fake models the
# bits the pool + execute() touch: per-call connect logging, `async with conn`
# closing the connection (the historic per-call lifecycle), a cursor, a
# transaction() block that applies/discards a transaction-scoped SET LOCAL (so the
# RLS owner-GUC leak guarantee is testable), and transaction_status for the
# check-in cleanliness guard.
class _FakeInfo:
    def __init__(self) -> None:
        self.transaction_status = 0   # 0 == IDLE (psycopg pq.TransactionStatus.IDLE)


class _FakeCursor:
    def __init__(self, conn) -> None:
        self.conn = conn

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def execute(self, sql, params=None):
        self.conn.executed.append((str(sql), dict(params) if params else None))
        # Emulate set_config(guc, owner, is_local=true) -> a SET LOCAL of the owner
        # GUC (transaction-scoped) vs a leaked session-level SET (the failure signal).
        if "set_config" in str(sql) and params and params.get("guc"):
            target = self.conn.local_guc if self.conn._in_txn else self.conn.session_guc
            target[params["guc"]] = params.get("owner")
        return self

    async def fetchall(self):
        return list(self.conn.fetch_rows)


class _FakeTxn:
    def __init__(self, conn) -> None:
        self.conn = conn

    async def __aenter__(self):
        self.conn._in_txn = True
        self.conn.info.transaction_status = 1   # inside a transaction block
        return self

    async def __aexit__(self, et, ev, tb):
        # commit (or rollback on error): SET LOCAL settings are discarded, txn closes
        self.conn.local_guc.clear()
        self.conn._in_txn = False
        self.conn.info.transaction_status = 0
        return False


class _FakeConn:
    def __init__(self) -> None:
        self.closed = False
        self.broken = False
        self.info = _FakeInfo()
        self.executed: list = []
        self.local_guc: dict = {}     # transaction-scoped (SET LOCAL) settings
        self.session_guc: dict = {}   # session-scoped settings (MUST stay {} == no leak)
        self._in_txn = False
        self.fetch_rows: list = []
        self.rolled_back = 0

    def cursor(self, row_factory=None):
        return _FakeCursor(self)

    def transaction(self):
        return _FakeTxn(self)

    async def rollback(self):
        self.rolled_back += 1
        self.local_guc.clear()
        self._in_txn = False
        self.info.transaction_status = 0

    async def close(self):
        self.closed = True

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        # psycopg3 closes the connection on context-manager exit (per-call path).
        self.closed = True
        return False


class _FakeAsyncConnection:
    opened: list = []   # class-level connect log

    @classmethod
    async def connect(cls, conninfo=None, autocommit=None, connect_timeout=None, **kw):
        c = _FakeConn()
        cls.opened.append(c)
        return c


def _install_fake_psycopg() -> None:
    mod = types.ModuleType("psycopg")
    mod.AsyncConnection = _FakeAsyncConnection
    rows = types.ModuleType("psycopg.rows")
    rows.dict_row = object()
    mod.rows = rows
    sys.modules["psycopg"] = mod
    sys.modules["psycopg.rows"] = rows
    _FakeAsyncConnection.opened = []


async def _two_executes(*, owner1=None):
    _FakeAsyncConnection.opened = []
    await P.execute("SELECT 1", fetch=False, rls_owner=owner1)
    await P.execute("SELECT 2", fetch=False)
    return list(_FakeAsyncConnection.opened)


def _set_env(**kw):
    """Set/clear env vars, returning a restore callable (snapshot+restore)."""
    prior = {k: os.environ.get(k) for k in kw}

    def _restore():
        for k, v in prior.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    for k, v in kw.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    return _restore


def t_pool_default_off_per_call_connect() -> None:
    # DEFAULT-OFF: byte-identical to the historic path -- a fresh connect PER call,
    # each closed after use, and the pool object is never even created.
    _install_fake_psycopg()
    restore = _set_env(MIOS_PG_POOL_ENABLE=None)
    P._POOL = None
    P._pg_down_until = 0.0
    try:
        opened = asyncio.run(_two_executes())
        _check("pool off: 2 calls -> 2 fresh connects (per-call connect, unchanged)",
               len(opened) == 2, f"connects={len(opened)}")
        _check("pool off: each connection closed after its call (per-call lifecycle)",
               all(c.closed for c in opened), str([c.closed for c in opened]))
        _check("pool off: pool object never created (byte-identical path)",
               P._POOL is None)
    finally:
        P._POOL = None
        restore()


def t_pool_on_reuses_connection() -> None:
    # ON: the two sequential queries share ONE pooled connection (no connect storm).
    _install_fake_psycopg()
    restore = _set_env(MIOS_PG_POOL_ENABLE="1")
    P._POOL = None
    P._pg_down_until = 0.0
    try:
        opened = asyncio.run(_two_executes())
        _check("pool on: 2 calls REUSE one connection (1 connect total)",
               len(opened) == 1, f"connects={len(opened)}")
        _check("pool on: the reused connection stays open between calls",
               bool(opened) and opened[0].closed is False)
        _check("pool on: both queries ran on the one reused connection",
               bool(opened) and len(opened[0].executed) == 2,
               str(opened[0].executed if opened else None))
    finally:
        P._POOL = None
        restore()


class _PoisonPool:
    """A pool whose checkout always fails -- exercises _conn's degrade-open path."""
    async def acquire(self, cfg=None):
        raise RuntimeError("pool poisoned")

    async def release(self, *a, **k):
        return None


def t_pool_degrade_open_poisoned() -> None:
    # DEGRADE-OPEN: a broken pool must never fail a query -- _conn falls back to a
    # direct connect and the query still runs (returns a result, not None-from-mark-down).
    _install_fake_psycopg()
    restore = _set_env(MIOS_PG_POOL_ENABLE="1")
    P._POOL = _PoisonPool()   # enabled + non-None -> _get_pool hands back this broken pool
    P._pg_down_until = 0.0
    try:
        async def _go():
            _FakeAsyncConnection.opened = []
            r = await P.execute("SELECT 1", fetch=True)
            return r, list(_FakeAsyncConnection.opened)
        r, opened = asyncio.run(_go())
        _check("pool degrade: poisoned checkout falls back to a direct connect",
               len(opened) == 1, f"connects={len(opened)}")
        _check("pool degrade: the query still returns a result (never fails on the pool)",
               r == [], str(r))
    finally:
        P._POOL = None
        restore()


def t_pool_no_owner_guc_leak() -> None:
    # SECURITY: an owner-scoped call (SET LOCAL mios.owner_user) followed by a plain
    # call on the SAME reused connection must NOT leak the owner GUC. SET LOCAL is
    # transaction-scoped (cleared on the txn commit/rollback), and the plain call
    # emits no scope at all -- so the reused connection carries nothing across.
    _install_fake_psycopg()
    restore = _set_env(MIOS_PG_POOL_ENABLE="1", MIOS_DB_RLS_ENABLE="1",
                       MIOS_PRINCIPAL_BIND_MODE="enforce")
    P._POOL = None
    P._pg_down_until = 0.0
    P._RLS_UNVERIFIED_WARNED = False
    try:
        opened = asyncio.run(_two_executes(owner1="alice"))
        _check("pool+RLS: owner-scoped call + plain call REUSE one connection",
               len(opened) == 1, f"connects={len(opened)}")
        conn = opened[0] if opened else None
        _check("pool+RLS: owner GUC never leaked to the SESSION (no cross-checkout leak)",
               conn is not None and conn.session_guc == {},
               str(conn.session_guc if conn else None))
        _check("pool+RLS: transaction-scoped owner GUC cleared after the scoped call",
               conn is not None and conn.local_guc == {},
               str(conn.local_guc if conn else None))
        setcfgs = [e for e in (conn.executed if conn else []) if "set_config" in e[0]]
        _check("pool+RLS: exactly ONE owner-scope statement (call 1 only; plain call inherited none)",
               len(setcfgs) == 1, str(setcfgs))
    finally:
        P._POOL = None
        P._RLS_UNVERIFIED_WARNED = False
        restore()


def t_pool_checkin_cleans_connection() -> None:
    # Check-in cleanliness guard: a connection released with a transaction left OPEN
    # (status != IDLE, e.g. a stray SET LOCAL) is ROLLED BACK before reuse (which
    # discards the SET LOCAL); a broken connection is discarded, not pooled.
    _install_fake_psycopg()

    async def _dirty_then_release():
        pool = P.AsyncConnPool(min_size=0, max_size=2)
        conn, pooled = await pool.acquire()
        conn.info.transaction_status = 1            # a transaction was left open
        conn.local_guc["mios.owner_user"] = "ghost"  # ... with a stray SET LOCAL
        await pool.release(conn, pooled, ok=True)
        return conn, pool

    async def _broken_release():
        pool = P.AsyncConnPool(min_size=0, max_size=2)
        conn, pooled = await pool.acquire()
        conn.broken = True
        await pool.release(conn, pooled, ok=True)
        return pool

    conn, pool = asyncio.run(_dirty_then_release())
    _check("pool checkin: open transaction rolled back on release (SET LOCAL discarded)",
           conn.rolled_back >= 1 and conn.local_guc == {},
           f"rolled={conn.rolled_back} local={conn.local_guc}")
    _check("pool checkin: the cleaned connection is returned for reuse",
           pool._free == [conn] and pool._size == 1)

    pool2 = asyncio.run(_broken_release())
    _check("pool checkin: a broken connection is discarded, not reused",
           pool2._free == [] and pool2._size == 0)


def t_pool_warm_and_exhaustion() -> None:
    # min_size pre-opens warm connections on first use; at max with none free the
    # pool degrades-open to an ephemeral (un-pooled) connection rather than blocking.
    _install_fake_psycopg()

    async def _warm():
        _FakeAsyncConnection.opened = []
        pool = P.AsyncConnPool(min_size=2, max_size=4)
        conn, pooled = await pool.acquire()
        return pool, pooled, list(_FakeAsyncConnection.opened)

    async def _exhaust():
        _FakeAsyncConnection.opened = []
        pool = P.AsyncConnPool(min_size=0, max_size=1)
        _c1, p1 = await pool.acquire()      # grows to the cap
        _c2, p2 = await pool.acquire()      # exhausted -> ephemeral
        return p1, p2, list(_FakeAsyncConnection.opened)

    pool, pooled, opened = asyncio.run(_warm())
    _check("pool warm: min_size pre-opens that many connections on first use",
           len(opened) == 2, f"opened={len(opened)}")
    _check("pool warm: one warm conn handed out (pooled), one stays idle",
           pooled is True and pool._size == 2 and len(pool._free) == 1,
           f"size={pool._size} free={len(pool._free)}")

    p1, p2, opened2 = asyncio.run(_exhaust())
    _check("pool exhaust: at-capacity checkout degrades to an ephemeral conn (pooled=False)",
           p1 is True and p2 is False, f"p1={p1} p2={p2}")
    _check("pool exhaust: the ephemeral conn is opened beyond the cap (never blocks)",
           len(opened2) == 2, f"opened={len(opened2)}")


def main() -> int:
    for t in (t_config_dsn, t_vector_literal, t_build_insert, t_build_insert_jsonb,
              t_build_recall, t_build_recall_emb_version, t_build_fts_query, t_recall_tuning,
              t_rid_to_pg_id, t_rls_owner_scope,
              t_pool_default_off_per_call_connect, t_pool_on_reuses_connection,
              t_pool_degrade_open_poisoned, t_pool_no_owner_guc_leak,
              t_pool_checkin_cleans_connection, t_pool_warm_and_exhaustion):
        t()
    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

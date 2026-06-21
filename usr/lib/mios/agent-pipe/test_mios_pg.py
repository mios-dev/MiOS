# AI-hint: Standalone unit test for mios_pg to verify pure-python PostgreSQL helper logic, including DSN construction, vector literal formatting, and SQL insert generation for knowledge and event tables.
# AI-related: mios_pg
# AI-functions: _check, t_config_dsn, t_vector_literal, t_build_insert, t_build_insert_jsonb, t_build_recall, t_recall_tuning, main
"""Standalone unit test for mios_pg pure helpers (WS-9 Postgres client).

Pure stdlib + the sibling module only -- no psycopg, no live Postgres (the I/O is
verified by the operator on MiOS-DEV). Run:  python test_mios_pg.py
"""

import sys

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
    _check("config: local defaults", d["host"] == "localhost" and d["port"] == 5432
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


def t_recall_tuning() -> None:
    _check("tuning: ef_search", P.recall_tuning(120) == "SET hnsw.ef_search = 120;",
           P.recall_tuning(120))


def t_rid_to_pg_id() -> None:
    # surreal record-string -> trailing bigint
    _check("rid: surreal numeric tail", P.rid_to_pg_id("knowledge:123") == 123)
    _check("rid: pending_action tail", P.rid_to_pg_id("pending_action:42") == 42)
    # bare bigint (int or str) -> itself
    _check("rid: bare int", P.rid_to_pg_id(789) == 789)
    _check("rid: bare numeric str", P.rid_to_pg_id("456") == 456)
    # non-numeric / missing -> None (caller skips the pg write)
    _check("rid: alpha surreal id -> None", P.rid_to_pg_id("knowledge:abc") is None)
    _check("rid: None -> None", P.rid_to_pg_id(None) is None)
    _check("rid: empty -> None", P.rid_to_pg_id("") is None)


def main() -> int:
    for t in (t_config_dsn, t_vector_literal, t_build_insert, t_build_insert_jsonb,
              t_build_recall, t_recall_tuning, t_rid_to_pg_id):
        t()
    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

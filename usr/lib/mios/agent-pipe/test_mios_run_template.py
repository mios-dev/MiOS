#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_pipe.routing.run_template -- the WS-6 capture half plus the T-225 replay read side, extracted out of dag_exec. Proves the structural plan-shape class is phrasing-independent and edge-count sensitive, that a captured row carries a NON-EMPTY intent key and is matchable by the very turn that produced it (an empty key silently kills replay while looking wired), that an empty DAG and a disabled flag both write nothing, and that load_run_templates filters to keyed rows, honours the limit, and degrades open on a read failure rather than raising into the planner.
# AI-related: ./mios_pipe/routing/run_template.py, ./mios_pipe/routing/replay.py, ./mios_pipe/routing/dag_exec.py, /usr/share/mios/postgres/schema-init.sql
# AI-functions: check, t_class, t_capture, t_capture_disabled, t_load, main

"""Unit tests for run-template capture + the replay read side (WS-6 / T-225)."""

import asyncio
import sys

from mios_pipe.routing import replay as R
from mios_pipe.routing import run_template as RT

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


A = "search the web for the latest linux kernel CVEs and summarise the top three"


def _wire(rows, *, enable=True, db_read=None):
    RT.configure(run_template_enable=enable, pg_primary=True,
                 pg_mirror=lambda t, r: rows.append(r),
                 db_create=lambda *a, **k: "x", db_post=lambda s: s,
                 db_fire=lambda x: None, db_read=db_read or (lambda *a, **k: None))


def t_class():
    a = {"nodes": [{"id": 1, "tool": "web_search"}, {"id": 2, "tool": "summarize", "deps": [1]}]}
    b = {"nodes": [{"id": 9, "tool": "summarize", "deps": [8]}, {"id": 8, "tool": "web_search"}]}
    check("class: same shape, different ids/order -> same class",
          RT._run_template_class(a) == RT._run_template_class(b))
    c = {"nodes": [{"id": 1, "tool": "web_search"}, {"id": 2, "tool": "summarize"}]}
    check("class: a different EDGE count -> a different class",
          RT._run_template_class(a) != RT._run_template_class(c))
    d = {"nodes": [{"id": 1, "tool": "web_search"}, {"id": 2, "tool": "open_url", "deps": [1]}]}
    check("class: different TOOLS -> a different class",
          RT._run_template_class(a) != RT._run_template_class(d))
    check("class: an empty DAG still classes without raising",
          isinstance(RT._run_template_class({}), str))


def t_capture():
    rows = []
    _wire(rows)
    RT._capture_run_template(
        {"summary": "s", "intent": A, "nodes": [{"id": 1, "tool": "web_search"}]}, "sess1")
    check("capture: one row is written", len(rows) == 1, str(len(rows)))
    row = rows[0] if rows else {}
    check("capture: the row carries a NON-EMPTY intent key",
          bool(row.get("intent_key")), str(row.get("intent_key")))
    check("capture: the row carries the turn itself", row.get("intent") == A)
    check("capture: the row carries the session", row.get("session_id") == "sess1")
    check("capture: the captured row is matchable by ITS OWN turn",
          R.match_template(A, [dict(row)], 0.85)[1] == 1.0)

    rows.clear()
    RT._capture_run_template({"summary": "s", "nodes": []}, "sess1")
    check("capture: an empty DAG writes nothing", rows == [])

    rows.clear()
    RT._capture_run_template({"summary": "s", "nodes": [{"id": 1, "tool": "x"}]}, None)
    check("capture: a DAG with no intent still stores, with an empty key",
          len(rows) == 1 and rows[0].get("intent_key") == "", str(rows[:1]))


def t_capture_disabled():
    rows = []
    _wire(rows, enable=False)
    RT._capture_run_template(
        {"summary": "s", "intent": A, "nodes": [{"id": 1, "tool": "web_search"}]}, "s")
    check("capture: the disabled flag writes nothing", rows == [])
    _wire([], enable=True)


def t_load():
    seen = {}

    async def _read(sql, pg_sql=None):
        seen["sql"] = pg_sql or sql
        return [{"result": [{"intent": A, "intent_key": R.intent_key(A),
                             "dag": {"nodes": [{"id": 1}]}}]}]

    _wire([], db_read=_read)
    out = asyncio.run(RT.load_run_templates(7))
    check("load: returns the stored rows", len(out) == 1, str(out))
    check("load: filters to rows that actually carry a key",
          "intent_key IS NOT NULL" in seen.get("sql", ""), seen.get("sql", ""))
    check("load: newest first", "ORDER BY ts DESC" in seen.get("sql", ""))
    check("load: the statement is a CONSTANT -- no caller value reaches the SQL",
          seen.get("sql", "").rstrip(";") == RT._SQL_LOAD, seen.get("sql", ""))
    check("load: the read is capped in the statement itself",
          f"LIMIT {RT._MAX_ROWS}" in seen.get("sql", ""), seen.get("sql", ""))

    async def _many(sql, pg_sql=None):
        seen["sql"] = pg_sql or sql
        return [{"result": [{"intent": f"turn {i}", "intent_key": R.intent_key(f"turn {i}"),
                             "dag": {"nodes": [{"id": 1}]}} for i in range(40)]}]

    _wire([], db_read=_many)
    check("load: the caller's limit slices the RESULT",
          len(asyncio.run(RT.load_run_templates(7))) == 7)
    check("load: a zero/absent limit falls back to a sane one, never zero rows",
          len(asyncio.run(RT.load_run_templates(0))) == 40)
    _wire([], db_read=_read)

    async def _boom(sql, pg_sql=None):
        raise RuntimeError("db down")

    _wire([], db_read=_boom)
    check("load: a read failure degrades OPEN (planning proceeds)",
          asyncio.run(RT.load_run_templates(5)) == [])

    _wire([], enable=False, db_read=_read)
    check("load: the disabled flag reads nothing",
          asyncio.run(RT.load_run_templates(5)) == [])
    _wire([], enable=True)


def main():
    t_class()
    t_capture()
    t_capture_disabled()
    t_load()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())

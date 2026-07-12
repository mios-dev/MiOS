#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_evict (WS-A3 parameterized-pg eviction). Pure stdlib, no server.py/DB/pytest. Verifies the WHERE fragment is PARAMETERIZED pg (named %(...)s placeholders, COALESCE not ??, no legacy time::now()/record-ids), TTL added only with_ttl, the count/select/delete SQL shapes (count(*) AS c, LIMIT %(limit)s, DELETE ... id = ANY(%(ids)s)), pg dict-row parsing (count + bigint ids), and plan_sweep arithmetic.
# AI-related: ./mios_evict.py
# AI-functions: check, main
"""Unit tests for mios_evict (WS-A3 parameterized-pg cutover)."""

import sys

import mios_evict as ev

_fails = 0
TABLE = "knowledge"


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_where_parameterized():
    w = ev.evict_where(with_ttl=False)
    check("where: COALESCE not legacy ??", "COALESCE" in w and "??" not in w)
    check("where: parameterized min_access", "%(min_access)s" in w)
    check("where: protects hot/satisfied/pinned",
          all(s in w for s in ("<> 'hot'", "COALESCE(satisfied", "COALESCE(pinned")))
    check("where: no TTL when with_ttl=False", "ttl_days" not in w and "make_interval" not in w)
    check("where: no legacy time::now()", "time::now()" not in w)
    wt = ev.evict_where(with_ttl=True)
    check("where: TTL predicate parameterized", "make_interval(days => %(ttl_days)s)" in wt)
    check("where: no interpolated literal Nd", "90d" not in wt)


def t_sql_shapes():
    where = ev.evict_where(with_ttl=True)
    csql = ev.count_sql(TABLE, where)
    check("count: count(*) AS c", "SELECT count(*) AS c FROM knowledge WHERE" in csql)
    ssql = ev.select_ids_sql(TABLE, where, ev.order_by(cap=False))
    check("select: SELECT id + LIMIT param", "SELECT id FROM knowledge WHERE" in ssql and "LIMIT %(limit)s" in ssql)
    check("select: order oldest-access first", "COALESCE(last_access, ts) ASC" in ssql)
    csap = ev.select_ids_sql(TABLE, where, ev.order_by(cap=True))
    check("select: cap order least-recalled first", "COALESCE(access_count, 0) ASC" in csap)
    dsql = ev.delete_ids_sql(TABLE)
    check("delete: parameterized ANY (not record-id concat)",
          dsql == "DELETE FROM knowledge WHERE id = ANY(%(ids)s)", dsql)
    check("delete: no legacy 'DELETE knowledge:'", "knowledge:" not in dsql)


def t_params():
    p = ev.evict_params(2, 90, 50)
    check("params: typed", p == {"min_access": 2, "ttl_days": 90, "limit": 50})
    check("params: limit floored >=0", ev.evict_params(0, 0, -5)["limit"] == 0)


def t_parse():
    check("parse_count: pulls c", ev.parse_count([{"c": 42}]) == 42)
    check("parse_count: empty -> 0", ev.parse_count([]) == 0)
    check("parse_count: malformed -> 0", ev.parse_count([{"x": 1}]) == 0)
    check("parse_ids: bigint ids", ev.parse_ids([{"id": 1}, {"id": 2}, {"id": 3}]) == [1, 2, 3])
    check("parse_ids: skips non-int", ev.parse_ids([{"id": 5}, {"id": None}, {"nope": 1}]) == [5])
    check("parse_ids: empty -> []", ev.parse_ids([]) == [])


def t_plan_sweep():
    p = ev.plan_sweep(total=1000, ttl_candidates=30, max_rows=900, batch=50)
    check("plan: ttl within batch", p["ttl_delete"] == 30)
    check("plan: overflow = total-cap", p["overflow"] == 100)
    check("plan: cap uses remaining batch", p["cap_delete"] == 20)
    p2 = ev.plan_sweep(total=100, ttl_candidates=0, max_rows=900, batch=50)
    check("plan: no overflow -> no cap delete", p2["overflow"] == 0 and p2["cap_delete"] == 0)


def main():
    t_where_parameterized()
    t_sql_shapes()
    t_params()
    t_parse()
    t_plan_sweep()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())

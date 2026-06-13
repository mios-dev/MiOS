# AI-hint: Standalone unit test for mios_evict to verify SQL construction for knowledge eviction, including blast-radius arithmetic, TTL logic, and SurrealDB response parsing for count and ID extraction.
# AI-related: mios_evict
# AI-functions: _check, t_protect_where, t_ttl_where, t_parse_count, t_parse_ids, t_delete_stmt, t_plan_sweep, main
"""Standalone unit test for mios_evict (WS-3 knowledge eviction helpers).

Pure stdlib + the sibling module only -- no server.py / SurrealDB needed, so it
runs on any Python 3.10+. Covers the SQL-building, response-parsing, and the
blast-radius arithmetic (the risky bits); the live DELETE semantics are verified
by the operator via dry-run logs against a real SurrealDB.

Run:  python test_mios_evict.py
"""

import sys

import mios_evict as E

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_protect_where() -> None:
    w = E.protect_where(1)
    _check("protect: excludes hot", "(tier ?? 'warm') != 'hot'" in w)
    _check("protect: excludes satisfied", "(satisfied ?? false) != true" in w)
    _check("protect: excludes pinned", "(pinned ?? false) != true" in w)
    _check("protect: min_access wired", "(access_count ?? 0) < 1" in w, w)
    _check("protect: min_access=3 renders", "< 3" in E.protect_where(3))


def t_ttl_where() -> None:
    w = E.ttl_where(E.protect_where(1), 90)
    _check("ttl: age predicate", "(last_access ?? ts) < time::now() - 90d" in w, w)
    _check("ttl: keeps protect", "(tier ?? 'warm') != 'hot'" in w)
    _check("ttl: custom days", "- 30d" in E.ttl_where("X", 30))


def t_parse_count() -> None:
    # SurrealDB /sql returns a list of statement-result objects; the USE prefix
    # yields a non-list result that must be skipped.
    resp = [{"status": "OK", "result": None},
            {"status": "OK", "result": [{"c": 42}]}]
    _check("count: extracts 42", E.parse_count(resp) == 42, str(E.parse_count(resp)))
    _check("count: empty -> 0", E.parse_count([]) == 0)
    _check("count: None -> 0", E.parse_count(None) == 0)
    _check("count: no-list -> 0", E.parse_count([{"result": None}]) == 0)
    _check("count: empty-list -> 0", E.parse_count([{"result": []}]) == 0)


def t_parse_ids() -> None:
    resp = [{"result": None},
            {"result": [{"id": "knowledge:abc"}, {"id": "knowledge:def"},
                        {"nope": 1}, {"id": "no-colon"}]}]
    ids = E.parse_ids(resp)
    _check("ids: extracts record ids", ids == ["knowledge:abc", "knowledge:def"],
           str(ids))
    _check("ids: empty -> []", E.parse_ids([]) == [])
    # non-string id coerced then ':'-checked
    _check("ids: stringifies", E.parse_ids([{"result": [{"id": 5}]}]) == [],
           "int id has no ':' -> dropped")


def t_delete_stmt() -> None:
    _check("delete: builds stmt",
           E.delete_stmt(["knowledge:a", "knowledge:b"])
           == "DELETE knowledge:a, knowledge:b;",
           E.delete_stmt(["knowledge:a", "knowledge:b"]))
    _check("delete: empty -> ''", E.delete_stmt([]) == "")
    _check("delete: filters invalid", E.delete_stmt(["bad", "knowledge:c"])
           == "DELETE knowledge:c;")


def t_plan_sweep() -> None:
    # under cap, only TTL candidates
    p = E.plan_sweep(total=100, ttl_candidates=10, max_rows=50000, batch=500)
    _check("plan: ttl only", p == {"overflow": 0, "ttl_delete": 10, "cap_delete": 0},
           str(p))
    # over cap, no ttl
    p = E.plan_sweep(total=50100, ttl_candidates=0, max_rows=50000, batch=500)
    _check("plan: cap only (batch-bounded)",
           p == {"overflow": 100, "ttl_delete": 0, "cap_delete": 100}, str(p))
    # ttl takes priority within batch; cap gets the remainder
    p = E.plan_sweep(total=51000, ttl_candidates=400, max_rows=50000, batch=500)
    _check("plan: ttl priority then cap remainder",
           p == {"overflow": 1000, "ttl_delete": 400, "cap_delete": 100}, str(p))
    # ttl alone exceeds batch -> cap gets nothing this sweep
    p = E.plan_sweep(total=60000, ttl_candidates=600, max_rows=50000, batch=500)
    _check("plan: ttl saturates batch",
           p == {"overflow": 10000, "ttl_delete": 500, "cap_delete": 0}, str(p))
    # nothing to do
    p = E.plan_sweep(total=10, ttl_candidates=0, max_rows=50000, batch=500)
    _check("plan: noop", p == {"overflow": 0, "ttl_delete": 0, "cap_delete": 0},
           str(p))


def main() -> int:
    for t in (t_protect_where, t_ttl_where, t_parse_count, t_parse_ids,
              t_delete_stmt, t_plan_sweep):
        t()
    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

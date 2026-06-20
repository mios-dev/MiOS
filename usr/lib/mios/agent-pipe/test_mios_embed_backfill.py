#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_embed_backfill (WS-A2 embedding-version hygiene). Pure stdlib, no server.py / DB / pytest -- runs as `python3 test_mios_embed_backfill.py` (exit 0 = pass) on the build host and as a build.sh sub-phase. Covers the staleness predicate (needs_reembed: only emb-present rows with a mismatched/NULL version), the parameterized candidate-SELECT + version-stamp UPDATE SQL shapes, batch planning, and the plan summary.
# AI-related: ./mios_embed_backfill.py
# AI-functions: check, main
"""Unit tests for mios_embed_backfill (WS-A2)."""

import sys

import mios_embed_backfill as bf

_fails = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _fails
    tag = "PASS" if cond else "FAIL"
    if not cond:
        _fails += 1
    print(f"[{tag}] {name}" + (f" -- {detail}" if detail else ""))


def t_needs_reembed():
    cur = "nomic-768-v1"
    check("stale: emb present, old version -> reembed",
          bf.needs_reembed(True, "nomic-768-v0", cur) is True)
    check("stale: emb present, NULL version -> reembed",
          bf.needs_reembed(True, None, cur) is True)
    check("current: emb present, same version -> skip",
          bf.needs_reembed(True, cur, cur) is False)
    check("no vector: never reembed (left for embed-on-write)",
          bf.needs_reembed(False, "anything", cur) is False)
    check("whitespace-insensitive version compare",
          bf.needs_reembed(True, "  nomic-768-v1 ", cur) is False)


def t_select_sql():
    sql, params = bf.select_candidates_sql("knowledge", "v2", limit=100)
    check("select: targets the table", "FROM knowledge" in sql)
    check("select: only emb-present rows", "emb IS NOT NULL" in sql)
    check("select: version mismatch clause", "emb_version IS DISTINCT FROM %(ver)s" in sql)
    check("select: parameterized (no literal version)", "v2" not in sql)
    check("select: params carry version + limit",
          params["ver"] == "v2" and params["lim"] == 100)
    _, p2 = bf.select_candidates_sql("agent_memory", "v2", limit=0)
    check("select: limit floored to >=1", p2["lim"] == 1)


def t_stamp_sql():
    sql = bf.stamp_version_sql("knowledge")
    check("stamp: UPDATE the table", sql.startswith("UPDATE knowledge"))
    check("stamp: writes emb+model+version", all(
        s in sql for s in ("emb = %(emb)s", "emb_model = %(model)s", "emb_version = %(ver)s")))
    check("stamp: keyed by id", "WHERE id = %(id)s" in sql)


def t_batches():
    check("batch: splits into chunks", bf.plan_batches(list(range(10)), 4) ==
          [[0, 1, 2, 3], [4, 5, 6, 7], [8, 9]])
    check("batch: empty -> []", bf.plan_batches([], 5) == [])
    check("batch: size floored to >=1", len(bf.plan_batches([1, 2, 3], 0)) == 3)
    check("batch: single batch when small", bf.plan_batches([1, 2], 50) == [[1, 2]])


def t_summary():
    s = bf.summarize(125, 50)
    check("summary: candidate count", s["candidates"] == 125)
    check("summary: batch count (ceil)", s["batches"] == 3, f"{s}")
    check("summary: zero candidates -> 0 batches", bf.summarize(0, 50)["batches"] == 0)


def main() -> int:
    t_needs_reembed()
    t_select_sql()
    t_stamp_sql()
    t_batches()
    t_summary()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())

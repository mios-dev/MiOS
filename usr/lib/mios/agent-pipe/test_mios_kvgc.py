#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_kvgc (WS-A4 KV-file GC planner). Pure stdlib, no server.py/DB/podman/pytest. Verifies the TTL pass (age-out old files), the total-size cap (oldest-first eviction until under cap), that protected/active-slot files are NEVER evicted (even when over cap), freed-bytes accounting, and the empty/no-op cases.
# AI-related: ./mios_kvgc.py
# AI-functions: check, main
"""Unit tests for mios_kvgc (WS-A4)."""

import sys

import mios_kvgc as gc

_fails = 0
NOW = 1_000_000.0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def f(path, age_s, size):
    return {"path": path, "mtime": NOW - age_s, "size": size}


def t_ttl():
    files = [f("a.bin", 10, 100), f("b.bin", 5000, 100), f("c.bin", 9999, 100)]
    plan = gc.plan_gc(files, ttl_s=3600, max_bytes=0, now=NOW)
    check("ttl: evicts files older than ttl", set(plan.evict) == {"b.bin", "c.bin"}, f"{plan.evict}")
    check("ttl: keeps fresh file", plan.kept == ["a.bin"])
    check("ttl: reason tagged", plan.reasons["b.bin"] == "ttl")
    check("ttl: freed bytes accounted", plan.freed_bytes == 200, f"{plan.freed_bytes}")


def t_size_cap():
    # 5 files of 100 each = 500; cap 250 -> evict oldest until <=250 (evict 3).
    files = [f(f"f{i}.bin", age_s=i * 10, size=100) for i in range(5)]
    plan = gc.plan_gc(files, ttl_s=0, max_bytes=250, now=NOW)
    check("size: evicts oldest-first to fit cap", len(plan.evict) == 3, f"{plan.to_dict()}")
    # oldest = largest age = f4,f3,f2.
    check("size: evicted the OLDEST", set(plan.evict) == {"f4.bin", "f3.bin", "f2.bin"}, f"{plan.evict}")
    check("size: survivors under cap", sum(100 for _ in plan.kept) <= 250)
    check("size: reason tagged size_cap", all(plan.reasons[p] == "size_cap" for p in plan.evict))


def t_protect():
    # Even when massively over cap, a protected (active-slot) file is never evicted.
    files = [f("active.bin", 9999, 1000), f("old.bin", 8888, 1000)]
    plan = gc.plan_gc(files, ttl_s=3600, max_bytes=0, now=NOW, protect=["active.bin"])
    check("protect: active never TTL-evicted", "active.bin" not in plan.evict)
    check("protect: non-protected old evicted", "old.bin" in plan.evict)
    # size-cap with protect:
    files2 = [f("active.bin", 1, 1000), f("p1.bin", 50, 100), f("p2.bin", 60, 100)]
    plan2 = gc.plan_gc(files2, ttl_s=0, max_bytes=150, now=NOW, protect=["active.bin"])
    check("protect: active counts vs cap but is never evicted", "active.bin" not in plan2.evict, f"{plan2.to_dict()}")
    check("protect: evicts evictable to fit", len(plan2.evict) >= 1)


def t_noop():
    plan = gc.plan_gc([], ttl_s=3600, max_bytes=100, now=NOW)
    check("noop: empty -> nothing", plan.evict == [] and plan.kept == [] and plan.freed_bytes == 0)
    files = [f("a.bin", 1, 10)]
    plan2 = gc.plan_gc(files, ttl_s=0, max_bytes=0, now=NOW)
    check("noop: no ttl + no cap -> keep all", plan2.evict == [] and plan2.kept == ["a.bin"])
    plan3 = gc.plan_gc(files, ttl_s=3600, max_bytes=1000, now=NOW)
    check("noop: under both thresholds -> keep all", plan3.evict == [])


def main():
    t_ttl()
    t_size_cap()
    t_protect()
    t_noop()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())

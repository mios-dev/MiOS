#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_toolconflict.ConflictGate (WS-A7). Pure stdlib + asyncio, no server.py / DB / pytest -- runs as `python3 test_mios_toolconflict.py` (exit 0 = pass) both on the build host and as a build.sh sub-phase. Covers the no-op fast path, parallel_limit caps, conflict_group mutual exclusion, group+limit composition (deadlock-free), cancellation-safety (no permit leak), release-on-exception, and from_catalog parsing.
# AI-related: ./mios_toolconflict.py, ./test_mios_sched.py
# AI-functions: _run, _peak_under, check, main
"""Unit tests for mios_toolconflict (WS-A7 per-verb dispatch serialization)."""

import asyncio
import sys

import mios_toolconflict as tc

_fails = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global _fails
    tag = "PASS" if cond else "FAIL"
    if not cond:
        _fails += 1
    print(f"[{tag}] {name}" + (f" -- {detail}" if detail else ""))


def _run(coro):
    return asyncio.run(coro)


async def _peak_under(gate: tc.ConflictGate, verbs, n_each: int = 4, hold: float = 0.02):
    """Launch n_each concurrent guarded bodies for each verb in `verbs`; return
    (global_peak, per_group_peak) observed concurrency. Each body bumps a live
    counter, records the peak, then sleeps `hold` so overlap is observable."""
    live = 0
    peak = 0
    group_live = {}
    group_peak = {}

    async def body(verb):
        nonlocal live, peak
        async with gate.guard(verb):
            live += 1
            peak = max(peak, live)
            grp = gate._groups.get(verb)
            if grp is not None:
                group_live[grp] = group_live.get(grp, 0) + 1
                group_peak[grp] = max(group_peak.get(grp, 0), group_live[grp])
            try:
                await asyncio.sleep(hold)
            finally:
                live -= 1
                if grp is not None:
                    group_live[grp] -= 1

    tasks = [asyncio.create_task(body(v)) for v in verbs for _ in range(n_each)]
    await asyncio.gather(*tasks)
    return peak, group_peak


async def t_noop():
    g = tc.ConflictGate()  # empty -> serializes nothing
    peak, _ = await _peak_under(g, ["anything"], n_each=5)
    check("no-op: unconstrained verb runs fully concurrent", peak == 5, f"peak={peak}")
    check("no-op: constrains() false", not g.constrains("anything"))


async def t_parallel_limit():
    g = tc.ConflictGate(limits={"open_app": 1, "pair": 2})
    peak1, _ = await _peak_under(g, ["open_app"], n_each=5)
    check("parallel_limit=1: strictly single-flight", peak1 == 1, f"peak={peak1}")
    peak2, _ = await _peak_under(g, ["pair"], n_each=6)
    check("parallel_limit=2: at most 2 concurrent", peak2 == 2, f"peak={peak2}")


async def t_conflict_group():
    # Two DIFFERENT verbs in the same group must never overlap.
    g = tc.ConflictGate(groups={"focus_window": "ui", "pc_type": "ui"})
    peak, gpeak = await _peak_under(g, ["focus_window", "pc_type"], n_each=3)
    check("conflict_group: cross-verb mutual exclusion", gpeak.get("ui") == 1, f"group_peak={gpeak}")
    check("conflict_group: global peak == 1 (one member at a time)", peak == 1, f"peak={peak}")


async def t_distinct_groups():
    g = tc.ConflictGate(groups={"a": "ga", "b": "gb"})
    peak, _ = await _peak_under(g, ["a", "b"], n_each=2)
    check("distinct groups run concurrently", peak >= 2, f"peak={peak}")


async def t_group_and_limit_no_deadlock():
    # A verb with BOTH a group and a limit must still complete (no deadlock) and
    # serialize at the tightest constraint.
    g = tc.ConflictGate(limits={"v": 1}, groups={"v": "g", "w": "g"})
    try:
        peak, gpeak = await asyncio.wait_for(
            _peak_under(g, ["v", "w"], n_each=3), timeout=2.0)
        check("group+limit: completes (no deadlock)", True)
        check("group+limit: serialized to 1", peak == 1 and gpeak.get("g") == 1,
              f"peak={peak} gpeak={gpeak}")
    except asyncio.TimeoutError:
        check("group+limit: completes (no deadlock)", False, "DEADLOCK/timeout")


async def t_cancellation_no_leak():
    g = tc.ConflictGate(limits={"v": 1})
    holding = asyncio.Event()
    release = asyncio.Event()

    async def holder():
        async with g.guard("v"):
            holding.set()
            await release.wait()

    h = asyncio.create_task(holder())
    await holding.wait()                      # holder owns the single permit
    waiter = asyncio.create_task(_acquire_once(g, "v"))
    await asyncio.sleep(0.02)                  # waiter is now blocked on acquire
    waiter.cancel()                            # cancel WHILE waiting
    try:
        await waiter
    except asyncio.CancelledError:
        pass
    release.set()                              # let holder finish
    await h
    # The cancelled waiter must not have leaked a permit: a fresh acquire works
    # immediately and in_flight returns to 0.
    ok = await asyncio.wait_for(_acquire_once(g, "v"), timeout=1.0)
    check("cancellation-safe: no permit leak", ok is True)
    check("cancellation-safe: in_flight drained", not g.stats()["in_flight"]["verbs"],
          f"in_flight={g.stats()['in_flight']}")


async def _acquire_once(g, verb):
    async with g.guard(verb):
        await asyncio.sleep(0)
    return True


async def t_release_on_exception():
    g = tc.ConflictGate(limits={"v": 1})

    async def boom():
        async with g.guard("v"):
            raise RuntimeError("boom")

    try:
        await boom()
    except RuntimeError:
        pass
    # Permit must have been released by the context manager despite the raise.
    ok = await asyncio.wait_for(_acquire_once(g, "v"), timeout=1.0)
    check("release-on-exception: permit freed after body raises", ok is True)
    check("release-on-exception: in_flight drained", not g.stats()["in_flight"]["verbs"])


def t_from_catalog():
    cat = {
        "open_app":     {"section": "Apps", "conflict_group": "desktop_ui"},
        "focus_window": {"section": "Win", "conflict_group": "desktop_ui", "parallel_limit": 1},
        "pc_type":      {"section": "Win", "conflict_group": "desktop_ui"},
        "web_search":   {"section": "Web", "parallel_limit": 3},
        "plain":        {"section": "X"},                       # neither
        "bad_limit":    {"section": "X", "parallel_limit": "nope"},  # unparseable
        "zero_limit":   {"section": "X", "parallel_limit": 0},      # < 1 -> dropped
        "not_a_dict":   "ignore me",
    }
    g = tc.ConflictGate.from_catalog(cat)
    check("from_catalog: conflict_group parsed", g._groups.get("open_app") == "desktop_ui")
    check("from_catalog: parallel_limit parsed", g._limits.get("web_search") == 3)
    check("from_catalog: group+limit on one verb", g.constrains("focus_window")
          and g._limits.get("focus_window") == 1)
    check("from_catalog: plain verb unconstrained", not g.constrains("plain"))
    check("from_catalog: unparseable limit dropped", "bad_limit" not in g._limits)
    check("from_catalog: <1 limit dropped", "zero_limit" not in g._limits)
    check("from_catalog: non-dict spec ignored", not g.constrains("not_a_dict"))
    st = g.stats()
    check("from_catalog: stats groups list", st["groups"] == ["desktop_ui"], f"{st['groups']}")


def main() -> int:
    _run(t_noop())
    _run(t_parallel_limit())
    _run(t_conflict_group())
    _run(t_distinct_groups())
    _run(t_group_and_limit_no_deadlock())
    _run(t_cancellation_no_leak())
    _run(t_release_on_exception())
    t_from_catalog()
    total = "ok" if _fails == 0 else f"{_fails} FAILED"
    print(f"\n{total}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())

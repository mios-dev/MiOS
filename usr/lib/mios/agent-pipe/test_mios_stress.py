"""Standalone unit test for mios_stress pure helpers (T20).

Pure stdlib + the sibling module only -- no httpx, no live agent-pipe (the live
run is exercised by the operator / the authorized direct-chat). Run:
  python test_mios_stress.py
"""

import sys

import mios_stress as S

_RESULTS: list = []


def _check(name: str, ok: bool, detail: str = "") -> None:
    _RESULTS.append((name, ok))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def t_percentile() -> None:
    xs = list(range(1, 11))  # 1..10
    _check("pct: p0", S.percentile(xs, 0) == 1)
    _check("pct: p100", S.percentile(xs, 100) == 10)
    _check("pct: p50", S.percentile(xs, 50) in (5, 6), str(S.percentile(xs, 50)))
    _check("pct: empty -> 0", S.percentile([], 95) == 0.0)


def t_aggregate() -> None:
    res = [{"latency_s": 1.0, "ok": True}, {"latency_s": 3.0, "ok": True},
           {"latency_s": 0.5, "ok": False, "status": 500}]
    a = S.aggregate(res, wall_s=2.0)
    _check("agg: count", a["count"] == 3)
    _check("agg: ok/errors", a["ok"] == 2 and a["errors"] == 1)
    _check("agg: error_rate", abs(a["error_rate"] - 0.3333) < 0.001, str(a["error_rate"]))
    _check("agg: throughput", a["throughput_rps"] == 1.0, str(a["throughput_rps"]))
    _check("agg: p95 from ok only", a["p95_s"] == 3.0, str(a["p95_s"]))
    _check("agg: empty", S.aggregate([], 1.0)["count"] == 0)


def t_throttle() -> None:
    _check("throttle: over", S.should_throttle(60, 50) is True)
    _check("throttle: under", S.should_throttle(40, 50) is False)
    _check("throttle: ceiling 0 = off", S.should_throttle(999, 0) is False)
    _check("throttle: None load", S.should_throttle(None, 50) is False)


def t_ramp() -> None:
    _check("ramp: increase under ceiling", S.ramp_concurrency(4, 16, 10, 50) == 6)
    _check("ramp: halve over ceiling", S.ramp_concurrency(8, 16, 99, 50) == 4)
    _check("ramp: cap at target", S.ramp_concurrency(15, 16, 10, 50) == 16)
    _check("ramp: floor at 1", S.ramp_concurrency(1, 16, 99, 50) == 1)
    _check("ramp: ceiling 0 = always increase", S.ramp_concurrency(4, 16, 999, 0) == 6)


def t_scenarios() -> None:
    sc = S.build_scenarios(40)
    _check("scen: exact count", len(sc) == 40, str(len(sc)))
    kinds = {s["kind"] for s in sc}
    _check("scen: mixed kinds", kinds == {"chat", "tool", "research"}, str(kinds))
    _check("scen: deterministic", [s["prompt"] for s in S.build_scenarios(10)]
           == [s["prompt"] for s in S.build_scenarios(10)])
    # interleaved (not all-chat-then-all-tool): first few span >1 kind
    _check("scen: interleaved", len({s["kind"] for s in sc[:3]}) > 1)
    _check("scen: count 0 -> empty", S.build_scenarios(0) == [])
    _check("scen: single-kind mix",
           {s["kind"] for s in S.build_scenarios(5, {"chat": 1.0})} == {"chat"})


def t_verdict() -> None:
    good = {"count": 100, "error_rate": 0.0, "p95_s": 10.0}
    _check("verdict: pass", S.verdict(good)["pass"] is True)
    _check("verdict: error fail", S.verdict({"count": 100, "error_rate": 0.5, "p95_s": 1})["pass"] is False)
    _check("verdict: p95 fail", S.verdict({"count": 100, "error_rate": 0.0, "p95_s": 999})["pass"] is False)
    _check("verdict: no requests", S.verdict({"count": 0})["pass"] is False)


def t_by_kind() -> None:
    res = [{"kind": "chat", "ok": True}, {"kind": "chat", "ok": False},
           {"kind": "tool", "ok": True}]
    bk = S.by_kind(res)
    _check("by_kind: chat 1/2", bk["chat"] == {"n": 2, "ok": 1}, str(bk["chat"]))
    _check("by_kind: tool 1/1", bk["tool"] == {"n": 1, "ok": 1})


def main() -> int:
    for t in (t_percentile, t_aggregate, t_throttle, t_ramp, t_scenarios,
              t_verdict, t_by_kind):
        t()
    passed = sum(1 for _, ok in _RESULTS if ok)
    total = len(_RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

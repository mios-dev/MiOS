#!/usr/bin/env python3
# AI-hint: Standalone assert-script unit test for mios_bench (agentic-capability benchmark scoring core). Pure stdlib, no server.py/DB/pytest. Verifies the unbiased pass@k estimator (pass@1=c/n, all-correct->1, c==0->0, k>n->0, monotonic in k), tau-bench's pass^k ("all k succeed": pass^1=c/n, c==n->1, c<k->0, pass^k<=pass@1<=pass@k) incl. the exact combinatorial value C(c,k)/C(n,k), the i.i.d. p**k closed form (the ~56%-at-k=8 reliability intuition), aggregate skip-when-n<k, percentile linear interpolation, and the CLASSic rollup (cost/latency-percentiles/accuracy/stability/security + task grouping).
# AI-related: ./mios_bench.py
# AI-functions: check, main
"""Unit tests for mios_bench (pass@k / pass^k / CLASSic scoring)."""

import sys

import mios_bench as b

_fails = 0


def check(name, cond, detail=""):
    global _fails
    if not cond:
        _fails += 1
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" -- {detail}" if detail else ""))


def _close(a, c, tol=1e-9):
    return abs(a - c) <= tol


def t_pass_at_k():
    check("pass@1 == c/n", _close(b.pass_at_k(10, 7, 1), 0.7))
    check("pass@k all-correct -> 1", _close(b.pass_at_k(5, 5, 3), 1.0))
    check("pass@k c==0 -> 0", _close(b.pass_at_k(5, 0, 3), 0.0))
    check("pass@k k>n -> 0", b.pass_at_k(3, 2, 5) == 0.0)
    # n=4,c=2,k=2: 1 - C(2,2)/C(4,2) = 1 - 1/6 = 5/6
    check("pass@k exact (4,2,2)=5/6", _close(b.pass_at_k(4, 2, 2), 5.0 / 6.0))
    # monotonic non-decreasing in k (more samples -> >= chance at least one passes)
    check("pass@k monotonic in k",
          b.pass_at_k(8, 3, 1) <= b.pass_at_k(8, 3, 2) <= b.pass_at_k(8, 3, 3))


def t_pass_hat_k():
    check("pass^1 == c/n", _close(b.pass_hat_k(10, 7, 1), 0.7))
    check("pass^k c==n -> 1", _close(b.pass_hat_k(5, 5, 3), 1.0))
    check("pass^k c<k -> 0", b.pass_hat_k(5, 2, 3) == 0.0)
    check("pass^k c==0 -> 0", b.pass_hat_k(5, 0, 2) == 0.0)
    check("pass^k k>n -> 0", b.pass_hat_k(3, 3, 5) == 0.0)
    # n=4,c=2,k=2: C(2,2)/C(4,2) = 1/6
    check("pass^k exact (4,2,2)=1/6", _close(b.pass_hat_k(4, 2, 2), 1.0 / 6.0))
    # the defining inequality: pass^k <= pass@1 <= pass@k (consistency is harder)
    n, c, k = 8, 6, 3
    check("pass^k <= pass@1 <= pass@k",
          b.pass_hat_k(n, c, k) <= b.pass_at_k(n, c, 1) + 1e-12
          and b.pass_at_k(n, c, 1) <= b.pass_at_k(n, c, k) + 1e-12)


def t_iid():
    check("iid pass^k = p**k (0.9,8)~=0.4305", _close(b.iid_pass_hat_k(0.9, 8), 0.9 ** 8, 1e-9))
    check("iid ~56% reliability at k=8 for p=0.93", 0.55 <= b.iid_pass_hat_k(0.93, 8) <= 0.57)
    check("iid p=1 -> 1", _close(b.iid_pass_hat_k(1.0, 8), 1.0))
    check("iid k=0 -> 1", _close(b.iid_pass_hat_k(0.5, 0), 1.0))
    check("iid clamps p>1", _close(b.iid_pass_hat_k(2.0, 3), 1.0))


def t_aggregate():
    tasks = [(4, 2), (4, 4), (1, 1)]   # last has n<k, skipped at k=2
    check("agg pass^k skips n<k", _close(
        b.aggregate_pass_hat_k(tasks, 2), (b.pass_hat_k(4, 2, 2) + 1.0) / 2.0))
    check("agg pass@k skips n<k", _close(
        b.aggregate_pass_at_k(tasks, 2), (b.pass_at_k(4, 2, 2) + 1.0) / 2.0))
    check("agg empty -> 0", b.aggregate_pass_hat_k([], 2) == 0.0)
    check("agg all-too-small -> 0", b.aggregate_pass_hat_k([(1, 1)], 3) == 0.0)


def t_pass_and_k_rate():
    # T-049: fraction of tasks whose pass^k is a PERFECT 1.0 (every trial passed).
    # (4,4) -> clears; (4,2) -> does not; (1,1) -> n<k, skipped at k=2.
    tasks = [(4, 4), (4, 2), (1, 1)]
    check("pass^k_rate = fraction all-pass (1 of 2 qualifying)",
          _close(b.aggregate_pass_and_k_rate(tasks, 2), 0.5))
    check("pass^k_rate all-perfect -> 1",
          _close(b.aggregate_pass_and_k_rate([(3, 3), (5, 5)], 2), 1.0))
    check("pass^k_rate none-perfect -> 0",
          _close(b.aggregate_pass_and_k_rate([(4, 3), (4, 2)], 2), 0.0))
    check("pass^k_rate empty -> 0", b.aggregate_pass_and_k_rate([], 2) == 0.0)
    check("pass^k_rate all-too-small -> 0",
          b.aggregate_pass_and_k_rate([(1, 1)], 3) == 0.0)
    # distinct from the MEAN pass^k: [(4,4),(4,2)] -> rate=0.5 but mean<0.5+ ...
    check("pass^k_rate differs from mean pass^k",
          b.aggregate_pass_and_k_rate([(4, 4), (4, 2)], 2)
          != b.aggregate_pass_hat_k([(4, 4), (4, 2)], 2))


def t_percentile():
    check("pctl p50 interp [100,200,300]=200", _close(b.percentile([100, 200, 300], 50), 200.0))
    check("pctl p95 [100,200,300]=290", _close(b.percentile([100, 200, 300], 95), 290.0))
    check("pctl single value", _close(b.percentile([42], 95), 42.0))
    check("pctl empty -> 0", b.percentile([], 50) == 0.0)
    check("pctl p0/p100 = min/max", _close(b.percentile([5, 1, 9], 0), 1.0)
          and _close(b.percentile([5, 1, 9], 100), 9.0))


def t_classic_rollup():
    recs = [
        {"task": "a", "ok": True, "cost": 0.1, "latency_ms": 100, "error": False, "security_violation": False},
        {"task": "a", "ok": False, "cost": 0.2, "latency_ms": 300, "error": True, "security_violation": False},
        {"task": "b", "ok": True, "cost": 0.3, "latency_ms": 200, "error": False, "security_violation": True},
    ]
    r = b.classic_rollup(recs, k=1)
    check("classic: n + n_tasks", r["n"] == 3 and r["n_tasks"] == 2)
    check("classic: cost", _close(r["cost_total"], 0.6, 1e-6) and _close(r["cost_mean"], 0.2, 1e-6))
    check("classic: accuracy 2/3", _close(r["accuracy"], 2.0 / 3.0, 1e-5))
    check("classic: stability k=1 = 1-err", _close(r["stability"], 2.0 / 3.0, 1e-5))
    check("classic: security 1-1/3", _close(r["security"], 2.0 / 3.0, 1e-5))
    check("classic: latency p50=200 p95=290", _close(r["latency_p50"], 200.0) and _close(r["latency_p95"], 290.0))
    # k=2 stability = pass^2 over tasks with n>=2 (only 'a': (2,1) -> 0)
    r2 = b.classic_rollup(recs, k=2)
    check("classic: stability k=2 = pass^2 grouped", _close(r2["stability"], 0.0))
    check("classic: empty -> safe zeros", b.classic_rollup([])["n"] == 0
          and b.classic_rollup([])["security"] == 1.0)


def main():
    t_pass_at_k()
    t_pass_hat_k()
    t_iid()
    t_aggregate()
    t_pass_and_k_rate()
    t_percentile()
    t_classic_rollup()
    print(f"\n{'ok' if _fails == 0 else str(_fails) + ' FAILED'}")
    return 1 if _fails else 0


if __name__ == "__main__":
    sys.exit(main())

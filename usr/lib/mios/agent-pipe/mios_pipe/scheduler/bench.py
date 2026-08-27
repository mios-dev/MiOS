# AI-hint: Pure, DB-free scoring core for the MiOS agentic-capability benchmark harness.
# AI-doc: usr/share/doc/mios/manual/scheduler.md

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple

def comb_ratio(numer_n: int, numer_k: int, denom_n: int, denom_k: int) -> float:
    """C(numer_n, numer_k) / C(denom_n, denom_k), guarding the empty denominator.
    Returns 0.0 when the denominator combination is 0 (e.g. k > n)."""
    denom = math.comb(denom_n, denom_k) if denom_k <= denom_n else 0
    if denom == 0:
        return 0.0
    numer = math.comb(numer_n, numer_k) if numer_k <= numer_n else 0
    return numer / denom

def pass_at_k(n: int, c: int, k: int) -> float:
    """Unbiased pass@k ("at least one of k succeeds") for n trials, c correct.
    = 1 - C(n-c, k)/C(n, k). pass@1 = c/n; all-correct -> 1; c==0 -> 0; k>n -> 0."""
    n, c, k = int(n), int(c), int(k)
    if k <= 0 or n <= 0 or k > n:
        return 0.0
    c = max(0, min(c, n))
    return 1.0 - comb_ratio(n - c, k, n, k)

def pass_hat_k(n: int, c: int, k: int) -> float:
    """Unbiased pass^k ("ALL k succeed", tau-bench reliability) for n trials, c
    correct. = C(c, k)/C(n, k). pass^1 = c/n; c==n -> 1; c<k -> 0; k>n -> 0.
    Always <= pass@1 <= pass@k (consistency is strictly harder)."""
    n, c, k = int(n), int(c), int(k)
    if k <= 0 or n <= 0 or k > n:
        return 0.0
    c = max(0, min(c, n))
    return comb_ratio(c, k, n, k)

def iid_pass_hat_k(p: float, k: int) -> float:
    """The i.i.d. closed form of pass^k: p**k. The intuition pump -- a 93%-reliable
    agent succeeds on all 8 of 8 trials only ~56% of the time."""
    p = max(0.0, min(1.0, float(p)))
    return p ** max(0, int(k))

def aggregate_pass_at_k(tasks: "Sequence[Tuple[int, int]]", k: int) -> float:
    """Mean pass@k across tasks. `tasks` = [(n_trials, c_correct), ...]. Tasks
    with fewer than k trials are skipped (can't estimate). 0.0 if none qualify."""
    vals = [pass_at_k(n, c, k) for (n, c) in tasks if n >= k and n > 0]
    return sum(vals) / len(vals) if vals else 0.0

def aggregate_pass_hat_k(tasks: "Sequence[Tuple[int, int]]", k: int) -> float:
    """Mean pass^k across tasks (the headline tau-bench reliability number).
    Tasks with fewer than k trials are skipped. 0.0 if none qualify."""
    vals = [pass_hat_k(n, c, k) for (n, c) in tasks if n >= k and n > 0]
    return sum(vals) / len(vals) if vals else 0.0

def aggregate_pass_and_k_rate(tasks: "Sequence[Tuple[int, int]]", k: int) -> float:
    vals = [1.0 if pass_hat_k(n, c, k) >= 1.0 else 0.0
            for (n, c) in tasks if n >= k and n > 0]
    return sum(vals) / len(vals) if vals else 0.0

def percentile(values: "Sequence[float]", q: float) -> float:
    """Linear-interpolation percentile (q in [0,100]) over `values`. [] -> 0.0."""
    xs = sorted(float(v) for v in values)
    if not xs:
        return 0.0
    if len(xs) == 1:
        return xs[0]
    q = max(0.0, min(100.0, float(q)))
    pos = (q / 100.0) * (len(xs) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return xs[lo]
    frac = pos - lo
    return xs[lo] * (1.0 - frac) + xs[hi] * frac

def classic_rollup(records: "List[dict]", *, k: int = 1) -> dict:
    recs = [r for r in (records or []) if isinstance(r, dict)]
    n = len(recs)
    if n == 0:
        return {"n": 0, "n_tasks": 0, "cost_total": 0.0, "cost_mean": 0.0,
                "latency_p50": 0.0, "latency_p95": 0.0, "accuracy": 0.0,
                "stability": 0.0, "security": 1.0}
    costs = [float(r.get("cost") or 0.0) for r in recs]
    lats = [float(r.get("latency_ms") or 0.0) for r in recs]
    n_ok = sum(1 for r in recs if r.get("ok"))
    n_err = sum(1 for r in recs if r.get("error"))
    n_sec = sum(1 for r in recs if r.get("security_violation"))
    by_task: dict = {}
    for r in recs:
        t = str(r.get("task") or "")
        slot = by_task.setdefault(t, [0, 0])
        slot[0] += 1
        if r.get("ok"):
            slot[1] += 1
    if k > 1:
        stability = aggregate_pass_hat_k([(v[0], v[1]) for v in by_task.values()], k)
    else:
        stability = 1.0 - (n_err / n)
    return {
        "n": n,
        "n_tasks": len(by_task),
        "cost_total": round(sum(costs), 6),
        "cost_mean": round(sum(costs) / n, 6),
        "latency_p50": round(percentile(lats, 50), 3),
        "latency_p95": round(percentile(lats, 95), 3),
        "accuracy": round(n_ok / n, 6),
        "stability": round(stability, 6),
        "security": round(1.0 - (n_sec / n), 6),
    }

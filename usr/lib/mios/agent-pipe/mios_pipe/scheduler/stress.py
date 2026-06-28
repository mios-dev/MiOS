#!/usr/bin/env python3
# AI-hint: Stress test harness for the agent-pipe that validates the /v1/chat/completions path under load-aware concurrency, ensuring stability of the llama.cpp/pgvector stack by monitoring latency and error rates.
# AI-related: mios-stresstest, mios-agent, localhost:8640
# AI-functions: percentile, aggregate, should_throttle, ramp_concurrency, build_scenarios, verdict, by_kind, _poll_load, _one, run, main
"""mios_stress -- end-to-end direct-chat stress harness for the MiOS agent-pipe.

Drives the OpenAI /v1/chat/completions path under BOUNDED, load-aware concurrency
and reports latency / throughput / error-rate + a pass/fail verdict. Built for
the full-conversion validation goal (llama.cpp + KV-paging primary, pgvector
backend, all features on).

SAFETY -- the operator's hard-won lessons baked in:
  * COMPLETES every turn (awaits to done) -- NEVER orphans a request. The server
    historically has a request-cancellation gap; abandoning turns (the classic
    bounded-curl mistake) leaves the DAG+deepen churning for minutes -> loadavg
    spikes -> wedge (the documented loadavg-361 incident). This harness never
    abandons a turn.
  * LOAD-AWARE circuit breaker: polls /v1/scheduler between waves; over the load
    ceiling it stops RAMPING and backs off (AIMD) -- "saturate the backlog,
    never the cores."
  * RAMPED concurrency: starts low, climbs toward the target only while healthy.

The pure helpers (percentile/aggregate/ramp/throttle/scenarios/verdict) are
stdlib-only + unit-tested (test_mios_stress.py); the async runner uses httpx
(already an agent-pipe dep) and is exercised live by the operator via
`mios-stresstest`.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from typing import Optional

from mios_config import PORT  # SSOT agent-pipe port (no restated :8640 literal)


# ── pure helpers (unit-tested) ───────────────────────────────────────────────
def percentile(values, p):
    """p-th percentile (0-100) of `values`, nearest-rank on a sorted copy."""
    xs = sorted(v for v in values if v is not None)
    if not xs:
        return 0.0
    if p <= 0:
        return xs[0]
    if p >= 100:
        return xs[-1]
    k = int(round((p / 100.0) * (len(xs) - 1)))
    return xs[max(0, min(len(xs) - 1, k))]


def aggregate(results, wall_s):
    """results = [{latency_s, ok(bool), status}] -> a metrics dict."""
    n = len(results)
    lat = [r["latency_s"] for r in results if r.get("ok")]
    ok = sum(1 for r in results if r.get("ok"))
    errs = n - ok
    return {
        "count": n, "ok": ok, "errors": errs,
        "error_rate": round((errs / n) if n else 0.0, 4),
        "p50_s": round(percentile(lat, 50), 3),
        "p95_s": round(percentile(lat, 95), 3),
        "p99_s": round(percentile(lat, 99), 3),
        "max_s": round(max(lat), 3) if lat else 0.0,
        "throughput_rps": round(ok / wall_s, 3) if wall_s > 0 else 0.0,
        "wall_s": round(wall_s, 2),
    }


def should_throttle(load1, ceiling):
    """True when the host 1-min load is over the ceiling -> stop ramping."""
    try:
        return float(ceiling) > 0 and float(load1) > float(ceiling)
    except (TypeError, ValueError):
        return False


def ramp_concurrency(current, target, load1, ceiling, step=2):
    """AIMD next concurrency: additive-increase toward `target` while healthy,
    multiplicative-decrease (halve) when over the load ceiling. Bounded [1,target]."""
    current = max(1, int(current))
    target = max(1, int(target))
    if should_throttle(load1, ceiling):
        return max(1, current // 2)
    return min(target, current + max(1, int(step)))


def build_scenarios(n, mix=None):
    """Deterministic, interleaved scenario list of size `n` from a weighted mix.
    Generic probes that exercise distinct pipeline paths -- NO hardcoded topic
    deny-lists, no PII (binding rules)."""
    mix = mix or {"chat": 0.6, "tool": 0.3, "research": 0.1}
    bank = {
        "chat":     "Briefly say hello and confirm you are responding (probe #{i}).",
        "tool":     "What is the current system status? Use your tools (probe #{i}).",
        "research": "Give a 3-point comparison of two well-known open-source databases (probe #{i}).",
    }
    keys = [k for k in bank if mix.get(k, 0) > 0] or list(bank)
    raw = {k: max(0, n) * float(mix.get(k, 0)) for k in keys}
    counts = {k: int(raw[k]) for k in keys}
    rem = max(0, n) - sum(counts.values())
    for k in sorted(keys, key=lambda k: raw[k] - int(raw[k]), reverse=True):
        if rem <= 0:
            break
        counts[k] += 1
        rem -= 1
    out, i, pools = [], 0, dict(counts)
    while len(out) < n and any(v > 0 for v in pools.values()):
        for k in keys:
            if pools[k] > 0:
                out.append({"kind": k, "prompt": bank[k].format(i=i)})
                pools[k] -= 1
                i += 1
                if len(out) >= n:
                    break
    return out


def verdict(agg, max_error_rate=0.02, max_p95_s=120.0):
    """Pass/fail from the aggregate vs thresholds -> {pass, reasons}."""
    if agg.get("count", 0) <= 0:
        return {"pass": False, "reasons": ["no requests completed"]}
    reasons = []
    if agg["error_rate"] > max_error_rate:
        reasons.append(f"error_rate {agg['error_rate']} > {max_error_rate}")
    if agg["p95_s"] > max_p95_s:
        reasons.append(f"p95 {agg['p95_s']}s > {max_p95_s}s")
    return {"pass": not reasons, "reasons": reasons or ["within thresholds"]}


def by_kind(results):
    """Per-scenario-kind ok/total tally."""
    kinds: dict = {}
    for r in results:
        k = r.get("kind", "?")
        d = kinds.setdefault(k, {"n": 0, "ok": 0})
        d["n"] += 1
        d["ok"] += 1 if r.get("ok") else 0
    return kinds


# ── live runner (httpx; operator runs this) ──────────────────────────────────
async def _poll_load(client, base):
    """Best-effort host 1-min load from /v1/scheduler (-> None on miss)."""
    try:
        r = await client.get(base + "/v1/scheduler", timeout=5)
        load = (((r.json().get("admission") or {}).get("host") or {}).get("load") or [])
        return float(load[0]) if load else None
    except Exception:  # noqa: BLE001
        return None


async def _one(client, base, scen, model, timeout):
    body = {"model": model, "stream": False,
            "messages": [{"role": "user", "content": scen["prompt"]}]}
    t0 = time.monotonic()
    try:
        r = await client.post(base + "/v1/chat/completions", json=body, timeout=timeout)
        return {"latency_s": time.monotonic() - t0, "ok": r.status_code == 200,
                "status": r.status_code, "kind": scen["kind"]}
    except Exception as e:  # noqa: BLE001
        return {"latency_s": time.monotonic() - t0, "ok": False,
                "status": str(e)[:80], "kind": scen["kind"]}


async def run(cfg):
    """Ramped, load-aware, COMPLETE-every-turn stress run. Returns the report."""
    import httpx  # agent-pipe dep; imported lazily so the pure helpers test w/o it
    base = cfg["endpoint"].rstrip("/")
    if base.endswith("/v1"):
        base = base[:-3]
    scenarios = build_scenarios(cfg["count"], cfg.get("mix"))
    results: list = []
    conc = max(1, int(cfg.get("start_concurrency", 2)))
    target = max(1, int(cfg["concurrency"]))
    ceiling = float(cfg.get("load_ceiling", 0) or 0)
    timeout = float(cfg.get("timeout_s", 600))
    model = cfg.get("model", "mios-agent")
    t0 = time.monotonic()
    async with httpx.AsyncClient() as client:
        idx = 0
        while idx < len(scenarios):
            wave = scenarios[idx: idx + conc]
            idx += len(wave)
            # run this wave to COMPLETION (gather awaits all -> no orphaned turns)
            results.extend(await asyncio.gather(
                *[_one(client, base, s, model, timeout) for s in wave]))
            load1 = await _poll_load(client, base)
            nxt = ramp_concurrency(conc, target, load1, ceiling)
            if cfg.get("verbose"):
                print(f"[stress] {len(results)}/{len(scenarios)} conc {conc}->{nxt} "
                      f"load={load1}", file=sys.stderr)
            conc = nxt
    wall = time.monotonic() - t0
    agg = aggregate(results, wall)
    return {"agg": agg, "by_kind": by_kind(results),
            "verdict": verdict(agg, cfg.get("max_error_rate", 0.02),
                               cfg.get("max_p95_s", 120.0)),
            "endpoint": base, "concurrency_target": target, "load_ceiling": ceiling}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="MiOS agent-pipe end-to-end direct-chat stress test")
    ap.add_argument("--endpoint", default=os.environ.get(
        "MIOS_STRESS_ENDPOINT", f"http://localhost:{PORT}/v1"))
    ap.add_argument("--model", default=os.environ.get("MIOS_STRESS_MODEL", "mios-agent"))
    ap.add_argument("--concurrency", type=int, default=8, help="target concurrency")
    ap.add_argument("--count", type=int, default=40, help="total requests")
    ap.add_argument("--start-concurrency", type=int, default=2)
    ap.add_argument("--load-ceiling", type=float, default=float(
        os.environ.get("MIOS_STRESS_LOAD_CEILING", "0")),
        help="host 1-min load over which to STOP ramping (0=off; set ~cpu*1.5)")
    ap.add_argument("--timeout-s", type=float, default=600)
    ap.add_argument("--max-error-rate", type=float, default=0.02)
    ap.add_argument("--max-p95-s", type=float, default=120.0)
    ap.add_argument("--verbose", action="store_true")
    ns = ap.parse_args(argv)
    out = asyncio.run(run(vars(ns)))
    print(json.dumps(out, indent=2))
    return 0 if out["verdict"]["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())

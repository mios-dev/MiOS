# AI-hint: Pure self-improvement ANALYZER (#64) -- improvement signals from local outcome data.
# AI-related: server.py, mios_pg, mios_reputation
# AI-functions: aggregate, analyze
#   Reads already-fetched tool_call outcome records (+ optional peer-reputation
#   snapshot) and computes the signals an improvement loop would act on: tools
#   with a high failure rate, persistently slow tools, and unreliable peers.
#   PURE + read-only + dependency-free -> unit-testable (test_mios_selfimprove.py).
#   This is the OBSERVE/ANALYZE half; CLOSING the loop (auto-tuning) is a separate
#   gated step (agent self-modification needs guardrails), intentionally NOT here.
"""Self-improvement analysis for #64 (federation + self-improve loop).

The risky part of "self-improvement" is an agent modifying itself; the safe,
high-value part is HONESTLY SEEING what is going wrong. This module is that safe
part: given the local outcome record (tool_call successes/latencies + peer
reputation), it surfaces concrete, ranked findings ("tool X fails 40% of the
time", "peer Y is unreliable") that a human -- or, later, a gated closed loop --
can act on. Pure functions over plain dicts: no DB, no server import, no I/O.
"""
from __future__ import annotations

from typing import Dict, List, Optional


def aggregate(tool_calls: list) -> "Dict[str, dict]":
    """Per-tool rollup from tool_call records. Each record may carry
    success(bool|None), exit_code(int|None), latency_ms(num|None), tainted."""
    stats: Dict[str, dict] = {}
    for tc in tool_calls or []:
        if not isinstance(tc, dict):
            continue
        tool = str(tc.get("tool") or "").strip() or "?"
        s = stats.setdefault(tool, {"n": 0, "fail": 0, "lat": 0.0, "latn": 0, "taint": 0})
        s["n"] += 1
        ok = tc.get("success")
        ec = tc.get("exit_code")
        failed = (ok is False) or (ok is None and ec not in (None, 0))
        if failed:
            s["fail"] += 1
        lat = tc.get("latency_ms")
        if isinstance(lat, (int, float)) and lat >= 0:
            s["lat"] += float(lat); s["latn"] += 1
        if tc.get("tainted"):
            s["taint"] += 1
    return stats


def analyze(tool_calls: list, *, reputation: "Optional[dict]" = None,
            min_samples: int = 5, fail_threshold: float = 0.3,
            slow_ms: float = 10000.0) -> dict:
    """Return {findings:[...], tools_analyzed, samples}. A finding is
    {kind, subject, severity, detail, suggestion}. Only tools with >= min_samples
    calls are judged (avoids over-reacting to a single failure)."""
    findings: List[dict] = []
    stats = aggregate(tool_calls)
    for tool, s in sorted(stats.items()):
        if s["n"] >= min_samples:
            fr = s["fail"] / s["n"]
            if fr >= fail_threshold:
                findings.append({
                    "kind": "failing_tool", "subject": tool,
                    "severity": "high" if fr >= 0.6 else "medium",
                    "detail": f"{s['fail']}/{s['n']} calls failed ({fr:.0%})",
                    "suggestion": f"inspect {tool}: stderr patterns, preconditions, or routing",
                })
        if s["latn"] >= min_samples:
            avg = s["lat"] / s["latn"]
            if avg >= slow_ms:
                findings.append({
                    "kind": "slow_tool", "subject": tool, "severity": "low",
                    "detail": f"avg latency {avg:.0f}ms over {s['latn']} calls",
                    "suggestion": f"consider a faster lane or a cache for {tool}",
                })
    for peer, r in (reputation or {}).items():
        if not isinstance(r, dict):
            continue
        score = r.get("score")
        seen = int(r.get("ok", 0)) + int(r.get("bad", 0))
        if isinstance(score, (int, float)) and score < 0.4 and seen >= 3:
            findings.append({
                "kind": "unreliable_peer", "subject": str(peer),
                "severity": "medium", "detail": f"reputation {score:.2f} over {seen} delegations",
                "suggestion": f"deprioritize or investigate peer {peer}",
            })
    # rank: high > medium > low, stable within a tier
    order = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: order.get(f.get("severity"), 9))
    return {
        "findings": findings,
        "tools_analyzed": len(stats),
        "samples": sum(s["n"] for s in stats.values()),
    }

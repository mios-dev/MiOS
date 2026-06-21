# AI-hint: WS-4 orchestrator-worker hop-budget + effort-scaling pure core. Extracts the cross-hop recursion-bound DECISIONS (depth_exhausted, the Via-chain loop guard, the Max-Forwards-style header seed) out of server.py into pure, unit-testable functions -- the structural guard that stops a worker which re-enters the gateway from recursing unboundedly. Adds effort_width(): the first-class "effort" knob that scales orchestration intensity (fan-out width) to query complexity, so a simple turn stays narrow and a hard one fans wide. server.py owns the contextvars + HTTP headers + the A2A self-id; this module owns the math.
# AI-related: ./server.py, /usr/share/mios/mios.toml, ./test_mios_hopbudget.py
# AI-functions: depth_exhausted, append_via, is_loop, seed_depth, effort_width
"""mios_hopbudget -- hop-budget recursion guard + effort scaling (WS-4, the AIOS
orchestrator-worker structural-guard layer).

Pure stdlib. The agent-pipe's fan-out can re-enter the gateway over HTTP (a
thin-gateway-as-worker, an A2A peer); a process-local depth counter resets to 0
across that hop -> unbounded recursion. The guard carries the depth + an
agent-id Via chain as headers (RFC 9110 Max-Forwards + Via) and kills a loop the
moment a self-id reappears. These functions are the pure decisions behind that
guard, plus the effort->width scaling that makes orchestration intensity a
first-class function of query complexity rather than a fixed cap.
"""

from __future__ import annotations

from typing import List


def depth_exhausted(depth: int, max_depth: int) -> bool:
    """True when a further fan-out hop would exceed the bound -> the caller must
    degrade CLOSED to single-agent. max_depth<=0 disables the bound."""
    try:
        return int(max_depth) > 0 and int(depth) >= int(max_depth)
    except (TypeError, ValueError):
        return False


def append_via(via_chain: str, self_id: str) -> str:
    """Append self_id to the comma-separated Via chain (skips empties)."""
    v = str(via_chain or "").strip()
    sid = str(self_id or "").strip()
    if not sid:
        return v
    return (v + "," + sid) if v else sid


def is_loop(via_chain: str, self_id: str) -> bool:
    """True when self_id already appears in the Via chain (case-insensitive) ->
    a re-entrant loop; the caller degrades closed instead of recursing."""
    sid = str(self_id or "").strip().lower()
    if not sid:
        return False
    chain: List[str] = [x.strip().lower() for x in str(via_chain or "").split(",") if x.strip()]
    return sid in chain


def seed_depth(hop_hdr, default: int = 0) -> int:
    """Parse an inbound X-MiOS-Hop header into a depth (>=0); `default` on miss
    so the bound CROSSES the HTTP hop instead of resetting to 0."""
    try:
        return max(0, int(str(hop_hdr).strip()))
    except (TypeError, ValueError):
        try:
            return max(0, int(default))
        except (TypeError, ValueError):
            return 0


def effort_width(effort, *, base: int = 2, cap: int = 6) -> int:
    """Map an 'effort' level to an orchestration fan-out width in [1, cap].
    Accepts a named tier (low|medium|high|max|xhigh) or a 0..1 float (complexity
    score). Unknown/empty -> `base`. This is the first-class knob that scales
    swarm intensity to query complexity instead of a single fixed width."""
    cap = max(1, int(cap))
    base = max(1, min(cap, int(base)))
    e = str(effort or "").strip().lower()
    named = {"low": 1, "medium": base, "high": max(base, cap - 1),
             "max": cap, "xhigh": cap}
    if e in named:
        return max(1, min(cap, named[e]))
    try:
        f = float(e)  # a 0..1 complexity score
        return max(1, min(cap, round(1 + f * (cap - 1))))
    except (TypeError, ValueError):
        return base

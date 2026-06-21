# AI-hint: WS-SCHED-SLO deadline/SLO scheduling core (the PURE half). The MiOS admission gate is capacity-only (VRAM/host-load) and degrades OPEN -- it can't say "no" and a probe failure silently disables backpressure. This adds SLO request classes (interactive vs best_effort), a per-class deadline budget, a least-deadline-first sort key (EDF-style ordering for the priority gate), and a FAIL-CLOSED shed decision: a best_effort dispatch is shed under capacity contention OR when the health probe failed (treat unknown as contended), while an interactive/foreground turn is NEVER shed. Pure stdlib + deterministic so it unit-tests in isolation; server.py owns wiring classify->_admit shed + the EDF key into PriorityGate, flag-gated. Sibling of mios_sched/mios_preempt.
# AI-related: ./mios_sched.py, ./mios_preempt.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_slo.py
# AI-functions: classify, deadline, edf_key, should_shed
"""mios_slo -- SLO-class admission + EDF ordering + fail-closed shed (WS-SCHED-SLO).

The 2026 SLO-serving frontier (SCORPIO/Andes/QLM): each request carries a
deadline/SLO class, the scheduler orders least-deadline-first, and best-effort
work is SHED under contention rather than unconditionally admitted. MiOS's
`_admit` is capacity-only (it always admits after a bounded wait) and worse,
degrades OPEN -- a DB/VRAM-probe failure during a storm silently disables
backpressure entirely.

This module is the PURE policy:
  * classify()     -- turn signals -> SLO class (interactive | best_effort).
  * deadline()     -- now + the class's wall-clock budget.
  * edf_key()      -- least-deadline-first sort key (earliest deadline served
                      first; interactive breaks ties).
  * should_shed()  -- FAIL-CLOSED: shed a best_effort dispatch under contention
                      OR when health is UNKNOWN (probe failed); NEVER shed
                      interactive. This inverts the current degrade-open hole.

server.py owns wiring (classify the turn, feed edf_key into PriorityGate._pick,
call should_shed in _admit), all flag-gated. Deterministic, no I/O.
"""
from __future__ import annotations

from typing import Optional

# SLO request classes, ASCENDING urgency (best_effort is shed first).
BEST_EFFORT = "best_effort"
INTERACTIVE = "interactive"
_CLASS_RANK = {BEST_EFFORT: 0, INTERACTIVE: 1}

# Default per-class deadline budget (seconds of wall-clock the turn SHOULD meet).
# interactive = a human waiting at the keyboard; best_effort = background /
# autonomous / fan-out work that can run long.
_DEFAULT_BUDGET_S = {INTERACTIVE: 8.0, BEST_EFFORT: 120.0}


def classify(*, foreground: bool = True, autonomous: bool = False,
             priority: float = 7.0, interactive_priority: float = 7.0) -> str:
    """Map turn signals to an SLO class. An AUTONOMOUS / background turn is
    best_effort; a FOREGROUND turn is interactive UNLESS its scheduling priority
    was clamped below `interactive_priority` (the autonomous-clamp path), in which
    case it is best_effort too. Fail-safe default (foreground, unclamped) ->
    interactive (protect the human)."""
    if autonomous or not foreground:
        return BEST_EFFORT
    return INTERACTIVE if float(priority) >= float(interactive_priority) else BEST_EFFORT


def deadline(slo_class: str, now: float, budgets: "Optional[dict]" = None) -> float:
    """Absolute deadline = now + the class's budget. Unknown class -> the
    best_effort budget (fail-safe: an unclassified turn is treated as low-urgency,
    never as a tighter-than-real deadline that could starve real interactive work)."""
    b = budgets or _DEFAULT_BUDGET_S
    return float(now) + float(b.get(slo_class, b.get(BEST_EFFORT, 120.0)))


def edf_key(slo_class: str, enqueue_t: float, now: float,
            budgets: "Optional[dict]" = None) -> tuple:
    """Least-deadline-first (EDF) sort key for the priority gate: (deadline,
    -class_rank). The EARLIEST absolute deadline is served first; an interactive
    request breaks a deadline tie (higher rank -> smaller -rank -> sorts first).
    Lower tuple = served sooner."""
    d = deadline(slo_class, enqueue_t, budgets)
    return (d, -_CLASS_RANK.get(slo_class, 0))


def should_shed(slo_class: str, *, over_ceiling: bool, healthy: bool = True) -> bool:
    """FAIL-CLOSED shed decision. An INTERACTIVE turn is NEVER shed (the human is
    protected). A BEST_EFFORT dispatch is shed when the system is over its
    capacity ceiling OR when health is UNKNOWN (`healthy=False`, e.g. the load/mem
    probe failed) -- the latter is the correctness fix: where `_admit` currently
    degrades OPEN (admit-on-probe-failure), best_effort here degrades CLOSED (shed
    when we can't confirm headroom), so a probe failure during a storm tightens
    backpressure instead of disabling it."""
    if slo_class == INTERACTIVE:
        return False
    if not healthy:
        return True
    return bool(over_ceiling)

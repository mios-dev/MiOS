# AI-hint: WS-SCHED-SLO deadline/SLO scheduling core (the PURE half). The MiOS admission gate is capacity-only (VRAM/host-load) and degrades OPEN -- it...
# AI-doc: usr/share/doc/mios/manual/scheduler.md
from __future__ import annotations

from typing import Optional

BEST_EFFORT = "best_effort"
INTERACTIVE = "interactive"
_CLASS_RANK = {BEST_EFFORT: 0, INTERACTIVE: 1}

_DEFAULT_BUDGET_S = {INTERACTIVE: 8.0, BEST_EFFORT: 120.0}
_DEFAULT_PRIORITY = 7.0
_INTERACTIVE_PRIORITY = 7.0

def configure(*, budgets: "Optional[dict]" = None,
              default_priority: "Optional[float]" = None,
              interactive_priority: "Optional[float]" = None) -> None:
    """Inject the SSOT [slo] policy (per-class deadline budgets + the interactive
    priority floor). server.py reads mios.toml [slo] and calls this once at load.
    Pure injection -- no I/O -- so the module stays deterministic and unit-testable
    in isolation; values stand at their documented defaults until injected."""
    global _DEFAULT_BUDGET_S, _DEFAULT_PRIORITY, _INTERACTIVE_PRIORITY
    if budgets is not None:
        _DEFAULT_BUDGET_S = dict(budgets)
    if default_priority is not None:
        _DEFAULT_PRIORITY = float(default_priority)
    if interactive_priority is not None:
        _INTERACTIVE_PRIORITY = float(interactive_priority)

def classify(*, foreground: bool = True, autonomous: bool = False,
             priority: "Optional[float]" = None,
             interactive_priority: "Optional[float]" = None) -> str:
    p = _DEFAULT_PRIORITY if priority is None else float(priority)
    ip = _INTERACTIVE_PRIORITY if interactive_priority is None else float(interactive_priority)
    if autonomous or not foreground:
        return BEST_EFFORT
    return INTERACTIVE if p >= ip else BEST_EFFORT

def deadline(slo_class: str, now: float, budgets: "Optional[dict]" = None) -> float:
    """Absolute deadline = now + the class's budget. Unknown class -> the
    best_effort budget (fail-safe: an unclassified turn is treated as low-urgency,
    never as a tighter-than-real deadline that could starve real interactive work)."""
    b = budgets or _DEFAULT_BUDGET_S
    return float(now) + float(
        b.get(slo_class, b.get(BEST_EFFORT, _DEFAULT_BUDGET_S[BEST_EFFORT])))

def edf_key(slo_class: str, enqueue_t: float, now: float,
            budgets: "Optional[dict]" = None) -> tuple:
    """Least-deadline-first (EDF) sort key for the priority gate: (deadline,
    -class_rank). The EARLIEST absolute deadline is served first; an interactive
    request breaks a deadline tie (higher rank -> smaller -rank -> sorts first).
    Lower tuple = served sooner."""
    d = deadline(slo_class, enqueue_t, budgets)
    return (d, -_CLASS_RANK.get(slo_class, 0))

def should_shed(slo_class: str, *, over_ceiling: bool, healthy: bool = True) -> bool:
    if slo_class == INTERACTIVE:
        return False
    if not healthy:
        return True
    return bool(over_ceiling)

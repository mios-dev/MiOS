# AI-hint: WS-A16 cost/quality SmartRouting core, designed per researched best practice (LiteLLM router + adaptive/cascading routing): LOCAL-FIRST...
# AI-doc: usr/share/doc/mios/manual/routing.md

from __future__ import annotations

from typing import Iterable, List, Optional

class Lane:
    """A routable lane with cost + quality metadata. kind: 'local' | 'remote'.
    cost_in = approx cost per 1k input tokens (0.0 for a local lane).
    quality_tier = higher is stronger (a heuristic capability rank)."""

    __slots__ = ("id", "kind", "cost_in", "quality_tier")

    def __init__(self, id: str, kind: str = "local", cost_in: float = 0.0,
                 quality_tier: int = 1) -> None:
        self.id = str(id)
        self.kind = str(kind)
        self.cost_in = max(0.0, float(cost_in))
        self.quality_tier = int(quality_tier)

    @property
    def is_local(self) -> bool:
        return self.kind == "local"

def order_lanes(lanes: Iterable[Lane]) -> List[Lane]:
    """The cascade order: ALL local lanes first (cheapest cost, then strongest),
    then remote lanes by ascending cost (then descending quality). Local-first
    by construction so a free local lane is always tried before a paid remote."""
    ls = list(lanes or [])
    locals_ = sorted((x for x in ls if x.is_local),
                     key=lambda x: (x.cost_in, -x.quality_tier))
    remotes = sorted((x for x in ls if not x.is_local),
                     key=lambda x: (x.cost_in, -x.quality_tier))
    return locals_ + remotes

class CostLedger:
    """Per-window spend tracker. Escalation to a paid lane is refused once the
    budget is exhausted (a runaway fan-out can't drain the account)."""

    __slots__ = ("spent", "budget")

    def __init__(self, budget: float = 0.0, spent: float = 0.0) -> None:
        self.budget = max(0.0, float(budget))   # 0 = unlimited
        self.spent = max(0.0, float(spent))

    def can_afford(self, cost: float) -> bool:
        if self.budget <= 0:
            return True
        return (self.spent + max(0.0, float(cost))) <= self.budget

    def charge(self, cost: float) -> None:
        self.spent += max(0.0, float(cost))

    def remaining(self) -> float:
        return float("inf") if self.budget <= 0 else max(0.0, self.budget - self.spent)

def should_escalate(quality_ok: bool, local_exhausted: bool) -> bool:
    """Escalate to the next (stronger/remote) lane when the local output failed
    its quality gate, OR the local group is exhausted (nothing local left)."""
    return (not quality_ok) or local_exhausted

def choose_next(lanes: Iterable[Lane], attempted: Iterable[str], *,
                ledger: Optional[CostLedger] = None,
                escalate: bool = False) -> Optional[Lane]:
    """Pick the next lane to try. Walks the cascade order, skipping already-
    attempted lanes. Local-first: a remote (paid) lane is only returned when
    `escalate` is True (the quality gate failed / local exhausted) AND the
    ledger can afford it. Returns None when nothing eligible remains."""
    done = {str(a) for a in (attempted or [])}
    for lane in order_lanes(lanes):
        if lane.id in done:
            continue
        if lane.is_local:
            return lane                      # always prefer an untried local lane
        if not escalate:
            continue
        if ledger is not None and not ledger.can_afford(lane.cost_in):
            continue                          # over budget -> skip this paid lane
        return lane
    return None

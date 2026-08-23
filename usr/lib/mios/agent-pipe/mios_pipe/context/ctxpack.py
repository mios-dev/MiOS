# AI-hint: WS-A5 priority token-budget context packer for the agent-pipe.
# AI-doc: usr/share/doc/mios/manual/context.md

from __future__ import annotations

from typing import Callable, List, Optional

import mios_tokenize


class PackResult:
    """The outcome of a pack(): kept/dropped items + token accounting."""

    __slots__ = ("kept", "dropped", "used_tokens", "budget")

    def __init__(self, kept: list, dropped: list, used_tokens: int, budget: int) -> None:
        self.kept = kept
        self.dropped = dropped
        self.used_tokens = used_tokens
        self.budget = budget

    def to_dict(self) -> dict:
        return {
            "kept": len(self.kept),
            "dropped": len(self.dropped),
            "used_tokens": self.used_tokens,
            "budget": self.budget,
        }


def pack(items: List, budget: int, *,
         text_of: Optional[Callable] = None,
         priority_of: Optional[Callable] = None,
         reserve: int = 0) -> PackResult:
    text_of = text_of or _default_text
    priority_of = priority_of or _default_priority
    avail = max(0, int(budget) - max(0, int(reserve)))

    enriched = []
    for i, it in enumerate(items or []):
        cost = mios_tokenize.count_text(text_of(it))
        enriched.append((i, it, cost, _num(priority_of(it))))

    order = sorted(enriched, key=lambda e: (-e[3], e[0]))  # priority desc, index asc
    kept_idx = set()
    used = 0
    for i, _it, cost, _p in order:
        if used + cost <= avail:
            kept_idx.add(i)
            used += cost
    kept = [e[1] for e in enriched if e[0] in kept_idx]
    dropped = [e[1] for e in enriched if e[0] not in kept_idx]
    return PackResult(kept, dropped, used, avail)


def _default_text(item) -> str:
    if isinstance(item, dict):
        return str(item.get("text") or "")
    return str(item)


def _default_priority(item):
    if isinstance(item, dict):
        return item.get("priority", 0)
    return 0


def _num(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0

# AI-hint: WS-A5 priority token-budget context packer for the agent-pipe. Given a list of candidate context items each carrying a priority + text, and a token budget, pack() greedily keeps the HIGHEST-priority items that fit the budget (measured via mios_tokenize) and DROPS the lowest-priority overflow, returning the kept items in their ORIGINAL order plus a packing report. Lets a hop assemble "as much of the most important context as fits" instead of a blind char slice. Pure stdlib; server.py decides what the items + budget are.
# AI-related: ./mios_tokenize.py, ./server.py, ./mios_compact.py, ./test_mios_ctxpack.py
# AI-functions: pack, class PackResult
"""mios_ctxpack -- priority token-budget context packing (WS-A5, the AIOS
Context-Manager assembly layer).

Pure stdlib (measures tokens via mios_tokenize). server.py owns WHAT the items
are (recalled knowledge, scratchpad checkpoints, tool previews, history) and the
budget; this module owns the SELECTION: keep the most important items that fit,
drop the rest, never exceed the budget.

Algorithm
=========
Stable greedy by priority: sort candidates by (priority desc, original-index
asc), admit each whose token cost still fits the remaining budget (skipping --
not stopping at -- an item too big to fit, so a smaller lower-priority item can
still be admitted), then re-emit the admitted set in ORIGINAL order. O(n log n).
"""

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
    """Select the highest-priority `items` whose total token cost fits
    `budget - reserve`, returned in ORIGINAL order.

    text_of(item) -> str  (default: item["text"] for dicts, else str(item))
    priority_of(item) -> number, higher = keep first (default: item["priority"], else 0)
    reserve: tokens to hold back from the budget (e.g. for a system prompt)."""
    text_of = text_of or _default_text
    priority_of = priority_of or _default_priority
    avail = max(0, int(budget) - max(0, int(reserve)))

    # (original_index, item, cost, priority)
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
        # else: skip this item, keep trying smaller lower-priority ones
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

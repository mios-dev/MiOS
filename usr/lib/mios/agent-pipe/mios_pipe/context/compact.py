# AI-hint: WS-A5 rolling-summary compaction planner for the agent-pipe. When a conversation's message history exceeds a token budget, plan_compaction() decides WHICH older messages to fold into a rolling summary and which recent ones to keep verbatim (always keeping the last keep_recent turns + any pinned system messages), measured via mios_tokenize. It returns the split (to_summarize / to_keep) -- the actual summarization LLM call stays in server.py; this module owns only the deterministic, testable DECISION of where to cut.
# AI-related: ./mios_tokenize.py, ./server.py, ./mios_ctxpack.py, ./test_mios_compact.py
# AI-functions: plan_compaction, class CompactionPlan
"""mios_compact -- rolling-summary compaction planning (WS-A5, the AIOS
Context-Manager history-compaction layer).

Pure stdlib (measures tokens via mios_tokenize). server.py owns the actual
summary generation (an LLM call) + applying the plan; this module owns the
deterministic decision: given a history + a token budget, keep the most recent
messages (and pinned system messages) verbatim, and mark the oldest overflow for
summarization so the prompt fits.

Why keep-recent-verbatim
========================
Recent turns carry the live task state; summarizing them loses fidelity. Older
turns compress well into a rolling summary. So compaction always preserves the
last `keep_recent` non-system messages + every system message, and only the
OLDEST messages beyond the budget are folded.
"""

from __future__ import annotations

from typing import List

import mios_tokenize


class CompactionPlan:
    """The compaction decision: which messages to summarize vs keep verbatim."""

    __slots__ = ("to_summarize", "to_keep", "needed", "kept_tokens")

    def __init__(self, to_summarize: list, to_keep: list,
                 needed: bool, kept_tokens: int) -> None:
        self.to_summarize = to_summarize   # oldest messages to fold into a summary
        self.to_keep = to_keep             # messages kept verbatim (in order)
        self.needed = needed               # False -> history already fit, no-op
        self.kept_tokens = kept_tokens

    def to_dict(self) -> dict:
        return {
            "needed": self.needed,
            "to_summarize": len(self.to_summarize),
            "to_keep": len(self.to_keep),
            "kept_tokens": self.kept_tokens,
        }


def plan_compaction(messages: List[dict], budget: int, *,
                    keep_recent: int = 4, keep_system: bool = True) -> CompactionPlan:
    """Decide the compaction split for `messages` under `budget` tokens.

    - System messages are kept verbatim when keep_system (they carry the
      contract/grounding).
    - The last `keep_recent` non-system messages are always kept (live state).
    - Older non-system messages are kept only while the running total fits the
      budget; the rest (OLDEST first) are marked to_summarize.
    needed=False (no-op) when the whole history already fits the budget."""
    msgs = [m for m in (messages or []) if isinstance(m, dict)]
    total = mios_tokenize.count_messages(msgs)
    if total <= max(0, int(budget)):
        return CompactionPlan([], list(msgs), needed=False, kept_tokens=total)

    keep_recent = max(0, int(keep_recent))
    # Partition: forced-keep (system) vs the ordered non-system stream.
    nonsys_idx = [i for i, m in enumerate(msgs)
                  if not (keep_system and m.get("role") in ("system", "developer"))]
    recent_keep = set(nonsys_idx[-keep_recent:]) if keep_recent else set()
    forced_keep = {i for i, m in enumerate(msgs)
                   if keep_system and m.get("role") in ("system", "developer")} | recent_keep

    used = sum(mios_tokenize.count_text(msgs[i].get("content") or "") for i in forced_keep)
    keep_idx = set(forced_keep)
    # Walk the remaining non-system messages NEWEST->oldest, keeping while they fit.
    for i in reversed([j for j in nonsys_idx if j not in forced_keep]):
        c = mios_tokenize.count_text(msgs[i].get("content") or "")
        if used + c <= int(budget):
            keep_idx.add(i)
            used += c
    to_keep = [m for i, m in enumerate(msgs) if i in keep_idx]
    to_summarize = [m for i, m in enumerate(msgs) if i not in keep_idx]
    return CompactionPlan(to_summarize, to_keep, needed=bool(to_summarize),
                          kept_tokens=used)

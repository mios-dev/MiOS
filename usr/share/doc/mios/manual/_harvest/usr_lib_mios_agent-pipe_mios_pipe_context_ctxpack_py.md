<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_ctxpack -- priority token-budget context packing...

mios_ctxpack -- priority token-budget context packing (WS-A5, the AIOS
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

<!-- mios-src:b1519b918772 from usr/lib/mios/agent-pipe/mios_pipe/context/ctxpack.py:3-17 -->

### Select the highest-priority `items` whose total token cost...

Select the highest-priority `items` whose total token cost fits
    `budget - reserve`, returned in ORIGINAL order.

    text_of(item) -> str  (default: item["text"] for dicts, else str(item))
    priority_of(item) -> number, higher = keep first (default: item["priority"], else 0)
    reserve: tokens to hold back from the budget (e.g. for a system prompt).

<!-- mios-src:e1ff87b7b627 from usr/lib/mios/agent-pipe/mios_pipe/context/ctxpack.py:50-55 -->

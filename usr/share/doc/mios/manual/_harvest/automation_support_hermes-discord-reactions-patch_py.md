<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### In-place patch of gateway/platforms/discord.py to add...

In-place patch of gateway/platforms/discord.py to add progressive
"thinking" reactions on the operator's Discord message during agent
processing.

Operator directive "also add more reactions to the
MiOS-Hermes Discord bot--Should be using more discord reactions to
show it's thinking!"

Upstream hermes-agent's Discord gateway emits exactly two reactions:
  on_processing_start    -> 👀 (single "looking" emoji)
  on_processing_complete -> ✅ / ❌

That gives the operator no visibility into what stage the agent is in
mid-run. This patch enriches the reaction surface with a progressive
sequence:
    📡 (received)          immediate
    🧠 (thinking)          after 2s if still processing
    🛠️ (using tools)       after 8s if still processing
    ⏳ (still working)      after 20s if still processing
    ✅ / ❌ (final)         on completion (and all phase reactions
                            are cleared first so the final outcome
                            stands alone)

A background asyncio.create_task() drives the progression so the
gateway's normal flow isn't blocked. The task is stashed on the
gateway instance keyed by Discord message id so concurrent
in-flight messages each get their own task that the matching
on_processing_complete can cancel.

Idempotent: rerunning is a no-op once the marker comment is present.
Safe: if Discord's add_reaction / remove_reaction fail (rate limit,
missing perm), each call already swallows the exception in the
existing _add_reaction / _remove_reaction helpers, so the progression
degrades silently.

Usage:
    hermes-discord-reactions-patch.py /path/to/discord.py

<!-- mios-src:72d662d789d6 from automation/support/hermes-discord-reactions-patch.py:3-40 -->

### Locate the contiguous on_processing_start +...

Locate the contiguous on_processing_start + on_processing_complete
    method pair by line-scanning. Returns (start_idx, end_idx) as half-
    open slice indices into `lines`. (-1, -1) if not found.

    Line-by-line scanning avoids the catastrophic backtracking that a
    nested-quantifier regex hits on this 5500-line file (the upstream
    discord.py has dozens of `async def` at 4-space indent, and the
    regex explores every alignment).

<!-- mios-src:e413ead8f7a4 from automation/support/hermes-discord-reactions-patch.py:104-112 -->

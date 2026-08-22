<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### mios_compact -- rolling-summary compaction planning (WS-A5...

mios_compact -- rolling-summary compaction planning (WS-A5, the AIOS
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

<!-- mios-src:a51b0ea20546 from usr/lib/mios/agent-pipe/mios_pipe/context/compact.py:3-18 -->

### Decide the compaction split for `messages` under `budget`...

Decide the compaction split for `messages` under `budget` tokens.

    - System messages are kept verbatim when keep_system (they carry the
      contract/grounding).
    - The last `keep_recent` non-system messages are always kept (live state).
    - Older non-system messages are kept only while the running total fits the
      budget; the rest (OLDEST first) are marked to_summarize.
    needed=False (no-op) when the whole history already fits the budget.

<!-- mios-src:d0d1ebdb2522 from usr/lib/mios/agent-pipe/mios_pipe/context/compact.py:50-57 -->

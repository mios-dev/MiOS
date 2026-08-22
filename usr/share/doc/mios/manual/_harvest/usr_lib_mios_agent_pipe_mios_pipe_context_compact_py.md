<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A5 rolling-summary compaction planner for the agent-pipe. When a conversation's message history exceeds a token budget, plan_compaction() decides WHICH older messages to fold into a rolling summary and which recent ones to keep verbatim (always keeping the last keep_recent turns + any pinned system messages), measured via mios_tokenize. It returns the split (to_summarize / to_keep) -- the actual summarization LLM call stays in server.py; this module owns only the deterministic, testable DECISION of where to cut.
AI-related: ./mios_tokenize.py, ./server.py, ./mios_ctxpack.py, ./test_mios_compact.py
AI-functions: plan_compaction, class CompactionPlan

<!-- mios-src:6cc83f3576ac from usr/lib/mios/agent-pipe/mios_pipe/context/compact.py:1-3 -->


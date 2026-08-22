<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: WS-A7 per-verb conflict/parallel-limit serialization for the agent-pipe Tool Manager. Provides ConflictGate, a pure-stdlib asyncio primitive that serializes verb dispatches the way a plain pass-through chokepoint cannot: a per-verb `parallel_limit` (max concurrent dispatches of that verb) AND a `conflict_group` (named mutual-exclusion set so stateful single-instance verbs -- e.g. open_app/focus_window/pc_type all contending for the one foreground window + keyboard -- never interleave across a council/DAG fan-out). server.py owns the wiring (build from _VERB_CATALOG, wrap _dispatch_bounded); this module owns only the reusable mechanism. No-op fast path for the vast majority of verbs that declare neither.
AI-related: ./mios_sched.py, ./server.py, /usr/share/mios/mios.toml, ./test_mios_toolconflict.py
AI-functions: from_catalog, guard, stats, _group_sem, _verb_sem, class ConflictGate, class _Guard

<!-- mios-src:bac13a75479d from usr/lib/mios/agent-pipe/mios_pipe/routing/toolconflict.py:1-3 -->


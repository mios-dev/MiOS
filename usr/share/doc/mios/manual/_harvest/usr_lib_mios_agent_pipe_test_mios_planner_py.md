<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Stdlib assert-script for mios_planner. No network: the planner LLM call in decompose_intent is exercised only on the early short-prompt-skip / disabled paths (no httpx). Verifies (1) _topological_order on a synthetic DAG -- dependency order + cycle/dangling fall-back to declaration order, no hang; (2) _dag_levels Kahn concurrent-level grouping + cycle progress-forcing; (3) decompose_intent envelope parse on a representative planner output via a STUBBED model call (monkeypatched httpx.AsyncClient) -- agent/tool node validation, <2-node reject, node cap; (4) configure() builds _PLANNER_SYSTEM byte-faithfully from injected sentinel catalogs and embeds them; (5) short-prompt-skip cutoffs read from SSOT injection; (6) the now-native Stage-2 narrowers _action_domain_verbs / _planner_system_for over a synthetic permission-driven SSOT (action-domain union, block-swap, research slice, None/unknown fail-safe).
AI-related: ./mios_planner.py, ./server.py
AI-functions: (test script -- no exported functions)

<!-- mios-src:127d71ccfea0 from usr/lib/mios/agent-pipe/test_mios_planner.py:1-3 -->


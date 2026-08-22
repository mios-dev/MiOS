<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: OAI-04/T-225 run-template REPLAY matcher -- the reuse half of the WS-6 capture path. Pure stdlib and deliberately MODEL-FREE: the whole point is to answer a repeated intent without spending a planning call, so an embedding call would defeat the feature. Keys a turn by its normalized significant tokens (order-insensitive, so rephrasing survives), matches a stored template by exact key first and bounded Jaccard overlap second, and returns NO match below the SSOT confidence threshold so a fuzzy variant re-plans instead of replaying the wrong DAG. The structural class in dag_exec answers "same plan shape"; this answers "same request", which is the question you have to ask BEFORE planning.
AI-related: ./dag_exec.py, ./planner.py, /usr/share/mios/mios.toml, ./test_mios_replay.py, usr/share/doc/mios/manual/ch61-run-template-replay.md
AI-functions: normalize_tokens, intent_key, similarity, match_template

<!-- mios-src:888995d394fe from usr/lib/mios/agent-pipe/mios_pipe/routing/replay.py:1-3 -->


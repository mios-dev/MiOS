<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: Council/swarm fan-out SELECTION (refactor R3 wave; de-hardcoded per operator "the scoring IS a hardcode in and of itself"). Sole export _pick_fanout_agents (now async): picks the SECONDARY (name,cfg) agents to run CONCURRENTLY alongside the chosen primary. Relevance is MODEL-DRIVEN (generative) -- the orchestrator micro-model is shown the refined plan + each eligible agent's OWN card (role/strengths/A2A skill-tags, the mios.toml [agents.*] SSOT) and RETURNS which specialists are worth engaging; there is NO hand-coded scoring heuristic, no magic weight, no lexical/ASCII token-overlap, no hardcoded lane bonus or topic map. force_council (full swarm) + council mode (equal-weight all-eligible) are explicit non-heuristic overrides and are unchanged. Degrade-open: if model selection is off/unavailable/fails, fall back to council-equal-weight (all eligible, sub-lane-diverse, endpoint/model-deduped, COUNCIL_MAX-capped) -- never single-primary, never the unbounded runaway. Safety bounds (depth-exhaust degrade-closed, dedup, roster cap, admission shed) stay -- the model chooses RELEVANCE, the caps bound WIDTH. Selection mode + micro model/endpoint/timeout are SSOT ([dispatch].fanout_select_mode + [ai].micro_model/micro_endpoint). Pure of server.py (one-way boundary): registry/config/helpers injected via configure; own httpx micro-call like mios_refine/mios_dci. server.py awaits the re-imported _pick_fanout_agents (surface-parity zero-diff).
AI-related: ./server.py, ./mios_config.py, ./mios_jsonsalvage.py, ./test_mios_fanout.py
AI-functions: _pick_fanout_agents, _model_select, _eligible_candidates, _council_fallback, configure

<!-- mios-src:18b9ad7f079a from usr/lib/mios/agent-pipe/mios_pipe/routing/fanout.py:1-3 -->


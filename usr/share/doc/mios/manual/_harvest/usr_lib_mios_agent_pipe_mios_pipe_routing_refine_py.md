<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: REFINE intent-classifier extracted verbatim from server.py (refactor R5/mios_refine wave). The PRIMARY pre-router pass -- refine_intent() calls the micro/refine model (own httpx) and parses the strict-json envelope into the intent/refined_text/news/web/local_state/needs_location/browser_action/domain_type/multi_task fields that feed all downstream routing, plus _salvage_refine_dispatch (recover a one-verb dispatch when the model NARRATES instead of emitting JSON) and the load-bearing classifier prompts _REFINE_SYSTEM / _REFINE_SYSTEM_LITE (moved byte-for-byte -- a single altered character changes routing behavior). Sibling imports: loads_lenient (mios_jsonsalvage), _env_grounding (mios_grounding), _deterministic_action_route (mios_routing), mios_tokenize. Every symbol that STAYS in server.py (logger, the config consts REFINE_*, the _VERB_CATALOG/_AGENT_REGISTRY/_FASTPATH_VERBS/routing-phrase globals, _over_global_ceiling/_resolve_verb_key/_route_domain/_routed_domain_var, the _db_* writers) is dependency-INJECTED via configure() under its EXACT original server name (one-way boundary -- this module NEVER imports server). server.py re-imports every moved name verbatim + re-applies the @_traced_stage("refine") span at the boundary (surface-parity zero-diff).
AI-related: server.py (host of the DI deps + re-import site), mios_routing (_deterministic_action_route + the SSOT routing-phrase loaders), mios_grounding (_env_grounding), mios_jsonsalvage (loads_lenient), mios_tokenize (history truncation), mios_config (config SSOT).
AI-functions: refine_intent, _salvage_refine_dispatch, configure

<!-- mios-src:6326c1034fe0 from usr/lib/mios/agent-pipe/mios_pipe/routing/refine.py:1-3 -->


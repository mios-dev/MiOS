<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### AI-hint

AI-hint: ROUTING layer extracted verbatim from server.py (refactor R2/mios_routing wave). The deterministic SSOT-config routing loaders -- _load_routing_domains (mios.toml [routing.domains.*] -> the 2-stage domain router), _load_routing_phrases (a lowercased/longest-first phrase list from [routing].<key>), _load_launch_fillers -- plus _deterministic_action_route, the catalog-derived pre-router that binds an unambiguous "open/launch <app>" (or a standalone "type '<text>'") to a single concrete verb BEFORE the refine micro can mis-classify it as a research swarm. All phrase/domain vocab is mios.toml data (NO hardcoded English). The loaders are pure config + a logger; _deterministic_action_route reads the fast-path verb sets + launch phrase frozensets, which stay in server.py (they derive from the _VERB_CATALOG server global) and are dependency-INJECTED via configure() under their original server names (one-way boundary -- this module NEVER imports server). server.py re-imports every name verbatim under its original alias (surface-parity zero-diff).
AI-related: ./server.py, ./mios_config.py, ./test_mios_routing.py
AI-functions: _load_routing_domains, _load_routing_phrases, _load_launch_fillers, _deterministic_action_route, configure

<!-- mios-src:5977af513137 from usr/lib/mios/agent-pipe/mios_pipe/routing/routing.py:1-3 -->


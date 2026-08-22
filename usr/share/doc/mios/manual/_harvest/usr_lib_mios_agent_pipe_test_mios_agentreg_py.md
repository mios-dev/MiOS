<!-- AI-hint: Prose harvested out of source comments by `mios-manual harvest`; each passage carries the mios-src anchor that proves which comment it came from. -->

# Harvested notes

### !/usr/bin/env python3 AI-hint: Standalone assert-script...

!/usr/bin/env python3
AI-hint: Standalone assert-script unit test for mios_agentreg (R3 agent/node registry builders). Pure stdlib, no server.py/DB/pytest. Stubs the injected deps (_is_remote_endpoint, _opt_int_mb, logger, flags) via configure() and monkeypatches the module's _toml_section so the [nodes.*] reader runs offline, then asserts: _build_agent_engines folds the home/cpu/explicit bindings; _load_agent_registry parses [agents.*], inherits [agents._defaults], applies the health_gate safe-default for remote/optional kinds, indexes per-agent auth into _AGENT_AUTH_BY_HOSTPORT, and falls back to a single hermes entry when empty; _load_node_pool synthesises one node:<name> research worker per [nodes.*] entry and skips endpoint-less nodes.
AI-related: ./mios_agentreg.py, ./mios_config.py
AI-functions: check, t_build_agent_engines, t_load_agent_registry, t_load_node_pool, t_health_gate_via_registry, t_agent_lane, t_render_agent_catalog, t_role_system, t_dedup_pool_by_target, main

<!-- mios-src:657de19c8639 from usr/lib/mios/agent-pipe/test_mios_agentreg.py:1-4 -->

